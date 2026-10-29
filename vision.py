"""
vision.py - AI Vision Engine for EchoMap
Sends desk images to Nexus AI API (OpenAI-compatible) for object detection.
Falls back to graceful mock mode when no API key is configured.
Team PythonCharlie | University of Bedfordshire HCI + AI + XR Hackathon
"""

import base64
import io
import json
import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel, Field, ValidationError

from spatial import region

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration — Nexus AI (OpenAI-compatible)
# ---------------------------------------------------------------------------
NEXUS_BASE_URL = os.getenv("NEXUS_BASE_URL", "https://nexusapi.navigatelabs.ai").rstrip("/")
NEXUS_API_KEY = os.getenv("NEXUS_API_KEY", "").strip()
NEXUS_MODEL = os.getenv("NEXUS_MODEL", "gemini-3.1-flash-lite").strip()

# Fallback model list (vision-capable models on Nexus)
FALLBACK_MODELS = ["gemini-3.1-flash-lite", "claude-haiku-4-5", "gemini-3.1-flash-image"]

# Legacy Gemini env var aliases (kept for backward compat)
_LEGACY_KEY = os.getenv("GEMINI_API_KEY", "").strip()
_LEGACY_MODEL = os.getenv("GEMINI_MODEL", "").strip()
if not NEXUS_API_KEY and _LEGACY_KEY:
    NEXUS_API_KEY = _LEGACY_KEY
if not NEXUS_MODEL and _LEGACY_MODEL:
    NEXUS_MODEL = _LEGACY_MODEL


class DetectedObject(BaseModel):
    name: str
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    visible: bool = True


MOCK_DESK_ITEMS = [
    {"name": "phone",        "x": 0.28, "y": 0.52, "confidence": 0.95, "visible": True},
    {"name": "keys",         "x": 0.35, "y": 0.48, "confidence": 0.90, "visible": True},
    {"name": "coffee mug",   "x": 0.82, "y": 0.25, "confidence": 0.92, "visible": True},
    {"name": "notebook",     "x": 0.55, "y": 0.70, "confidence": 0.88, "visible": True},
    {"name": "pen",          "x": 0.42, "y": 0.68, "confidence": 0.85, "visible": True},
    {"name": "laptop",       "x": 0.50, "y": 0.28, "confidence": 0.98, "visible": True},
    {"name": "water bottle", "x": 0.88, "y": 0.40, "confidence": 0.91, "visible": True},
    {"name": "glasses",      "x": 0.18, "y": 0.35, "confidence": 0.86, "visible": True},
]

# Expose API_KEY and MODEL_NAME as module-level names (used by server.py)
API_KEY = NEXUS_API_KEY
MODEL_NAME = NEXUS_MODEL


def is_api_configured() -> bool:
    """Checks whether a valid Nexus AI API key is configured."""
    return bool(API_KEY and API_KEY not in ("your_gemini_api_key_here", "your_nexus_api_key_here"))


def update_api_config(new_key: str, new_model: Optional[str] = None) -> Dict[str, Any]:
    """Updates runtime API key and model, persisting them to .env file."""
    global API_KEY, MODEL_NAME, NEXUS_API_KEY, NEXUS_MODEL
    cleaned_key = (new_key or "").strip()
    if cleaned_key:
        API_KEY = cleaned_key
        NEXUS_API_KEY = cleaned_key
        os.environ["NEXUS_API_KEY"] = API_KEY

    if new_model and new_model.strip():
        MODEL_NAME = new_model.strip()
        NEXUS_MODEL = MODEL_NAME
        os.environ["NEXUS_MODEL"] = MODEL_NAME

    # Persist to .env
    from pathlib import Path
    env_path = Path(__file__).parent / ".env"
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(
                f"# EchoMap Configuration\n"
                f"NEXUS_API_KEY={API_KEY}\n"
                f"NEXUS_BASE_URL={NEXUS_BASE_URL}\n"
                f"NEXUS_MODEL={MODEL_NAME}\n"
            )
    except Exception:
        pass

    return {
        "configured": is_api_configured(),
        "model": MODEL_NAME,
        "masked_key": (API_KEY[:6] + "..." + API_KEY[-4:]) if len(API_KEY) > 10 else ("***" if API_KEY else ""),
    }


def verify_nexus_connection(test_key: str, test_model: str) -> Dict[str, Any]:
    """Attempts a lightweight verification call to Nexus AI to validate the key."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=test_key, base_url=f"{NEXUS_BASE_URL}/v1")
        resp = client.chat.completions.create(
            model=test_model or MODEL_NAME,
            messages=[{"role": "user", "content": "Respond with only the word OK"}],
            max_tokens=5,
        )
        reply = resp.choices[0].message.content.strip() if resp.choices else ""
        return {"valid": True, "message": f"Connected to Nexus AI — response: {reply}"}
    except Exception as e:
        return {"valid": False, "message": str(e)}


# Alias so server.py import still works
def verify_gemini_connection(test_key: str, test_model: str) -> Dict[str, Any]:
    """Alias → verify_nexus_connection (backward compat)."""
    return verify_nexus_connection(test_key, test_model)


def clean_json_response(raw_text: str) -> str:
    """Extracts JSON array from potential Markdown backticks or preambles."""
    cleaned = raw_text.strip()
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1].strip()
    return cleaned


def _image_to_base64(image: Image.Image) -> str:
    """Converts PIL image to base64 JPEG data URI for the vision API."""
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=88)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


VISION_PROMPT = """You are the spatial perception system for EchoMap, an assistant for blind individuals.
Analyze this desk or room workspace photo and identify ALL distinct everyday objects.

Instructions:
1. Detect each separate physical item (e.g. phone, keys, mug, water bottle, laptop, pen, notebook, glasses, charger, mouse, keyboard, monitor, headphones, lamp, wallet, plant).
2. For every item, estimate its normalized 2D center position on the desk/table surface:
   - x: from 0.05 (far left of desk) to 0.95 (far right of desk)
   - y: from 0.05 (far back / top edge of desk) to 0.95 (near front / closest edge to user)
   IMPORTANT: DO NOT set x=1.0 or y=1.0 unless an item is literally falling off the edge. Spread out coordinates realistically according to where each item sits on the table.
3. If multiple similar items exist (e.g. 2 pens or 2 cups), list them as "pen 1", "pen 2" with their distinct positions.
4. Output up to 15 real, distinct visible objects. Do not group them all at (1.0, 1.0).

Return ONLY a valid JSON array. Each element:
{
  "name": "short object name",
  "x": 0.35,
  "y": 0.48,
  "confidence": 0.92,
  "visible": true
}"""


def scan_desk(image: Image.Image, force_mock: bool = False) -> List[Dict[str, Any]]:
    """
    Scans a desk image to identify objects and their normalized coordinates.
    Uses Nexus AI (OpenAI-compatible) vision API when configured.
    Returns a list of dicts with name, x, y, confidence, visible, and region_desc.
    """
    # Ensure image is fully loaded and in RGB mode
    if isinstance(image, Image.Image):
        image.load()
        if image.mode != "RGB":
            image = image.convert("RGB")

    if force_mock or not is_api_configured():
        # Offline / mock demonstration fallback
        results = []
        for item in MOCK_DESK_ITEMS:
            obj = dict(item)
            obj["region_desc"] = region(obj["x"], obj["y"])
            results.append(obj)
        return results

    from openai import OpenAI
    client = OpenAI(api_key=API_KEY, base_url=f"{NEXUS_BASE_URL}/v1")
    img_b64 = _image_to_base64(image)

    models_to_try = [MODEL_NAME] + [m for m in FALLBACK_MODELS if m != MODEL_NAME]
    last_err = None

    for model_name in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                            },
                            {"type": "text", "text": VISION_PROMPT},
                        ],
                    }
                ],
                max_tokens=1024,
            )
            raw_text = response.choices[0].message.content or ""
            json_str = clean_json_response(raw_text)
            data = json.loads(json_str)

            validated_objects: List[Dict[str, Any]] = []
            for entry in data:
                try:
                    entry["x"] = max(0.0, min(1.0, float(entry.get("x", 0.5))))
                    entry["y"] = max(0.0, min(1.0, float(entry.get("y", 0.5))))
                    entry["confidence"] = max(0.0, min(1.0, float(entry.get("confidence", 0.8))))
                    validated = DetectedObject(**entry)
                    if validated.visible:
                        item_dict = validated.model_dump()
                        item_dict["name"] = item_dict["name"].strip().lower()
                        item_dict["region_desc"] = region(item_dict["x"], item_dict["y"])
                        validated_objects.append(item_dict)
                except (ValidationError, TypeError, ValueError):
                    continue

            return validated_objects

        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"EchoMap Vision API Error (Nexus AI): {str(last_err)}")
