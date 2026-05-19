from sqlalchemy.orm import sessionmaker, DeclarativeBase,Session
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.engine import make_url
from typing import Generator ,AsyncGenerator

from app.core.settings import settings

def _create_async_url(db_url:str)->str:
    parsed = make_url(db_url)

    if parsed.drivername =="postgresql+asyncpg":
        return db_url
    if parsed.drivername.startswith("postgresql"):
        return parsed.set(drivername="postgresql+asyncpg").render_as_string(hide_password=False)
    raise ValueError("Only Postgresql is supported so far. " \
    "Has to change _create_async_engine to user other db")

    

DATABASE_URL = settings.DATABASE_URL
ASYNC_DATABASE_URL = _create_async_url(settings.DATABASE_URL)

engine  = create_engine(url=DATABASE_URL, pool_pre_ping=True )
async_engine = create_async_engine(url=ASYNC_DATABASE_URL , pool_pre_ping=True)

SessionLocal= sessionmaker(bind = engine ,autocommit=False, autoflush=False)
AsyncSessionLocal = async_sessionmaker(bind=async_engine,expire_on_commit=False)
class Base(DeclarativeBase):
    pass

def get_db()-> Generator[Session,None,None]: 
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
    
async def get_async_db() -> AsyncGenerator[AsyncSession,None]:
   async with AsyncSessionLocal() as session:
       yield session
