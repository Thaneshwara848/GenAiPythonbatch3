import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

import models
from api import router as api_router
from business import seed
from chat import router as chat_router
from database import Base, SessionLocal, engine
from rag import router as document_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(title="Food AI Capstone", lifespan=lifespan)
app.include_router(api_router)
app.include_router(chat_router)
app.include_router(document_router)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

_requests = defaultdict(deque)
_lock = Lock()


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = str(uuid4())
    if request.url.path.startswith("/api/"):
        address = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with _lock:
            for key, times in list(_requests.items()):
                while times and times[0] <= now - 60:
                    times.popleft()
                if not times:
                    del _requests[key]
            times = _requests[address]
            if len(times) >= 120:
                return JSONResponse(status_code=429, content={"code": "RATE_LIMITED", "message": "Too many requests",
                                                             "request_id": request.state.request_id})
            times.append(now)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, headers=exc.headers,
                        content={"code": f"HTTP_{exc.status_code}", "message": str(exc.detail),
                                 "request_id": request.state.request_id})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"code": "VALIDATION_ERROR", "message": "Invalid request",
                                                  "request_id": request.state.request_id,
                                                  "details": [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.exception("Unexpected error, request %s", request.state.request_id)
    return JSONResponse(status_code=500, content={"code": "INTERNAL_ERROR", "message": "Unexpected server error",
                                                  "request_id": request.state.request_id})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse("frontend/index.html")
