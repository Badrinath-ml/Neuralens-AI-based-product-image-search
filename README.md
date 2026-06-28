# NeuralLens — AI Product Image Search

Production-grade AI product search platform: snap or stream a product with your camera, get instant brand/model/spec extraction, live market prices, and an AI assistant to compare deals.

## Architecture

```
┌─────────────────────────────────────────────┐
│         React Frontend (NeuralLens UI)      │
│                                             │
│  Text Search  │  Upload Image  │  🎥 Camera │
└───────────────┬─────────────────────────────┘
                │  REST + Multipart (bytes)
                ▼
┌────────────────────────────────────────────────────┐
│                  FastAPI Backend                    │
│  (read-only filesystem safe — zero disk writes)    │
│                                                    │
│  /search    /detect (cloud)    /chat    /health    │
└───────────┬──────────────┬────────────┬────────────┘
            │              │            │
            ▼              ▼            ▼
   Gemini 2.5 Flash  Ultralytics HUB  SerpAPI Shopping
   vision analysis   Cloud Inference  (price comparison)
   (LangChain)       API (async httpx)      │
            │                               ▼
            ▼                        HuggingFace LLM
      SQLite + media storage         (streaming chat)
```

## Features

| Feature | Description |
|---------|-------------|
| 🖼️ **Visual Search** | Upload any product image — Gemini extracts brand, model, specs, search query |
| 🔤 **Text Search** | Search by product name without an image |
| 🎥 **Browser Camera** | Snapshot or Live AR Lens mode directly in the browser (no app needed) |
| 🔴 **Live AR Object Detection** | Real-time cloud bounding boxes overlaid on the webcam feed every 1.5 s |
| 📦 **Cloud Detection** | Highlights detected product with bounding box overlay on results page |
| 💰 **Price Comparison** | SerpAPI Google Shopping results with 24 h cache |
| 🤖 **AI Chat** | Context-aware follow-up Q&A using scan + price data |
| 🔁 **Background Price Fetch** | Prices load automatically after upload; UI polls until ready |
| 🕐 **Search History** | Recent scans accessible from the home page |
| ☁️ **Serverless-safe** | All image processing happens in memory — no disk writes required |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- API keys: `GOOGLE_API_KEY`, `SERPAPI_KEY`, `HUGGINGFACEHUB_API_TOKEN`
- Optional: `DETECTION_API_URL` + `DETECTION_API_KEY` from [Ultralytics HUB](https://hub.ultralytics.com)

### Backend

```bash
cd Backend
cp .env.example .env
# Edit .env with your API keys

uv sync
uv run python -m uvicorn main:app --reload
```

API docs: http://127.0.0.1:8000/docs

### Frontend

```bash
cd Frontend
npm install
npm run dev
```

App: http://127.0.0.1:5173

### Docker (Full Stack)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/ai/search` | Unified search (image file or `?query=` param) |
| `POST` | `/api/v1/ai/search/text` | Text-only product search |
| `POST` | `/api/v1/ai/search/upload` | Image upload (legacy / camera) |
| `GET` | `/api/v1/ai/search/{id}` | Full result with prices + status |
| `GET` | `/api/v1/ai/search/history` | Paginated search history |
| `GET` | `/api/v1/ai/search/latest` | Latest scan (polling) |
| `GET` | `/api/v1/ai/search/results/{id}` | Price listings only |
| `POST` | `/api/v1/ai/detect` | Live cloud object detection (browser AR Lens) |
| `POST` | `/api/v1/ai/chat/{session_id}` | Streaming AI chat (text/plain) |
| `POST` | `/api/v1/ai/camera/upload` | Trigger local OpenCV webcam UI (server-side, desktop only) |
| `GET` | `/health` | Health check with DB status |
| `GET` | `/media/{file}` | Static uploaded images |

## User Workflow

1. **Home** — type a query, upload an image, or click **Camera** to open the browser lens
2. **Camera Lens** — choose *Snapshot* (capture + search) or *Live AR* (real-time cloud detection labels on feed; click any box to search)
3. **Analyze** — backend runs Gemini vision + cloud object detection, saves product to DB
4. **Fetch prices** — background task queries SerpAPI; frontend polls until ready
5. **Results** — Shopping tab shows price cards; About tab shows detection overlay; Chat tab for AI Q&A
6. **History** — recent scans accessible from home page

## Environment Variables

See `Backend/.env.example` for the full template.

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini 2.5 Flash vision API key |
| `SERPAPI_KEY` | For prices | Google Shopping search |
| `HUGGINGFACEHUB_API_TOKEN` | For chat | LLM chat assistant |
| `DETECTION_API_URL` | For detection | Ultralytics HUB inference endpoint URL |
| `DETECTION_API_KEY` | For detection | Ultralytics HUB API key (`x-api-key` header) |
| `CORS_ORIGINS` | No | Comma-separated frontend URLs |
| `CACHE_TTL_HOURS` | No | Price cache TTL (default 24) |
| `MAX_UPLOAD_MB` | No | Max image size (default 10) |

## Tests

```bash
cd Backend
uv sync --extra dev
uv run pytest -v
```

## Project Structure

```
├── Backend/          # FastAPI API, ML pipeline, SQLite
├── Frontend/         # React + Vite + TypeScript UI
├── docker-compose.yml
└── README.md
```

## Security Notes

- Never commit `.env` files — use `.env.example` as template
- Rotate keys if they were ever exposed in version control
- Set `CORS_ORIGINS` to your production domain before deploying
- The server-side `/camera/upload` endpoint requires a local display + OpenCV — not for headless/cloud servers
- The browser `/detect` camera endpoint is fully web-based and works anywhere
- All image bytes are processed in memory — no temp files created on the server filesystem
