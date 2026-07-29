"""
PC-side Kokoro TTS service.
Env:
  TTS_PORT=8789
  KOKORO_MODEL_DIR=C:\Apps\Model_TTS\
Run:
  python tts_pc_service.py
"""
import os
import io
import json
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler

from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel

app = FastAPI()

class TTSRequest(BaseModel):
    text: str
    voice: str = "en_US/female"
    lang: str = "en"
    speed: float = 1.0

@app.post("/tts")
def tts(req: TTSRequest):
    model_dir = Path(os.environ.get("KOKORO_MODEL_DIR", r"C:\Apps\Model_TTS"))
    try:
        # Lazy import so service can start even if kokoro is missing
        import importlib.util
        spec = importlib.util.spec_from_file_location("kokoro_pipeline", str(model_dir / "kokoro_pipeline.py"))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            pipeline = mod.KPipeline(lang_code=req.lang)
            chunks = list(pipeline(req.text, voice=req.voice, speed=req.speed))
            wav = chunks[0].audio if len(chunks) > 0 else b''
        else:
            raise ImportError("kokoro_pipeline.py not found")
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    b64 = base64.b64encode(wav).decode("utf-8")
    return {"ok": True, "audio_b64": b64, "format": "wav", "provider": "kokoro-pc", "voice": req.voice, "lang": req.lang}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("TTS_PORT", "8789")))
