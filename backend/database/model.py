import json
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, ForeignKey, DateTime, TypeDecorator, Float
from database.db import Base

# Custom TypeDecorator to save list elements as a string block inside SQLite naturally
class JSONTextList(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return "[]"

    def process_result_value(self, value, dialect):
        if value:
            return json.loads(value)
        return []

# Custom TypeDecorator to save JSON dictionary data inside SQLite naturally
class JSONData(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value:
            return json.loads(value)
        return None

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    brand: Mapped[str] = mapped_column(String, index=True, nullable=True)
    model_name: Mapped[str] = mapped_column(String, index=True, nullable=True)
    color: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    search_query: Mapped[str] = mapped_column(String, index=True, nullable=False)
    # Stores the specification tags seamlessly as text inside SQLite while reading as a list in Python
    specification: Mapped[list[str]] = mapped_column(JSONTextList, default=[])
    # Stores normalized product bounding box coordinate maps (xmin, ymin, xmax, ymax)
    bounding_box: Mapped[dict | None] = mapped_column(JSONData, nullable=True)
    image_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    scraped_results = relationship("ScrapedResult", back_populates="product", cascade="all, delete-orphan")

class ScrapedResult(Base):
    __tablename__ = "scraped_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    # Core fields for the frontend layout matrix
    title: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)  # Stored as Float to sort mathematically in ascending order
    currency: Mapped[str] = mapped_column(String, default="INR")
    source_website: Mapped[str] = mapped_column(String, nullable=False)  # e.g., "Amazon", "eBay"
    product_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Cache lifecycle configuration metric
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="scraped_results")
    