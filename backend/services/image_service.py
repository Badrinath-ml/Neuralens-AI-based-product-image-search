import io
import os
import logging
from typing import Optional

import httpx
from PIL import Image

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from config import get_settings
from schemas.schema import ProductCatalog

logger = logging.getLogger(__name__)
settings = get_settings()

_ai_service: Optional["AIService"] = None


class AIService:
    """
    Handles vision analysis (Gemini) and object detection.

    Object detection is delegated to the Ultralytics HUB Cloud Inference API
    so that no local model weights or heavy ML libraries (torch, ultralytics,
    opencv) are required at runtime — keeping the Render deployment image slim.
    """

    def __init__(self):
        if not settings.google_api_key and not os.getenv("GOOGLE_API_KEY"):
            raise ValueError(
                "GOOGLE_API_KEY is required for image analysis."
            )

        api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.1,
            max_retries=3,
            google_api_key=api_key,
        )
        logger.info("Gemini vision model initialized.")

        # Cloud detection endpoint — set via DETECTION_API_URL in .env
        self._detection_api_url: str = settings.detection_api_url
        self._detection_api_key: str = settings.detection_api_key

        if self._detection_api_url:
            logger.info(
                "Cloud object detection configured: %s", self._detection_api_url
            )
        else:
            logger.warning(
                "DETECTION_API_URL not set — bounding-box detection will be skipped."
            )

        self.parser = JsonOutputParser(pydantic_object=ProductCatalog)
        instructions = """\
You are an expert product cataloging and e-commerce research system.
Analyze the primary item in the image and return structured JSON.

CRITICAL SEARCH QUERY RULES:
- search_query MUST be concise commercial keywords only (Brand + Model + Key Spec).
- No conversational filler or visual descriptions.

Return ONLY valid JSON.
{format_instructions}
"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", instructions),
            ("user", [
                {"type": "text", "text": "Extract all identifiable properties of the main product in this image."},
                {"type": "image_url", "image_url": {"url": "{image_url}"}},
            ]),
        ])
        self.chain = prompt | self.llm | self.parser

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_image_bytes(self, image_path: str) -> tuple[bytes, str]:
        """Read *image_path* from disk and return (raw_bytes, mime_type)."""
        with open(image_path, "rb") as fh:
            raw = fh.read()
        # Use Pillow to reliably detect the format
        with Image.open(io.BytesIO(raw)) as img:
            fmt = (img.format or "JPEG").upper()
        mime_map = {
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
            "GIF": "image/gif",
        }
        mime = mime_map.get(fmt, "image/jpeg")
        return raw, mime

    async def _call_detection_api(self, image_bytes: bytes, mime: str) -> dict:
        """
        POST *image_bytes* to the Ultralytics HUB Cloud Inference endpoint.

        Expected response shape (subset we consume):
        {
          "images": [
            {
              "results": [
                {
                  "box": {"x1": …, "y1": …, "x2": …, "y2": …},
                  "name": "label",
                  "confidence": 0.87
                },
                …
              ],
              "shape": [height, width]
            }
          ]
        }
        Returns the raw parsed JSON dict (or raises on HTTP error).
        """
        headers: dict[str, str] = {}
        if self._detection_api_key:
            headers["x-api-key"] = self._detection_api_key

        filename = "upload.jpg" if "jpeg" in mime else "upload.png"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._detection_api_url,
                headers=headers,
                files={"file": (filename, image_bytes, mime)},
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _normalize_box(raw_box: dict, img_width: int, img_height: int) -> dict:
        """
        Convert absolute pixel coordinates returned by the HUB API
        (x1/y1/x2/y2) to the 0–1000 scale expected by the rest of the app.
        """
        xmin = raw_box.get("x1", 0)
        ymin = raw_box.get("y1", 0)
        xmax = raw_box.get("x2", img_width)
        ymax = raw_box.get("y2", img_height)
        return {
            "xmin": int((xmin / img_width) * 1000),
            "ymin": int((ymin / img_height) * 1000),
            "xmax": int((xmax / img_width) * 1000),
            "ymax": int((ymax / img_height) * 1000),
        }

    # ------------------------------------------------------------------
    # Public detection methods (same signatures as the old YOLO version)
    # ------------------------------------------------------------------

    async def detect_bounding_box_async(self, image_path: str) -> dict | None:
        """
        Async version of detect_bounding_box.
        Returns the highest-confidence bounding box in 0–1000 scale, or None.
        """
        if not self._detection_api_url:
            return None
        try:
            raw_bytes, mime = self._load_image_bytes(image_path)
            payload = await self._call_detection_api(raw_bytes, mime)

            images = payload.get("images") or []
            if not images:
                return None

            results = images[0].get("results") or []
            if not results:
                return None

            shape = images[0].get("shape", [1, 1])
            img_height, img_width = shape[0], shape[1]

            best = max(results, key=lambda r: float(r.get("confidence", 0)))
            return self._normalize_box(best["box"], img_width, img_height)

        except Exception as exc:
            logger.error("Cloud detection (bounding_box) failed: %s", exc)
            return None

    def detect_bounding_box(self, image_path: str) -> dict | None:
        """
        Synchronous shim kept for backward compatibility with callers that
        cannot await.  Schedules the async call on a new event loop.
        Prefer detect_bounding_box_async in async contexts.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We are already inside an async context (e.g. FastAPI).
                # Return None immediately; callers inside async code should
                # use detect_bounding_box_async instead.
                logger.debug(
                    "detect_bounding_box called from a running event loop; "
                    "use detect_bounding_box_async for proper async support."
                )
                return None
            return loop.run_until_complete(self.detect_bounding_box_async(image_path))
        except Exception as exc:
            logger.error("detect_bounding_box shim failed: %s", exc)
            return None

    async def detect_all_objects(self, image_path: str) -> list[dict]:
        """
        Returns a list of all detected objects (async).
        Each entry: {"box": {xmin,ymin,xmax,ymax}, "label": str, "confidence": float}
        Signature preserved from the old YOLO implementation.
        """
        if not self._detection_api_url:
            return []
        try:
            raw_bytes, mime = self._load_image_bytes(image_path)
            payload = await self._call_detection_api(raw_bytes, mime)

            images = payload.get("images") or []
            if not images:
                return []

            results = images[0].get("results") or []
            shape = images[0].get("shape", [1, 1])
            img_height, img_width = shape[0], shape[1]

            detected = []
            for item in results:
                detected.append({
                    "box": self._normalize_box(item["box"], img_width, img_height),
                    "label": item.get("name", "object"),
                    "confidence": float(item.get("confidence", 0)),
                })
            return detected

        except Exception as exc:
            logger.error("Cloud detection (all_objects) failed: %s", exc)
            return []

    async def analyze_image(self, image_path: str) -> dict:
        """
        Full pipeline: run Gemini vision analysis + cloud bounding-box detection.
        Returns the structured product dict expected by the rest of the app.
        """
        import base64
        import mimetypes
        from core.exceptions import AppError

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        mime_type, _ = mimetypes.guess_type(image_path)
        mime_type = mime_type or "image/jpeg"

        with open(image_path, "rb") as image_file:
            raw_bytes = image_file.read()
            if not raw_bytes:
                raise ValueError("Image file is empty.")
            base64_image = base64.b64encode(raw_bytes).decode("utf-8")

        computed_image_url = f"data:{mime_type};base64,{base64_image}"
        logger.info("Running vision analysis for %s (using Gemini)", image_path)

        try:
            structured_data = await self.chain.ainvoke({
                "image_url": computed_image_url,
                "format_instructions": self.parser.get_format_instructions(),
            })
        except Exception as exc:
            exc_str = str(exc).lower()
            if any(
                term in exc_str
                for term in ["resourceexhausted", "429", "quota", "rate limit", "exhausted"]
            ):
                logger.error("Gemini API rate limit hit: %s", exc)
                raise AppError(
                    "Gemini API rate limits reached. Server is busy, please try again in a few moments.",
                    status_code=429,
                ) from exc

            logger.exception("Vision analysis generation failed")
            raise AppError(f"Image analysis failed: {exc}", status_code=500) from exc

        # Async bounding-box detection — no blocking call on the event loop
        structured_data["bounding_box"] = await self.detect_bounding_box_async(image_path)
        return structured_data


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
