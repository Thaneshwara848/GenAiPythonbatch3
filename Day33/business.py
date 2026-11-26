import hashlib
import json
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import MenuItem, Order, OrderLine, User
from schemas import OrderCreate
from security import hash_password


def create_order(db: Session, user_id: int, data: OrderCreate, key: str):
    request_hash = hashlib.sha256(json.dumps(data.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    existing = db.scalar(select(Order).where(Order.user_id == user_id, Order.idempotency_key == key))
    if existing:
        if existing.request_hash != request_hash:
            raise HTTPException(409, "Idempotency key already used for a different order")
        return existing
    counts = Counter(line.item_id for line in data.lines)
    if any(count > 1 for count in counts.values()):
        raise HTTPException(422, "Each menu item may appear only once")
    items = db.scalars(select(MenuItem).where(MenuItem.id.in_(counts)).order_by(MenuItem.id).with_for_update()).all()
    by_id = {item.id: item for item in items}
    if len(by_id) != len(counts):
        raise HTTPException(404, "Menu item not found")
    total = 0
    lines = []
    for line in data.lines:
        item = by_id[line.item_id]
        if not item.active or item.capacity < line.quantity:
            raise HTTPException(409, f"Insufficient availability for {item.title}")
        if line.expected_unit_price is not None and item.price != line.expected_unit_price:
            raise HTTPException(409, f"Price changed for {item.title}; review and confirm again")
        item.capacity -= line.quantity
        total += item.price * line.quantity
        lines.append(OrderLine(item_id=item.id, quantity=line.quantity, unit_price=item.price))
    order = Order(user_id=user_id, total=total, idempotency_key=key, request_hash=request_hash, lines=lines)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order_id: int, user_id: int, key: str):
    order = db.scalar(select(Order).where(Order.id == order_id, Order.user_id == user_id).with_for_update())
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status == "CANCELLED" and order.cancel_key == key:
        return order
    if order.status != "CONFIRMED":
        raise HTTPException(409, "Cancellation is only allowed before preparation")
    ids = sorted(line.item_id for line in order.lines)
    items = db.scalars(select(MenuItem).where(MenuItem.id.in_(ids)).order_by(MenuItem.id).with_for_update()).all()
    by_id = {item.id: item for item in items}
    for line in order.lines:
        by_id[line.item_id].capacity += line.quantity
    order.status = "CANCELLED"
    order.cancel_key = key
    db.commit()
    db.refresh(order)
    return order


TRANSITIONS = {"CONFIRMED": {"PREPARING"}, "PREPARING": {"OUT_FOR_DELIVERY"}, "OUT_FOR_DELIVERY": {"DELIVERED"}}


def seed(db: Session):
    if db.scalar(select(User.id).limit(1)) is not None:
        return
    admin = User(username="admin", password_hash=hash_password("admin123"), role="admin")
    alice = User(username="alice", password_hash=hash_password("alice123"), role="user")
    bob = User(username="bob", password_hash=hash_password("bob123"), role="user")
    db.add_all([admin, alice, bob])
    entries = [
        ("Masala Dosa", "Breakfast", True, 90, 20),
        ("Paneer Biryani", "Main course", True, 180, 10),
        ("Idli Sambar", "Breakfast", True, 80, 20),
        ("Vegetable Pulao", "Main course", True, 150, 15),
        ("Dal Tadka", "Main course", True, 140, 15),
        ("Roti", "Sides", True, 25, 30),
        ("Chicken Curry", "Main course", False, 220, 12),
        ("Egg Fried Rice", "Main course", False, 170, 12),
        ("Mango Lassi", "Drinks", True, 70, 20),
        ("Gulab Jamun", "Dessert", True, 60, 15),
    ]
    db.add_all([MenuItem(title=t, category=c, vegetarian=v, price=p, capacity=n) for t, c, v, p, n in entries])
    db.commit()
    for user, item_id, key in [(alice, 1, "seed-alice-1"), (alice, 2, "seed-alice-2"), (bob, 3, "seed-bob-1")]:
        create_order(db, user.id, OrderCreate.model_validate({"lines": [{"item_id": item_id, "quantity": 1}]}), key)
