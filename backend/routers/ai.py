import json
import logging
import threading
from typing import Annotated

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Request, Query, BackgroundTasks
from fastapi.responses import Response, StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.exceptions import AppError
from database.db import get_db, session_factory
from schemas.schema import (
    ScanResponse,
    ScrapedResultResponse,
    SearchResultResponse,
    LatestResultResponse,
    SearchListResponse,
    TextSearchRequest,
    ChatRequest,
    SearchStatus,
)
from services.search_service import search_service
from services.assistent_service import ProductAssistant
from services.camera_service import cam_mode
from services import lens_service
from services.image_service import get_ai_service

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


async def _fetch_prices_background(product_id: int) -> None:
    async with session_factory() as db:
        try:
            await search_service.get_prices_by_product_id(db, product_id)
            logger.info("Background price fetch completed for product %s", product_id)
        except Exception:
            logger.exception("Background price fetch failed for product %s", product_id)


@router.post("/search", response_model=SearchResultResponse, status_code=status.HTTP_201_CREATED)
async def unified_search(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile | None = File(None),
    query: str | None = Query(None, min_length=2, max_length=200),
):
    """
    Google-like unified search entry point.
    Accepts either an image upload or a text query.
    Automatically triggers background price fetching.
    """
    base_url = str(request.base_url)

    if file and file.filename:
        content = await file.read()
        product = await search_service.create_from_image(
            db, content, file.filename, file.content_type, base_url
        )
    elif query:
        product = await search_service.create_from_text(db, query.strip())
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either an image file or a text query.",
        )

    background_tasks.add_task(_fetch_prices_background, product.id)

    return SearchResultResponse(
        product=product,
        prices=[],
        status=SearchStatus.FETCHING_PRICES,
        price_count=0,
    )


@router.post("/search/upload", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def search_product_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    """Legacy image upload endpoint — kept for camera integration."""
    content = await file.read()
    product = await search_service.create_from_image(
        db, content, file.filename or "upload.jpg", file.content_type, str(request.base_url)
    )
    background_tasks.add_task(_fetch_prices_background, product.id)
    return product


@router.post("/search/text", response_model=SearchResultResponse, status_code=status.HTTP_201_CREATED)
async def search_product_text(
    payload: TextSearchRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    product = await search_service.create_from_text(db, payload.query)
    background_tasks.add_task(_fetch_prices_background, product.id)
    return SearchResultResponse(
        product=product,
        prices=[],
        status=SearchStatus.FETCHING_PRICES,
        price_count=0,
    )


@router.get("/search/latest", response_model=LatestResultResponse)
async def get_latest_product(db: Annotated[AsyncSession, Depends(get_db)]):
    product = await search_service.get_latest(db)
    if not product:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    prices = await search_service.get_prices_for_product(db, product)
    return LatestResultResponse(product=product, prices=prices)


@router.get("/search/history", response_model=SearchListResponse)
async def list_searches(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    items, total = await search_service.list_products(db, page, page_size)
    return SearchListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/search/results/{product_id}", response_model=list[ScrapedResultResponse])
async def get_product_prices(
    product_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh: bool = Query(False),
):
    prices = await search_service.get_prices_by_product_id(db, product_id, force_refresh=refresh)
    if not prices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No price listings found yet. Try again shortly.",
        )
    return prices


@router.get("/search/{product_id}", response_model=SearchResultResponse)
async def get_search_result(
    product_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh: bool = Query(False),
):
    product = await search_service.get_product(db, product_id)
    prices = await search_service.get_prices_for_product(db, product, force_refresh=refresh)

    status_value = SearchStatus.COMPLETE if prices else SearchStatus.FETCHING_PRICES
    return SearchResultResponse(
        product=product,
        prices=prices,
        status=status_value,
        price_count=len(prices),
    )


@router.post("/camera/upload", status_code=status.HTTP_201_CREATED)
async def camera_search(mode: str = "snapshot"):
    if mode not in ["snapshot", "stream"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'snapshot' or 'stream'.")

    if mode == "snapshot":
        if cam_mode.is_active:
            raise HTTPException(status_code=409, detail="Webcam snapshot viewfinder is already active.")
        threading.Thread(target=cam_mode.start_lens_camera, daemon=True).start()
    else:
        if lens_service.is_active:
            raise HTTPException(status_code=409, detail="Webcam stream viewfinder is already active.")
        threading.Thread(target=lens_service.start_realtime_lens, daemon=True).start()

    return {"status": "success", "message": f"Webcam viewfinder ({mode} mode) triggered successfully."}


@router.post("/detect", status_code=status.HTTP_200_OK)
async def detect_objects(
    file: UploadFile = File(...),
):
    """
    Endpoint for live camera object detection on the frontend.
    Passes image bytes directly to the cloud detection API — no temp files,
    no disk writes, safe on read-only serverless filesystems (Vercel, Render, etc.).
    """
    content = await file.read()
    mime = file.content_type or "image/jpeg"
    ai_service = get_ai_service()
    detected = await ai_service.detect_all_objects_from_bytes(content, mime)
    return {"objects": detected}


@router.post("/chat/{session_id}")
async def chat_with_session_stream(
    session_id: int,
    payload: ChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        product, prices = await search_service.get_chat_context(db, session_id)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    seen_keys: set[tuple] = set()
    price_context = []
    for item in prices:
        key = (item.title.strip().lower(), item.source_website.strip().lower(), item.price)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        price_context.append({
            "title": item.title,
            "price": item.price,
            "currency": item.currency,
            "source": item.source_website,
            "url": item.product_url,
        })
        if len(price_context) >= 8:
            break

    contextual_prompt = (
        "You are NeuralLens AI, an expert product search assistant.\n"
        "Answer using the scan data below. State prices in Indian Rupees (₹) when applicable.\n\n"
        f"[PRODUCT]\n"
        f"- Brand: {product.brand or 'Unknown'}\n"
        f"- Model: {product.model_name or 'Unknown'}\n"
        f"- Color: {product.color or 'Unknown'}\n"
        f"- Search Query: {product.search_query}\n"
        f"- Specs: {', '.join(product.specification or [])}\n"
        f"- Description: {product.description or 'N/A'}\n"
        f"- Bounding Box: {json.dumps(product.bounding_box)}\n\n"
        f"[MARKET PRICES — deduplicated, sorted low to high]\n"
        f"{json.dumps(sorted(price_context, key=lambda x: x['price']), indent=2)}\n\n"
        "RESPONSE FORMAT RULES:\n"
        "1. Start with a direct 1-sentence answer to the user's question.\n"
        "2. Use markdown for structure: headings (###), bullet lists, or GFM tables when comparing prices.\n"
        "3. Never repeat the same listing twice.\n"
        "4. For price comparisons, prefer a clean markdown table with columns: Store | Product | Price.\n"
        "5. End with a brief recommendation when relevant.\n"
        "6. Keep responses concise — under 200 words unless the user asks for detail."
    )

    formatted_history = []
    for msg in payload.chat_history:
        if msg.get("sender") == "user":
            formatted_history.append(HumanMessage(content=msg.get("text", "")))
        elif msg.get("sender") == "assistant":
            formatted_history.append(AIMessage(content=msg.get("text", "")))

    assistant = ProductAssistant(contextual_system_prompt=contextual_prompt)

    async def token_generator():
        try:
            async for chunk in assistant.chain.astream({
                "chat_history": formatted_history,
                "question": payload.query,
            }):
                yield chunk
        except Exception as err:
            logger.exception("Chat stream error")
            yield f"\n[Error]: Unable to complete response. {err}"

    return StreamingResponse(token_generator(), media_type="text/plain")
