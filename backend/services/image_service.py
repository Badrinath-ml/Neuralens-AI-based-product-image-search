import os
import logging
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ultralytics import YOLO

from config import get_settings
from schemas.schema import ProductCatalog

logger = logging.getLogger(__name__)
settings = get_settings()

_ai_service: Optional["AIService"] = None


class AIService:
    def __init__(self):
        if not settings.google_api_key and not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY is required for image analysis when not using Ollama.")

        api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.1,
            max_retries=3,
            google_api_key=api_key,
        )
        logger.info("Gemini vision model initialized.")

        try:
            self.yolo_model = YOLO("yolo26n.pt")
            logger.info("YOLO model loaded successfully.")
        except Exception as exc:
            logger.warning("Failed to load YOLO model: %s", exc)
            self.yolo_model = None

        self.parser = JsonOutputParser(pydantic_object=ProductCatalog)
        instructions = """
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

    def detect_bounding_box(self, image_path: str) -> dict | None:
        if self.yolo_model is None:
            return None
        try:
            results = self.yolo_model(image_path, verbose=False)
            if not results or not results[0].boxes:
                return None
            best_box = max(results[0].boxes, key=lambda x: float(x.conf[0]))
            xmin, ymin, xmax, ymax = best_box.xyxy[0].tolist()
            img_height, img_width = results[0].orig_shape[0], results[0].orig_shape[1]
            return {
                "xmin": int((xmin / img_width) * 1000),
                "ymin": int((ymin / img_height) * 1000),
                "xmax": int((xmax / img_width) * 1000),
                "ymax": int((ymax / img_height) * 1000),
            }
        except Exception as exc:
            logger.error("YOLO detection failed: %s", exc)
            return None

    def detect_all_objects(self, image_path: str) -> list[dict]:
        if self.yolo_model is None:
            return []
        try:
            results = self.yolo_model(image_path, verbose=False)
            if not results or not results[0].boxes:
                return []
            
            detected = []
            img_height, img_width = results[0].orig_shape[0], results[0].orig_shape[1]
            names = results[0].names
            
            for box in results[0].boxes:
                xmin, ymin, xmax, ymax = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = names.get(cls_id, f"object_{cls_id}")
                
                detected.append({
                    "box": {
                        "xmin": int((xmin / img_width) * 1000),
                        "ymin": int((ymin / img_height) * 1000),
                        "xmax": int((xmax / img_width) * 1000),
                        "ymax": int((ymax / img_height) * 1000),
                    },
                    "label": label,
                    "confidence": conf
                })
            return detected
        except Exception as exc:
            logger.error("YOLO multiple detection failed: %s", exc)
            return []

    async def analyze_image(self, image_path: str) -> dict:
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
        logger.info("Running vision analysis for %s (using %s)", image_path, "Ollama" if settings.use_ollama else "Gemini")

        try:
            structured_data = await self.chain.ainvoke({
                "image_url": computed_image_url,
                "format_instructions": self.parser.get_format_instructions(),
            })
        except Exception as exc:
            exc_str = str(exc).lower()
            if not settings.use_ollama and any(term in exc_str for term in ["resourceexhausted", "429", "quota", "rate limit", "exhausted"]):
                logger.error("Gemini API rate limit hit: %s", exc)
                raise AppError(
                    "Gemini API rate limits reached. Server is busy, please try again in a few moments or set up local Ollama.",
                    status_code=429
                ) from exc
            
            logger.exception("Vision analysis generation failed")
            raise AppError(f"Image analysis failed: {exc}", status_code=500) from exc

        structured_data["bounding_box"] = self.detect_bounding_box(image_path)
        return structured_data


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
