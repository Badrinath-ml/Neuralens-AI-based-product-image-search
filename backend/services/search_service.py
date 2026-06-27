import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.exceptions import AppError, NotFoundError, ValidationError
from database.model import Product, ScrapedResult
from services.image_service import get_ai_service
from services.scraper_service import scraper_service

logger = logging.getLogger(__name__)
settings = get_settings()


class SearchService:
    async def create_from_image(
        self,
        db: AsyncSession,
        file_bytes: bytes,
        filename: str,
        content_type: Optional[str],
        base_url: str,
    ) -> Product:
        if not content_type or not content_type.startswith("image/"):
            raise ValidationError("Invalid file format. Only image uploads are supported.")

        if len(file_bytes) > settings.max_upload_bytes:
            raise ValidationError(f"File exceeds maximum size of {settings.max_upload_mb}MB.")

        if len(file_bytes) == 0:
            raise ValidationError("Uploaded file is empty.")

        os.makedirs(settings.media_dir, exist_ok=True)
        safe_filename = f"scan_{os.urandom(4).hex()}_{filename}"
        local_path = os.path.join(settings.media_dir, safe_filename)

        try:
            with open(local_path, "wb") as buffer:
                buffer.write(file_bytes)

            ai_service = get_ai_service()
            result = await ai_service.analyze_image(local_path)

            public_url = f"{base_url.rstrip('/')}/media/{safe_filename}"
            product = Product(
                model_name=result.get("model_name"),
                brand=result.get("brand"),
                color=result.get("color"),
                specification=result.get("specification", []),
                bounding_box=result.get("bounding_box"),
                description=result.get("description"),
                search_query=result.get("search_query"),
                image_path=public_url,
            )
            db.add(product)
            await db.commit()
            await db.refresh(product)
            return product

        except AppError:
            await db.rollback()
            if os.path.exists(local_path):
                os.remove(local_path)
            raise
        except Exception as exc:
            await db.rollback()
            if os.path.exists(local_path):
                os.remove(local_path)
            logger.exception("Image analysis pipeline failed")
            raise ValidationError(f"Image analysis failed: {exc}") from exc

    async def create_from_text(self, db: AsyncSession, query: str) -> Product:
        clean_query = query.strip()
        if len(clean_query) < 2:
            raise ValidationError("Search query must be at least 2 characters.")

        product = Product(
            brand=None,
            model_name=clean_query,
            color=None,
            specification=[],
            bounding_box=None,
            description=f"Text search: {clean_query}",
            search_query=clean_query,
            image_path=f"{settings.api_url.rstrip('/')}/media/placeholder.svg",
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product

    async def get_product(self, db: AsyncSession, product_id: int) -> Product:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalars().first()
        if not product:
            raise NotFoundError("Product scan not found.")
        return product

    async def get_latest(self, db: AsyncSession) -> Optional[Product]:
        result = await db.execute(select(Product).order_by(Product.id.desc()).limit(1))
        return result.scalars().first()

    async def list_products(
        self, db: AsyncSession, page: int = 1, page_size: int = 10
    ) -> tuple[list[Product], int]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 50)
        offset = (page - 1) * page_size

        count_result = await db.execute(select(func.count()).select_from(Product))
        total = count_result.scalar() or 0

        result = await db.execute(
            select(Product).order_by(Product.id.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_prices_for_product(
        self, db: AsyncSession, product: Product, force_refresh: bool = False
    ) -> list[ScrapedResult]:
        if not force_refresh:
            cached = await self._get_cached_prices(db, product.id)
            if cached:
                return cached

            cross_cached = await self._copy_cross_cache(db, product)
            if cross_cached:
                return cross_cached

        if not product.search_query:
            return []

        scraped = await scraper_service.fetch_prices_api(product.search_query)
        if not scraped:
            return []

        if force_refresh:
            existing = await db.execute(
                select(ScrapedResult).where(ScrapedResult.product_id == product.id)
            )
            for row in existing.scalars().all():
                await db.delete(row)

        records: list[ScrapedResult] = []
        for item in scraped:
            record = ScrapedResult(
                product_id=product.id,
                title=item["title"],
                price=item["price"],
                currency=item["currency"],
                source_website=item["source_website"],
                product_url=item["product_url"],
                thumbnail_url=item["thumbnail_url"],
            )
            db.add(record)
            records.append(record)

        await db.commit()
        return sorted(records, key=lambda item: item.price)

    async def get_prices_by_product_id(
        self, db: AsyncSession, product_id: int, force_refresh: bool = False
    ) -> list[ScrapedResult]:
        product = await self.get_product(db, product_id)
        return await self.get_prices_for_product(db, product, force_refresh=force_refresh)

    async def get_chat_context(self, db: AsyncSession, product_id: int) -> tuple[Product, list[ScrapedResult]]:
        product = await self.get_product(db, product_id)
        prices = await self.get_prices_for_product(db, product)
        return product, prices

    async def _get_cached_prices(self, db: AsyncSession, product_id: int) -> list[ScrapedResult]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.cache_ttl_hours)
        result = await db.execute(
            select(ScrapedResult).where(
                ScrapedResult.product_id == product_id,
                ScrapedResult.fetched_at >= cutoff,
            )
        )
        items = list(result.scalars().all())
        return sorted(items, key=lambda item: item.price) if items else []

    async def _copy_cross_cache(self, db: AsyncSession, product: Product) -> list[ScrapedResult]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.cache_ttl_hours)
        result = await db.execute(
            select(ScrapedResult)
            .join(Product, ScrapedResult.product_id == Product.id)
            .where(
                Product.search_query == product.search_query,
                Product.id != product.id,
                ScrapedResult.fetched_at >= cutoff,
            )
            .order_by(ScrapedResult.fetched_at.desc())
        )
        historical = result.scalars().first()
        if not historical:
            return []

        source_result = await db.execute(
            select(ScrapedResult).where(
                ScrapedResult.product_id == historical.product_id,
                ScrapedResult.fetched_at >= cutoff,
            )
        )
        source_items = list(source_result.scalars().all())
        if not source_items:
            return []

        copied: list[ScrapedResult] = []
        for item in source_items:
            record = ScrapedResult(
                product_id=product.id,
                title=item.title,
                price=item.price,
                currency=item.currency,
                source_website=item.source_website,
                product_url=item.product_url,
                thumbnail_url=item.thumbnail_url,
            )
            db.add(record)
            copied.append(record)

        await db.commit()
        return sorted(copied, key=lambda item: item.price)


search_service = SearchService()
