import secrets

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import User

basic = HTTPBasic()
_dummy = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt())


def current_user(credentials: HTTPBasicCredentials = Depends(basic), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == credentials.username))
    try:
        valid = bcrypt.checkpw(credentials.password.encode(), (user.password_hash.encode() if user else _dummy))
    except ValueError:
        valid = False
    if not valid or user is None:
        raise HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Basic"})
    return user


def admin_user(user: User = Depends(current_user)):
    if not secrets.compare_digest(user.role, "admin"):
        raise HTTPException(403, "Administrator access required")
    return user
