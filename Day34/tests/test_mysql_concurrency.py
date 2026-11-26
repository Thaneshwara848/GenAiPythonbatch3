import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from booking_service import create_booking
from database import SessionLocal
from models import Booking, BookingLine, Package, User
from schemas import BookingInput

pytestmark = pytest.mark.skipif(os.environ.get("TEST_MYSQL_CONCURRENCY") != "1", reason="Requires explicitly configured MySQL demo database")


def test_last_seat_is_sold_only_once():
    token = uuid.uuid4().hex
    with SessionLocal() as db:
        users = [User(username=f"test_{token}_{i}", password_hash="unused", role="user") for i in range(2)]
        package = Package(title="Concurrency test", destination="Test", duration_days=1, price=100,
                          capacity=1, start_date=date.today() + timedelta(days=30), active=True)
        db.add_all([*users, package])
        db.commit()
        user_ids = [u.id for u in users]
        package_id = package.id
    barrier = Barrier(2)

    def book(user_id):
        with SessionLocal() as db:
            user = db.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                booking = create_booking(db, user, BookingInput(lines=[{"item_id": package_id, "quantity": 1}]), "concurrent")
                return booking.status
            except HTTPException as exc:
                return exc.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(book, user_ids))
        assert outcomes.count("CONFIRMED") == 1
        assert outcomes.count(409) == 1
        with SessionLocal() as db:
            assert db.get(Package, package_id).capacity == 0
    finally:
        with SessionLocal() as db:
            booking_ids = db.scalars(select(Booking.id).where(Booking.user_id.in_(user_ids))).all()
            if booking_ids:
                db.execute(delete(BookingLine).where(BookingLine.booking_id.in_(booking_ids)))
                db.execute(delete(Booking).where(Booking.id.in_(booking_ids)))
            db.execute(delete(Package).where(Package.id == package_id))
            db.execute(delete(User).where(User.id.in_(user_ids)))
            db.commit()
