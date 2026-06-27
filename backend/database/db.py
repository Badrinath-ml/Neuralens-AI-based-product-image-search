from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=settings.debug)
session_factory = async_sessionmaker(
    expire_on_commit=False,
    class_=AsyncSession,
    bind=engine,
)


async def get_db():
    async with session_factory() as session:
        yield session
