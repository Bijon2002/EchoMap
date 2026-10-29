"""
server.py - EchoMap FastAPI Web Application Server
Serves the modern, accessible single-page interface and REST API endpoints.
Team PythonCharlie | University of Bedfordshire HCI + AI + XR Hackathon
"""

import base64
import io
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw
from pydantic import BaseModel

import commands
import memory
from spatial import compare_scans, region, distance
import vision

# Initialize database
memory.initialise()

# Create FastAPI app
app = FastAPI(
    title="EchoMap API",
    description="Spatial Memory Assistant for Blind & Low-Vision Users",
    version="2.0.0",
)

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "css").mkdir(exist_ok=True)
(STATIC_DIR / "js").mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Pydantic Request Models
class QueryRequest(BaseModel):
    query: str


class Base64ScanRequest(BaseModel):
    image_base64: str
    scene: Optional[str] = "desk"
    summary: Optional[str] = ""


class CorrectionRequest(BaseModel):
    object_name: str
    relation_type: str
    reference_object: str
    note: Optional[str] = ""


class TTSRequest(BaseModel):
    text: str
    tld: Optional[str] = "co.uk"


class SettingsRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = "gemini-3.1-flash-lite"
    test_connection: Optional[bool] = False


# In-memory LRU-bounded cache for fast instantaneous playback
_TTS_CACHE: Dict[str, bytes] = {}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Silence favicon 404 logs with an empty response."""
    return Response(content=b"", media_type="image/x-icon")


# -------------------------------------------------------------
# ROOT & FRONTEND ROUTE
# -------------------------------------------------------------
@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serves the modern single-page HTML frontend."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(str(index_file))


# -------------------------------------------------------------
# SYSTEM & STATUS APIS
# -------------------------------------------------------------
@app.get("/api/status")
async def get_system_status():
    """Returns system diagnostic status and memory counts."""
    api_ready = vision.is_api_configured()
    latest = memory.latest_scan()
    all_scans = memory.get_all_scans()
    corrections = memory.get_corrections()

    scan_meta = latest[0] if latest else None
    objects = latest[1] if latest else []

    return {
        "gemini_api_configured": api_ready,
        "gemini_model": vision.MODEL_NAME if api_ready else "Mock / Offline Demo",
        "has_memory": bool(latest),
        "total_scans": len(all_scans),
        "latest_scan_time": scan_meta["created_at"] if scan_meta else None,
        "latest_object_count": len(objects),
        "total_corrections": len(corrections),
        "app_title": "EchoMap: Your World, Remembered",
        "team": "Team PythonCharlie",
        "event": "University of Bedfordshire HCI + AI + XR Hackathon",
    }


# -------------------------------------------------------------
# SPATIAL MEMORY APIS
# -------------------------------------------------------------
@app.get("/api/scans/latest")
async def get_latest_scan():
    """Retrieves the latest scan and its remembered objects."""
    latest = memory.latest_scan()
    prev = memory.previous_scan()

    if not latest:
        return {
            "has_scan": False,
            "scan": None,
            "objects": [],
            "previous_scan": None,
            "previous_objects": [],
            "sectors": {"top": [], "middle": [], "bottom": []},
        }

    scan_meta, objects = latest
    prev_meta = prev[0] if prev else None
    prev_objects = prev[1] if prev else []

    # Calculate 3 depth tiers for quick tactile / spatial overview
    sectors = {
        "top": [o for o in objects if o["y"] < 1 / 3],
        "middle": [o for o in objects if 1 / 3 <= o["y"] < 2 / 3],
        "bottom": [o for o in objects if o["y"] >= 2 / 3],
    }

    # Calculate proximity pairs for visualization
    proximity_pairs = []
    for i in range(len(objects)):
        for j in range(i + 1, len(objects)):
            dist = distance(objects[i], objects[j])
            if dist < 0.28:
                proximity_pairs.append({
                    "obj1": objects[i]["name"],
                    "obj2": objects[j]["name"],
                    "x1": objects[i]["x"],
                    "y1": objects[i]["y"],
                    "x2": objects[j]["x"],
                    "y2": objects[j]["y"],
                    "distance": round(dist, 3),
                })

    return {
        "has_scan": True,
        "scan": scan_meta,
        "objects": objects,
        "previous_scan": prev_meta,
        "previous_objects": prev_objects,
        "sectors": sectors,
        "proximity_pairs": proximity_pairs,
    }


@app.get("/api/scans")
async def get_all_scans():
    """Returns list of all historical scans."""
    return {"scans": memory.get_all_scans()}


# -------------------------------------------------------------
# NATURAL LANGUAGE QUERY API
# -------------------------------------------------------------
@app.post("/api/query")
async def query_memory(req: QueryRequest):
    """
    Answers questions directly from persistent SQLite memory
    without activating the camera or incurring vision API costs.
    """
    query_text = req.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    latest = memory.latest_scan()
    prev = memory.previous_scan()

    scan_meta = latest[0] if latest else None
    objects = latest[1] if latest else []
    prev_objects = prev[1] if prev else []

    answer = commands.answer_question(
        query_text,
        objects=objects,
        scan_meta=scan_meta,
        previous_objects=prev_objects,
    )

    return {
        "query": query_text,
        "answer": answer,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scan_id": scan_meta["id"] if scan_meta else None,
        "objects_count": len(objects),
    }


# -------------------------------------------------------------
# NEURAL EXPRESSIVE TTS AUDIO API (E.D.I.T.H. PROSODY & PITCH CONTOURS)
# -------------------------------------------------------------
@app.post("/api/tts")
async def generate_speech_audio(req: TTSRequest):
    """
    Generates natural British female E.D.I.T.H. speech audio with prosodic
    ups and downs, human-like cadence, and melodic inflection using gTTS.
    """
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    tld = req.tld or "co.uk"
    cache_key = f"{tld}::{text}"
    if cache_key in _TTS_CACHE:
        return Response(content=_TTS_CACHE[cache_key], media_type="audio/mpeg")

    try:
        from gtts import gTTS
        buf = io.BytesIO()
        # British English female voice contour with natural human intonation
        tts = gTTS(text=text, lang="en", tld=tld, slow=False)
        tts.write_to_fp(buf)
        audio_data = buf.getvalue()

        # Cache bounded to 100 recent utterances for zero-latency replays
        if len(_TTS_CACHE) > 100:
            _TTS_CACHE.pop(next(iter(_TTS_CACHE)))
        _TTS_CACHE[cache_key] = audio_data

        return Response(content=audio_data, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


# -------------------------------------------------------------
# IMAGE DECODER HELPER (PIL + OPENCV FALLBACK + BASE64 DATA-URL)
# -------------------------------------------------------------
def decode_image_bytes(contents: bytes) -> Image.Image:
    """
    Robust multi-layer image decoder handling standard PIL, OpenCV imdecode fallback,
    WebP, JFIF, raw camera buffers, and Base64 data-URL text strings.
    """
    if not contents or len(contents) < 4:
        raise ValueError("Uploaded image file is empty or corrupted.")

    # 1. Handle Base64 data-URL text uploaded as raw bytes
    if contents.startswith(b"data:image/") or b";base64," in contents[:120]:
        try:
            parts = contents.split(b";base64,")
            raw_b64 = parts[1] if len(parts) > 1 else parts[0]
            contents = base64.b64decode(raw_b64)
        except Exception:
            pass

    # 2. Standard PIL decode with stream rewind
    try:
        buf = io.BytesIO(contents)
        buf.seek(0)
        img = Image.open(buf)
        img.load()
        return img.convert("RGB")
    except Exception:
        pass

    # 3. OpenCV imdecode fallback (decodes unusual headers, JFIF, camera raw, webp)
    try:
        import numpy as np
        import cv2
        nparr = np.frombuffer(contents, np.uint8)
        cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if cv_img is not None:
            cv_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            return Image.fromarray(cv_rgb)
    except Exception:
        pass

    raise ValueError("The provided file could not be recognized as an image. Please upload a standard JPG, PNG, or WebP photo.")


# -------------------------------------------------------------
# VISION SCAN APIS (CAMERA & UPLOAD)
# -------------------------------------------------------------
def _process_and_save_scan(image: Image.Image, scene: str = "desk", summary: str = "") -> Dict[str, Any]:
    """Helper to run vision analysis and store results in SQLite."""
    try:
        detected = vision.scan_desk(image)
        if not detected:
            return {
                "success": False,
                "detected_count": 0,
                "objects": [],
                "message": "No clear everyday objects detected in the image.",
            }

        scan_summary = summary or f"Scan with {len(detected)} objects detected"
        scan_id = memory.save_scan(detected, scene=scene, summary=scan_summary)

        return {
            "success": True,
            "scan_id": scan_id,
            "detected_count": len(detected),
            "objects": detected,
            "message": f"Successfully identified and remembered {len(detected)} objects on your desk.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision Scan Error: {str(e)}")


@app.post("/api/scan/upload")
async def scan_file_upload(file: UploadFile = File(...)):
    """Accepts an uploaded image file (webcam snapshot or uploaded photo)."""
    try:
        contents = await file.read()
        image = decode_image_bytes(contents)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image format: {str(e)}")

    return _process_and_save_scan(image, scene="upload", summary=f"Uploaded photo: {file.filename or 'photo.jpg'}")


@app.post("/api/scan/base64")
async def scan_base64_upload(req: Base64ScanRequest):
    """Accepts a base64 encoded data-URL snapshot directly from HTML5 webcam."""
    try:
        raw_b64 = req.image_base64
        if "base64," in raw_b64:
            raw_b64 = raw_b64.split("base64,")[1]
        image_bytes = base64.b64decode(raw_b64)
        image = decode_image_bytes(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode base64 image: {str(e)}")

    return _process_and_save_scan(image, scene=req.scene or "webcam", summary=req.summary or "Webcam snapshot")


# -------------------------------------------------------------
# MOVEMENT & VERIFICATION DIFF API
# -------------------------------------------------------------
@app.get("/api/diff")
async def get_movement_diff():
    """Compares the two most recent scans to identify moved or missing items."""
    latest = memory.latest_scan()
    prev = memory.previous_scan()

    if not latest or not prev:
        return {
            "has_diff": False,
            "message": "Need at least two scans to compute spatial diffs.",
            "diffs": [],
            "prev_scan": prev[0] if prev else None,
            "latest_scan": latest[0] if latest else None,
        }

    diffs = compare_scans(prev[1], latest[1])
    return {
        "has_diff": True,
        "message": f"Compared Scan #{prev[0]['id']} with Scan #{latest[0]['id']}.",
        "prev_scan": prev[0],
        "latest_scan": latest[0],
        "diffs": diffs,
    }


# -------------------------------------------------------------
# USER TACTILE CORRECTIONS APIS
# -------------------------------------------------------------
@app.get("/api/corrections")
async def list_corrections():
    """Retrieves all user-taught tactile facts."""
    return {"corrections": memory.get_corrections()}


@app.post("/api/corrections")
async def create_correction(req: CorrectionRequest):
    """Saves a user-taught spatial fact."""
    if not req.object_name or not req.reference_object:
        raise HTTPException(status_code=400, detail="Object name and Reference object are required.")

    corr_id = memory.save_correction(
        object_name=req.object_name,
        relation_type=req.relation_type,
        reference_object=req.reference_object,
        note=req.note or "",
    )

    return {
        "success": True,
        "id": corr_id,
        "message": f"Saved fact: '{req.object_name}' is {req.relation_type} '{req.reference_object}'.",
    }


@app.delete("/api/corrections/{corr_id}")
async def delete_correction_item(corr_id: int):
    """Deletes a user correction fact by ID."""
    memory.delete_correction(corr_id)
    return {"success": True, "message": f"Correction #{corr_id} removed."}


# -------------------------------------------------------------
# DEMO & EVALUATION SHORTCUTS
# -------------------------------------------------------------
@app.post("/api/demo/sample")
async def load_sample_desk():
    """Loads a realistic 7-item desk setup for quick demonstration and judging."""
    sample_objects = [
        {"name": "phone", "x": 0.28, "y": 0.52, "confidence": 0.96, "region_desc": "left side of the desk"},
        {"name": "keys", "x": 0.35, "y": 0.48, "confidence": 0.91, "region_desc": "centre of the desk"},
        {"name": "coffee mug", "x": 0.82, "y": 0.25, "confidence": 0.94, "region_desc": "top-right area of the desk"},
        {"name": "notebook", "x": 0.55, "y": 0.70, "confidence": 0.89, "region_desc": "bottom centre of the desk"},
        {"name": "pen", "x": 0.45, "y": 0.68, "confidence": 0.87, "region_desc": "bottom centre of the desk"},
        {"name": "laptop", "x": 0.50, "y": 0.28, "confidence": 0.98, "region_desc": "top centre of the desk"},
        {"name": "water bottle", "x": 0.86, "y": 0.55, "confidence": 0.92, "region_desc": "right side of the desk"},
    ]
    scan_id = memory.save_scan(
        sample_objects,
        scene="hackathon_sample_desk",
        summary="Sample desk layout with 7 everyday objects",
    )
    return {
        "success": True,
        "scan_id": scan_id,
        "object_count": len(sample_objects),
        "message": "Realistic sample desk layout loaded into memory.",
    }


@app.post("/api/demo/simulate-diff")
async def simulate_movement():
    """Adds a second scan with moved keys and missing coffee mug to demo diffing."""
    simulated_new = [
        {"name": "phone", "x": 0.28, "y": 0.52, "confidence": 0.96, "region_desc": "left side of the desk"},
        {"name": "keys", "x": 0.78, "y": 0.75, "confidence": 0.90, "region_desc": "bottom-right area of the desk"},  # Moved!
        {"name": "notebook", "x": 0.55, "y": 0.70, "confidence": 0.89, "region_desc": "bottom centre of the desk"},
        {"name": "pen", "x": 0.45, "y": 0.68, "confidence": 0.87, "region_desc": "bottom centre of the desk"},
        {"name": "laptop", "x": 0.50, "y": 0.28, "confidence": 0.98, "region_desc": "top centre of the desk"},
        {"name": "glasses", "x": 0.15, "y": 0.20, "confidence": 0.88, "region_desc": "top-left area of the desk"},  # New!
        # Coffee mug missing!
    ]
    scan_id = memory.save_scan(
        simulated_new,
        scene="simulated_scan_movement",
        summary="Simulated scan with moved keys, missing mug, and new glasses",
    )
    return {
        "success": True,
        "scan_id": scan_id,
        "message": "Simulated second scan created (Keys moved, mug missing, glasses added).",
    }


@app.post("/api/demo/clear")
async def reset_memory():
    """Clears all scans, objects, and corrections."""
    memory.clear_memory()
    return {"success": True, "message": "All spatial memory and corrections have been wiped."}


# -------------------------------------------------------------
# SETTINGS & CONFIGURATION APIS
# -------------------------------------------------------------
@app.get("/api/settings")
async def get_settings():
    """Returns current Nexus AI API configuration (masked for security)."""
    key = vision.API_KEY
    masked = (key[:6] + "..." + key[-4:]) if len(key) > 10 else ("configured" if key else "not configured")
    return {
        "configured": vision.is_api_configured(),
        "model": vision.MODEL_NAME,
        "masked_key": masked,
        "provider": "Nexus AI",
        "base_url": vision.NEXUS_BASE_URL,
        "models_available": [
            "gemini-3.1-flash-lite",
            "gemini-3.1-flash-image",
            "claude-haiku-4-5",
            "gemini-2.5-flash",
            "gpt-4o",
        ],
    }


@app.post("/api/settings")
async def save_settings(req: SettingsRequest):
    """Updates and saves the Nexus AI API key and model selection."""
    new_key = (req.api_key or "").strip()
    new_model = (req.model or "gemini-3.1-flash-lite").strip()

    if req.test_connection and new_key:
        verification = vision.verify_nexus_connection(new_key, new_model)
        if not verification["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Nexus AI verification failed: {verification['message']}"
            )

    updated = vision.update_api_config(new_key, new_model)
    return {
        "success": True,
        "message": f"Nexus AI configured. Model: {updated['model']}.",
        **updated,
    }


# Entry point for production hosting and local development
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("server:app", host=host, port=port, reload=False)


