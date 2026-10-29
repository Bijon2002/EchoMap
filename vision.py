"""
vision.py - AI Vision Engine for EchoMap
Sends desk images to Google Gemini API (google-genai SDK), validates
structured spatial coordinates via Pydantic, and provides graceful offline fallback.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel, Field, ValidationError

from spatial import region

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]


class DetectedObject(BaseModel):
    name: str
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    visible: bool = True


MOCK_DESK_ITEMS = [
    {"name": "phone", "x": 0.28, "y": 0.52, "confidence": 0.95, "visible": True},
    {"name": "keys", "x": 0.35, "y": 0.48, "confidence": 0.90, "visible": True},
    {"name": "coffee mug", "x": 0.82, "y": 0.25, "confidence": 0.92, "visible": True},
    {"name": "notebook", "x": 0.55, "y": 0.70, "confidence": 0.88, "visible": True},
    {"name": "pen", "x": 0.42, "y": 0.68, "confidence": 0.85, "visible": True},
    {"name": "laptop", "x": 0.50, "y": 0.28, "confidence": 0.98, "visible": True},
    {"name": "water bottle", "x": 0.88, "y": 0.40, "confidence": 0.91, "visible": True},
    {"name": "glasses", "x": 0.18, "y": 0.35, "confidence": 0.86, "visible": True},
]


def is_api_configured() -> bool:
    """Checks whether a valid Gemini API key is configured."""
    return bool(API_KEY and API_KEY != "your_gemini_api_key_here")


def update_api_config(new_key: str, new_model: Optional[str] = None) -> Dict[str, Any]:
    """Updates runtime API key and persists it to .env file."""
    global API_KEY, MODEL_NAME
    cleaned_key = (new_key or "").strip()
    if cleaned_key:
        API_KEY = cleaned_key
        os.environ["GEMINI_API_KEY"] = API_KEY

    if new_model and new_model.strip():
        MODEL_NAME = new_model.strip()
        os.environ["GEMINI_MODEL"] = MODEL_NAME

    # Save to .env
    from pathlib import Path
    env_path = Path(__file__).parent / ".env"
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"# EchoMap Configuration\nGEMINI_API_KEY={API_KEY}\nGEMINI_MODEL={MODEL_NAME}\n")
    except Exception as e:
        pass

    return {
        "configured": is_api_configured(),
        "model": MODEL_NAME,
        "masked_key": (API_KEY[:6] + "..." + API_KEY[-4:]) if len(API_KEY) > 10 else ("***" if API_KEY else ""),
    }


def verify_gemini_connection(test_key: str, test_model: str) -> Dict[str, Any]:
    """Attempts a lightweight verification call to Gemini to ensure key is valid."""
    try:
        from google import genai
        client = genai.Client(api_key=test_key)
        res = client.models.generate_content(
            model=test_model or MODEL_NAME,
            contents="Respond with only the word OK",
        )
        return {"valid": True, "message": "Successfully connected to Gemini API"}
    except Exception as e:
        return {"valid": False, "message": str(e)}


def clean_json_response(raw_text: str) -> str:
    """Extracts JSON content from potential Markdown backticks or preambles."""
    cleaned = raw_text.strip()
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Try finding first [ and last ]
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1].strip()
    return cleaned


def scan_desk(image: Image.Image, force_mock: bool = False) -> List[Dict[str, Any]]:
    # Ensure image is fully loaded and in RGB mode
    if isinstance(image, Image.Image):
        image.load()
        if image.mode != "RGB":
            image = image.convert("RGB")
    """
    Scans a desk image to identify objects and normalized coordinates.
    Returns a list of dicts with name, x, y, confidence, and region_desc.
    """
    if force_mock or not is_api_configured():
        # Offline or mock demonstration fallback
        results = []
        for item in MOCK_DESK_ITEMS:
            obj = dict(item)
            obj["region_desc"] = region(obj["x"], obj["y"])
            results.append(obj)
        return results

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)

    prompt = """
Examine this desk or workspace image carefully for visible everyday objects (e.g. phone, keys, mug, bottle, notebook, pen, laptop, glasses, headphones, wallet, charger).
Return ONLY a valid JSON array. Each object must contain:
- name: short lowercase common object name (e.g. "phone", "keys", "scissors", "water bottle")
- x: normalized horizontal center coordinate from 0.0 (far left) to 1.0 (far right)
- y: normalized vertical center coordinate from 0.0 (top/back of desk) to 1.0 (bottom/front of desk closest to user)
- confidence: confidence estimate between 0.0 and 1.0
- visible: true if visibly identifiable
Do not invent imaginary objects. If partially occluded, lower the confidence.
Output strictly JSON without explanations or markdown formatting outside the JSON array.
Example format:
[
  {"name": "phone", "x": 0.32, "y": 0.45, "confidence": 0.95, "visible": true},
  {"name": "keys", "x": 0.40, "y": 0.42, "confidence": 0.89, "visible": true}
]
"""

    models_to_try = [MODEL_NAME] + [m for m in FALLBACK_MODELS if m != MODEL_NAME]
    last_err = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[image, prompt],
            )
            raw_text = response.text or ""
            json_str = clean_json_response(raw_text)
            data = json.loads(json_str)

            validated_objects: List[Dict[str, Any]] = []
            for entry in data:
                try:
                    # Clamp coordinates safely into [0.0, 1.0]
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

    raise RuntimeError(f"EchoMap Vision API Error: {str(last_err)}")
