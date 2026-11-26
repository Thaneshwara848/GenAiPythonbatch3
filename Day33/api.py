from decimal import Decimal
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from business import TRANSITIONS, cancel_order, create_order
from database import get_db
from models import MenuItem, Order, User
from schemas import ItemCreate, ItemResponse, ItemUpdate, OrderCreate, OrderResponse, StatusUpdate
from security import admin_user, current_user

router = APIRouter(prefix="/api")
Db = Annotated[Session, Depends(get_db)]
Current = Annotated[User, Depends(current_user)]
Admin = Annotated[User, Depends(admin_user)]


@router.get("/me")
def me(user: Current):
    return {"username": user.username, "role": user.role}


@router.get("/menu_items", response_model=list[ItemResponse])
def list_items(db: Db, category: str | None = None, vegetarian: bool | None = None,
               max_price: Decimal | None = Query(default=None, gt=0), keyword: str | None = Query(default=None, max_length=120)):
    query = select(MenuItem).where(MenuItem.active.is_(True))
    if category:
        query = query.where(MenuItem.category == category)
    if vegetarian is not None:
        query = query.where(MenuItem.vegetarian == vegetarian)
    if max_price is not None:
        query = query.where(MenuItem.price <= max_price)
    if keyword:
        query = query.where(MenuItem.title.contains(keyword, autoescape=True))
    return db.scalars(query.order_by(MenuItem.id)).all()


@router.get("/menu_items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Db):
    item = db.scalar(select(MenuItem).where(MenuItem.id == item_id, MenuItem.active.is_(True)))
    if not item:
        raise HTTPException(404, "Menu item not found")
    return item


@router.post("/menu_items", response_model=ItemResponse, status_code=201)
def add_item(data: ItemCreate, db: Db, admin: Admin):
    item = MenuItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/menu_items/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, data: ItemUpdate, db: Db, admin: Admin):
    item = db.scalar(select(MenuItem).where(MenuItem.id == item_id).with_for_update())
    if not item:
        raise HTTPException(404, "Menu item not found")
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/menu_items/{item_id}", status_code=204)
def disable_item(item_id: int, db: Db, admin: Admin):
    item = db.scalar(select(MenuItem).where(MenuItem.id == item_id).with_for_update())
    if not item:
        raise HTTPException(404, "Menu item not found")
    item.active = False
    db.commit()
    return Response(status_code=204)


@router.post("/orders", response_model=OrderResponse, status_code=201)
def post_order(data: OrderCreate, db: Db, user: Current,
               idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128)):
    return create_order(db, user.id, data, idempotency_key)


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(db: Db, user: Current):
    return db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())).all()


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Db, user: Current):
    query = select(Order).where(Order.id == order_id)
    if user.role != "admin":
        query = query.where(Order.user_id == user.id)
    order = db.scalar(query)
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
def post_cancel(order_id: int, db: Db, user: Current, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", min_length=1, max_length=128)):
    return cancel_order(db, order_id, user.id, idempotency_key or str(uuid4()))


@router.patch("/admin/orders/{order_id}/status", response_model=OrderResponse)
def update_status(order_id: int, data: StatusUpdate, db: Db, admin: Admin):
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if not order:
        raise HTTPException(404, "Order not found")
    if data.status not in TRANSITIONS.get(order.status, set()):
        raise HTTPException(409, "Invalid order status transition")
    order.status = data.status
    db.commit()
    db.refresh(order)
    return order
