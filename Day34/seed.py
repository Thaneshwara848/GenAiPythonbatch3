"""Initialize a new demo database and insert fictional data without resetting existing data."""
from datetime import date, timedelta
from getpass import getpass
import os

import bcrypt
from sqlalchemy import select

from booking_service import create_booking
from database import Base, SessionLocal, engine
from models import Package, User
from schemas import BookingInput


def main():
    password = os.environ.get("DEMO_PASSWORD") or getpass("Password for the demo users (at least 8 characters): ")
    if len(password) < 8 or len(password.encode()) > 72:
        raise SystemExit("Password must be at least 8 characters and at most 72 UTF-8 bytes")
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for username, role in (("admin", "admin"), ("traveller1", "user"), ("traveller2", "user")):
            if not db.scalar(select(User).where(User.username == username)):
                db.add(User(username=username, role=role, password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()))
        if not db.scalar(select(Package.id).limit(1)):
            entries = [
                ("Kashmir Explorer", "Srinagar", 5, 24000, 8),
                ("Coastal Escape", "Goa", 3, 12000, 12),
                ("Desert Trails", "Jaisalmer", 4, 18000, 10),
                ("Mountain Retreat", "Manali", 5, 21000, 10),
                ("Backwater Journey", "Alleppey", 4, 16500, 8),
                ("Heritage Walk", "Jaipur", 3, 13500, 15),
                ("Tea Country", "Munnar", 4, 17000, 10),
                ("Island Discovery", "Port Blair", 6, 30000, 6),
                ("City of Lakes", "Udaipur", 3, 14500, 12),
                ("Himalayan Views", "Gangtok", 6, 26000, 8),
            ]
            for index, (title, destination, duration, price, capacity) in enumerate(entries):
                db.add(Package(title=title, destination=destination, duration_days=duration, price=price,
                               capacity=capacity, start_date=date.today() + timedelta(days=30 + index * 3), active=True))
        db.commit()
        users = [db.scalar(select(User).where(User.username == name)) for name in ("traveller1", "traveller2")]
        items = db.scalars(select(Package).order_by(Package.id).limit(3)).all()
        for index, item in enumerate(items):
            create_booking(db, users[index % 2], BookingInput(lines=[{"item_id": item.id, "quantity": 1}]), f"demo-seed-{index}")
    print("Schema and demo data initialized. Existing users and packages were not overwritten.")


if __name__ == "__main__":
    main()
