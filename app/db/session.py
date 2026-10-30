from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

id="m2o5z8"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./paidpilot.db")

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
