# NeuralLens Backend

FastAPI backend for **NeuralLens** — an AI/ML product search engine combining computer vision, structured data extraction, live market price intelligence, and a streaming chat assistant.

## Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI + Uvicorn |
| Database | SQLite (async SQLAlchemy + aiosqlite) |
| Vision (cloud) | Google Gemini 2.5 Flash via LangChain |
| Detection | Ultralytics HUB Cloud Inference API (async httpx) |
| Prices | SerpAPI Google Shopping (India) |
| Chat | LangChain + HuggingFace Router LLM |
| Camera (server) | OpenCV — local desktop only (not deployed) |
| Camera (browser) | `POST /detect` → HUB Cloud Inference API |

## Project Structure

```
Backend/
├── main.py                 # App entry, CORS, health check, lifespan
├── config.py               # Pydantic settings from .env (detection API keys, app config)
├── core/
│   ├── logging.py          # Structured stdout logging
│   └── exceptions.py       # AppError → NotFoundError / ValidationError hierarchy
├── database/
│   ├── db.py               # Async engine + session factory
│   └── model.py            # Product, ScrapedResult ORM models
├── routers/
│   └── ai.py               # All /api/v1/ai/* routes (including /detect)
├── schemas/
│   └── schema.py           # Pydantic request/response models
├── services/
│   ├── image_service.py    # Gemini vision + cloud detection pipeline
│   ├── search_service.py   # Search orchestration + price cache
│   ├── scraper_service.py  # SerpAPI price fetch
│   ├── assistent_service.py# Streaming HuggingFace chat assistant
│   ├── camera_service.py   # Server-side OpenCV webcam snapshot mode
│   └── lens_service.py     # Server-side OpenCV live AR HUD stream
├── tests/
│   ├── test_api.py
│   └── test_assistent.py
├── media_storage/          # Uploaded images served at /media/*
├── pyproject.toml
└── .env.example
```

## Setup

```bash
cd Backend
cp .env.example .env
# Fill in your API keys

uv sync
uv run python -m uvicorn main:app --reload
```

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini 2.5 Flash vision API key |
| `SERPAPI_KEY` | For prices | SerpAPI key for Google Shopping |
| `HUGGINGFACEHUB_API_TOKEN` | For chat | HuggingFace router token |
| `DETECTION_API_URL` | For detection | Ultralytics HUB inference endpoint URL |
| `DETECTION_API_KEY` | For detection | Ultralytics HUB API key (`x-api-key` header) |
| `CORS_ORIGINS` | No | Comma-separated frontend URLs |
| `DATABASE_URL` | No | Default: `sqlite+aiosqlite:///./products.db` |
| `MAX_UPLOAD_MB` | No | Max image upload size (default `10`) |
| `CACHE_TTL_HOURS` | No | Price cache TTL in hours (default `24`) |
| `API_URL` | No | Used by server-side camera services for upload callback |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/ai/search` | Unified search — image `multipart/form-data` or `?query=` text param |
| `POST` | `/api/v1/ai/search/text` | Text-only product search |
| `POST` | `/api/v1/ai/search/upload` | Image upload (legacy / camera service callback) |
| `GET` | `/api/v1/ai/search/{id}` | Full result + price status for polling |
| `GET` | `/api/v1/ai/search/history` | Paginated search history (`?page=&page_size=`) |
| `GET` | `/api/v1/ai/search/latest` | Most recent scan |
| `GET` | `/api/v1/ai/search/results/{id}` | Price listings only |
| `POST` | `/api/v1/ai/detect` | **Live object detection** — returns all objects + boxes (browser AR Lens) |
| `POST` | `/api/v1/ai/chat/{session_id}` | Streaming AI chat (`text/plain` SSE-style) |
| `POST` | `/api/v1/ai/camera/upload` | Trigger server-side OpenCV webcam UI (local desktop only) |
| `GET` | `/health` | Health check with DB connectivity status |
| `GET` | `/media/{filename}` | Static media — uploaded product images |

## Search Pipeline

```
1. Ingest     → image upload (File/Blob) or text query
2. Analyze    → Gemini 2.5 Flash extracts brand, model, color,
                specs, description, optimized search_query (JSON)
3. Detect     → Ultralytics HUB API → normalized bounding box (0–1000)
4. Persist    → Product + bounding_box saved to SQLite
5. Price Fetch→ Background task queries SerpAPI; results cached 24 h
6. Poll       → Frontend polls GET /search/{id} every 2 s until status=complete
7. Chat       → LLM receives product metadata + deduplicated price context
```

### Live AR Lens Pipeline (`/detect`)

```
Browser frame (JPEG) → POST /detect → Cloud detect_all_objects()
→ [{label, confidence, box:{xmin,ymin,xmax,ymax}}]
→ Frontend overlays glowing cyan boxes on live video
→ Click box → submit frame as /search image
```

## Rate Limit Error Handling

- **Backend**: `image_service.py` wraps `chain.ainvoke()` in try/except; detects `resourceexhausted`, `429`, `quota`, `rate limit` in the exception message and raises `AppError(status_code=429)`
- **Pipeline**: `search_service.py` catches `AppError` directly and re-raises, preserving the HTTP status code through to the client
- **Frontend**: `client.ts` checks `response.status === 429` and throws a user-friendly message; pages render a styled alert card with a retry hint

## Known Implementation Notes

### LangChain Template Escaping
JSON embedded in the chat system prompt (e.g. `json.dumps(price_context)`) contains `{` / `}` which LangChain's `ChatPromptTemplate` treats as template variables.  
**Fix:** `assistent_service.py` escapes braces via `_escape_template_literals()` before building the prompt.

## Tests

```bash
uv sync --extra dev
uv run pytest -v
# 6/6 tests pass
```

## Docker

```bash
docker build -t neurallens-backend .
docker run -p 8000:8000 --env-file .env neurallens-backend
```

Use `docker-compose.yml` at the project root for the full Frontend + Backend stack.

## Notes

- **YOLO weights** — `yolo26n.pt` must exist in the `Backend/` directory before starting
- **Server-side camera** (`/camera/upload`) requires a local display + webcam — not suitable for headless/cloud servers
- **Browser camera** (`/detect`) is fully web-based and works in any deployment
- Rotate all API keys if `.env` was ever committed to version control
