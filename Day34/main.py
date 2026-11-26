import logging
import uuid
from collections import defaultdict, deque
from datetime import date
from decimal import Decimal
from pathlib import Path
from threading import Lock
from time import monotonic

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from booking_service import cancel_booking, create_booking, owned_booking
from database import get_db
from models import Package, User
from schemas import BookingInput, BookingResponse, PackageInput, PackageResponse, StatusInput
from security import admin_user, current_user

app = FastAPI(title="Travel AI")
logger = logging.getLogger("travel_ai")
_requests = defaultdict(deque)
_rate_lock = Lock()


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = uuid.uuid4().hex
    if request.url.path.startswith("/api/chat/") or request.url.path == "/api/documents":
        now = monotonic()
        client = request.client.host if request.client else "unknown"
        with _rate_lock:
            timestamps = _requests[client]
            while timestamps and timestamps[0] <= now - 60:
                timestamps.popleft()
            if len(timestamps) >= 30:
                return JSONResponse(status_code=429, content={"code": "rate_limited", "message": "Too many requests", "request_id": request.state.request_id})
            timestamps.append(now)
    return await call_next(request)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, headers=exc.headers,
                        content={"code": f"http_{exc.status_code}", "message": str(exc.detail), "request_id": request.state.request_id})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    errors = [{"location": list(error["loc"]), "message": error["msg"]} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"code": "validation_error", "message": "Invalid request", "request_id": request.state.request_id, "errors": errors})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.exception("Unexpected error request_id=%s", request.state.request_id)
    return JSONResponse(status_code=500, content={"code": "internal_error", "message": "Unexpected server error", "request_id": request.state.request_id})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}


@app.get("/api/packages", response_model=list[PackageResponse])
def packages(destination: str | None = None, max_price: Decimal | None = Query(None, gt=0),
             duration_days: int | None = Query(None, gt=0), start_date: date | None = None,
             db: Session = Depends(get_db)):
    query = select(Package).where(Package.active.is_(True))
    if destination:
        query = query.where(Package.destination.ilike(f"%{destination}%"))
    if max_price:
        query = query.where(Package.price <= max_price)
    if duration_days:
        query = query.where(Package.duration_days == duration_days)
    if start_date:
        query = query.where(Package.start_date == start_date)
    return db.scalars(query.order_by(Package.id)).all()


@app.get("/api/packages/{item_id}", response_model=PackageResponse)
def package(item_id: int, db: Session = Depends(get_db)):
    item = db.scalar(select(Package).where(Package.id == item_id, Package.active.is_(True)))
    if not item:
        raise HTTPException(404, "Package not found")
    return item


@app.post("/api/packages", response_model=PackageResponse, status_code=201)
def add_package(data: PackageInput, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    item = Package(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.put("/api/packages/{item_id}", response_model=PackageResponse)
def update_package(item_id: int, data: PackageInput, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    item = db.scalar(select(Package).where(Package.id == item_id).with_for_update())
    if not item:
        raise HTTPException(404, "Package not found")
    for name, value in data.model_dump().items():
        setattr(item, name, value)
    db.commit()
    return item


@app.delete("/api/packages/{item_id}", status_code=204)
def disable_package(item_id: int, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    item = db.scalar(select(Package).where(Package.id == item_id).with_for_update())
    if not item:
        raise HTTPException(404, "Package not found")
    item.active = False
    db.commit()


@app.post("/api/bookings", response_model=BookingResponse, status_code=201)
def book(data: BookingInput, key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128),
         user: User = Depends(current_user), db: Session = Depends(get_db)):
    return create_booking(db, user, data, key)


@app.get("/api/bookings", response_model=list[BookingResponse])
def bookings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from models import Booking
    return db.scalars(select(Booking).where(Booking.user_id == user.id).order_by(Booking.id.desc())).all()


@app.get("/api/bookings/{booking_id}", response_model=BookingResponse)
def booking(booking_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return owned_booking(db, booking_id, user)


@app.post("/api/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel(booking_id: int, expected_refund: Decimal | None = Query(None, ge=0),
           user: User = Depends(current_user), db: Session = Depends(get_db)):
    return cancel_booking(db, user, booking_id, expected_refund)


@app.patch("/api/admin/bookings/{booking_id}/status", response_model=BookingResponse)
def set_status(booking_id: int, data: StatusInput, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    booking = owned_booking(db, booking_id, admin, lock=True)
    if booking.status != "CONFIRMED":
        raise HTTPException(409, "Invalid status transition")
    booking.status = data.status
    db.commit()
    return booking


from chat import router as chat_router
from rag import router as rag_router

app.include_router(chat_router)
app.include_router(rag_router)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "frontend"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(Path(__file__).parent / "frontend" / "index.html")
