# NeuralLens Frontend

React + TypeScript web client for **NeuralLens** — a modern AI product search interface with browser camera capture, live AR object detection, visual search, real-time price comparison, and context-aware chat.

## Stack

| Layer | Technology |
|-------|------------|
| Framework | React 19 |
| Build | Vite 6 |
| Routing | React Router 7 |
| Styling | Tailwind CSS 4 + CSS custom properties |
| Fonts | Inter + Space Grotesk (Google Fonts) |
| Language | TypeScript 5 |

## Features

| Feature | Description |
|---------|-------------|
| 🔤 **Text Search** | Search products by name, brand or model |
| 🖼️ **Image Upload** | Visual search via file upload |
| 🎥 **Browser Camera** | Full webcam interface — no native app needed |
| 📸 **Snapshot Mode** | Capture a photo and search instantly |
| 🔴 **Live AR Lens** | Real-time YOLO bounding box overlays on the webcam feed; click any detected object to search it |
| 💰 **Price Comparison** | Auto-polling for market prices until ready |
| 🤖 **AI Chat** | Streaming follow-up Q&A with product + price context |
| 🌗 **Dark / Light Theme** | Persisted in `localStorage`; respects system preference |
| ⚠️ **Rate Limit Banner** | Clear user-friendly message when Gemini API quota is hit |
| 🕐 **Search History** | Recent scans on the home page |

## Project Structure

```
Frontend/
├── public/
│   └── favicon.svg
├── src/
│   ├── api/
│   │   └── client.ts              # All API calls + 429 rate limit detection
│   ├── components/
│   │   ├── CameraModal.tsx        # 🆕 Browser camera — snapshot + Live AR Lens
│   │   ├── Logo.tsx               # NeuralLens branding
│   │   ├── SearchBar.tsx          # Text + upload + camera button
│   │   ├── PriceGrid.tsx          # Shopping result cards
│   │   ├── BoundingBoxOverlay.tsx # YOLO bounding box on product image
│   │   ├── ChatPanel.tsx          # Streaming AI chat
│   │   ├── LoadingSpinner.tsx
│   │   └── ThemeToggle.tsx        # Dark / light switch
│   ├── context/
│   │   └── ThemeContext.tsx       # Theme state + persistence
│   ├── pages/
│   │   ├── HomePage.tsx           # Search entry + camera trigger
│   │   └── ResultsPage.tsx        # Results + camera trigger
│   ├── types/
│   │   └── index.ts               # ProductScan, PriceResult, DetectedObject…
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css                  # Design system tokens (CSS custom properties)
├── index.html
├── vite.config.ts
└── package.json
```

## Setup

```bash
cd Frontend
npm install
npm run dev
```

App runs at **http://127.0.0.1:5173**

The Vite dev server proxies `/api` and `/media` to the backend at `http://127.0.0.1:8000`.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server with HMR |
| `npm run build` | Type-check + production build → `dist/` |
| `npm run preview` | Preview production build locally |

## Browser Camera — How It Works

The `CameraModal` component accesses the webcam using the browser's `getUserMedia` API — no plugin or native app required.

### Snapshot Mode
1. Opens webcam feed
2. User frames the product inside the dashed guide
3. Click **Capture Photo** → JPEG blob is submitted to `/api/v1/ai/search`
4. Navigate to results page automatically

### Live AR Lens Mode
1. Opens webcam feed
2. Every **1.5 seconds**, a frame is captured and sent to `POST /api/v1/ai/detect`
3. Backend runs YOLO locally and returns all detected objects + bounding boxes
4. Glowing cyan boxes with labels are overlaid on the live video
5. Click any box → submits the current frame as a search image

> **Camera permission:** Chrome/Edge will ask for camera permission on first use. If denied, click the 🔒 lock icon in the address bar → Site settings → Camera → Allow.

## API Integration

All requests go through `src/api/client.ts`:

```typescript
searchByImage(file)           // POST multipart /search (File or Blob)
searchByText(query)           // POST JSON /search/text
getSearchResult(id)           // GET /search/:id
getSearchHistory(page)        // GET /search/history
detectObjects(blob)           // POST multipart /detect  (Live AR Lens)
streamChat(id, query, history, onToken)  // POST /chat/:id (streaming)
```

### Rate Limit Handling

`handleResponse()` checks for `status === 429` before parsing JSON and throws:

```
"Gemini API rate limit reached. Server is busy, please try again in a few moments."
```

The `HomePage` and `ResultsPage` render this in a styled alert card with an extra hint to retry. Switch the backend to Ollama to avoid this entirely — see `Backend/README.md`.

## Theme System

Themes are controlled via `data-theme="light|dark"` on `<html>`.

CSS variables in `src/index.css` define the full design system:

- `--accent` / `--cyan` — primary brand colors
- `--bg`, `--bg-elevated`, `--bg-muted` — surfaces
- `--gradient-brand` — logo and button gradients
- `--chat-user`, `--chat-assistant` — chat bubble colors

Toggle: `ThemeToggle.tsx` | Provider: `ThemeContext.tsx` (key: `neurallens-theme`)

An inline script in `index.html` applies the saved theme before React mounts to prevent flash.

## User Flow

1. **Home** — enter query, upload image, or click **Camera** to open the lens modal
2. **Camera Lens** — pick *Snapshot* or *Live AR* mode; capture or click a detected box
3. **Navigate** — redirect to `/search/:productId`
4. **Poll** — `GET /api/v1/ai/search/:id` every 2 seconds until prices arrive
5. **Browse** — Market Prices tab → cards; Scan Details → YOLO overlay; AI Assistant → streaming chat

## Production Build

```bash
npm run build
```

Serve `dist/` with any static host, or use the included `Dockerfile` + `nginx.conf` (proxies `/api` to backend).

## Docker

```bash
docker build -t neurallens-frontend .
docker run -p 3000:80 neurallens-frontend
```

Use with `docker-compose.yml` at the project root for full stack.

## Customization

| What | Where |
|------|-------|
| Brand name / logo | `components/Logo.tsx` |
| Colors / theme tokens | `src/index.css` `[data-theme="light"]` / `[data-theme="dark"]` |
| API base URL (prod) | `vite.config.ts` proxy or nginx `location /api/` |
| Poll interval | `ResultsPage.tsx` → `POLL_INTERVAL` |
| AR detection frequency | `CameraModal.tsx` → `setInterval(performLiveDetection, 1500)` |
