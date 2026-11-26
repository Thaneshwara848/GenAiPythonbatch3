from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings


class Base(DeclarativeBase):
    pass


engine_options = {"pool_pre_ping": True}
if settings().database_url.startswith("mysql"):
    engine_options["isolation_level"] = "READ COMMITTED"
engine = create_engine(settings().database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
