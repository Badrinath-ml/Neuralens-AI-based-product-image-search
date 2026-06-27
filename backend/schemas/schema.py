from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional


class SearchStatus(str, Enum):
    ANALYZING = "analyzing"
    FETCHING_PRICES = "fetching_prices"
    COMPLETE = "complete"
    FAILED = "failed"


class ProductCatalog(BaseModel):
    model_name: str = Field(description="The exact model name or model number of the item")
    brand: str|None = Field(description="The brand or manufacturer name of the product")
    color: str|None = Field(description="The primary color or color scheme of the product")
    specification: List[str] = Field(description="List of 3-4 distinct structural or design features")
    description: str = Field(description="A brief summary describing the visual properties of the item")
    search_query: str = Field(description="Optimized query string for search engines")


class ScanResponse(ProductCatalog):
    id: int
    image_path: str
    bounding_box: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Backward compatibility alias
scan = ScanResponse


class ScrapedResultResponse(BaseModel):
    id: int
    title: str
    price: float
    currency: str
    source_website: str
    product_url: str
    thumbnail_url: Optional[str] = None
    fetched_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SearchResultResponse(BaseModel):
    product: ScanResponse
    prices: List[ScrapedResultResponse]
    status: SearchStatus = SearchStatus.COMPLETE
    price_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class LatestResultResponse(BaseModel):
    product: ScanResponse
    prices: List[ScrapedResultResponse]

    model_config = ConfigDict(from_attributes=True)


class SearchListResponse(BaseModel):
    items: List[ScanResponse]
    total: int
    page: int
    page_size: int


class TextSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    chat_history: list[dict] = []


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
