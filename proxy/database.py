import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.dialects import postgresql
from dotenv import load_dotenv
import datetime
load_dotenv()

DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

class RequestLog(Base):
    __tablename__ = "analytics_requestlog"
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(postgresql.INET, nullable=False)
    country = Column(String(100))
    path = Column(String(500))
    method = Column(String(10))
    user_agent = Column(String(300))
    referrer = Column(String(300))
    response_time = Column(Float)
    timestamp = Column(DateTime)
    http_status = Column(Integer)

class BlockedCountry(Base):
    __tablename__ = "analytics_blockedcountry"
    id = Column(Integer, primary_key=True)
    country_name = Column(String, unique=True, index=True)
    reason = Column(String, nullable=True)
    blocked_at = Column(DateTime)