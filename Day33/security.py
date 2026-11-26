import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import User

basic = HTTPBasic()
_dummy_hash = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def current_user(credentials: HTTPBasicCredentials = Depends(basic), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == credentials.username))
    candidate = credentials.password.encode()
    valid = len(candidate) <= 72 and bcrypt.checkpw(candidate, (user.password_hash.encode() if user else _dummy_hash))
    if not user or not valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials", headers={"WWW-Authenticate": "Basic"})
    return user


def admin_user(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return user
