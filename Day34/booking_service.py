import hashlib
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Booking, BookingLine, Package, User
from schemas import BookingInput


def owned_booking(db: Session, booking_id: int, user: User, lock: bool = False):
    query = select(Booking).where(Booking.id == booking_id)
    if user.role != "admin":
        query = query.where(Booking.user_id == user.id)
    if lock:
        query = query.with_for_update()
    booking = db.scalar(query)
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking


def create_booking(db: Session, user: User, data: BookingInput, key: str):
    digest = hashlib.sha256(data.model_dump_json().encode()).hexdigest()

    def replay(booking):
        if booking.request_hash != digest:
            raise HTTPException(409, "Idempotency key already used with different booking")
        return booking

    existing = db.scalar(select(Booking).where(Booking.user_id == user.id, Booking.idempotency_key == key))
    if existing:
        return replay(existing)
    try:
        db.scalar(select(User).where(User.id == user.id).with_for_update())
        existing = db.scalar(select(Booking).where(Booking.user_id == user.id, Booking.idempotency_key == key))
        if existing:
            return replay(existing)
        items = {}
        for line in sorted(data.lines, key=lambda x: x.item_id):
            item = db.scalar(select(Package).where(Package.id == line.item_id).with_for_update())
            if not item or not item.active or item.start_date <= date.today():
                raise HTTPException(404, f"Available package {line.item_id} not found")
            if item.capacity < line.quantity:
                raise HTTPException(409, f"Insufficient seats for package {line.item_id}")
            if (line.expected_price is not None and item.price != line.expected_price
                    or line.expected_start_date is not None and item.start_date != line.expected_start_date):
                raise HTTPException(409, "Package terms changed; request a new confirmation")
            items[line.item_id] = item
        booking = Booking(user_id=user.id, total=sum(items[line.item_id].price * line.quantity for line in data.lines),
                          status="CONFIRMED", idempotency_key=key, request_hash=digest)
        db.add(booking)
        db.flush()
        for line in data.lines:
            item = items[line.item_id]
            item.capacity -= line.quantity
            db.add(BookingLine(booking_id=booking.id, item_id=item.id, quantity=line.quantity, unit_price=item.price))
        db.commit()
        db.refresh(booking)
        return booking
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Booking).where(Booking.user_id == user.id, Booking.idempotency_key == key))
        if existing:
            return replay(existing)
        raise
    except Exception:
        db.rollback()
        raise


def cancellation_quote(db: Session, booking: Booking):
    if booking.status != "CONFIRMED":
        raise HTTPException(409, "Only confirmed bookings can be cancelled")
    refund = Decimal("0")
    for line in booking.lines:
        item = db.get(Package, line.item_id)
        days = (item.start_date - date.today()).days
        if days < 0:
            raise HTTPException(409, "Past departures cannot be cancelled")
        rate = Decimal("1") if days >= 7 else Decimal("0.5") if days >= 2 else Decimal("0")
        refund += line.unit_price * line.quantity * rate
    return refund.quantize(Decimal("0.01"))


def cancel_booking(db: Session, user: User, booking_id: int, expected_refund: Decimal | None = None):
    try:
        booking = owned_booking(db, booking_id, user, lock=True)
        if booking.user_id != user.id:
            raise HTTPException(404, "Booking not found")
        if booking.status == "CANCELLED":
            return booking
        for line in sorted(booking.lines, key=lambda x: x.item_id):
            db.scalar(select(Package).where(Package.id == line.item_id).with_for_update())
        refund = cancellation_quote(db, booking)
        if expected_refund is not None and refund != expected_refund:
            raise HTTPException(409, "Cancellation terms changed; request a new confirmation")
        for line in sorted(booking.lines, key=lambda x: x.item_id):
            item = db.get(Package, line.item_id)
            item.capacity += line.quantity
        booking.refund = refund
        booking.status = "CANCELLED"
        db.commit()
        return booking
    except Exception:
        db.rollback()
        raise
