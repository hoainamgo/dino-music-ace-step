"""
Music backend adapters for ai-video-editor.

Providers:
- deapi       -> ai.deapi.ai (ACE Step 1.5 / txt2audio)
- suno-302    -> 302.ai Suno chirp-crow
- kokoro-pc   -> local Kokoro TTS audio (fallback music-like bed)
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel
import os, requests, json, httpx

app = FastAPI()

class MusicReq(BaseModel):
    prompt: str
    seconds: int = 60
    bpm: int | None = None
    key: str | None = None
    instrumental: bool = True

DEAPI_KEY = os.environ.get("DEAPI_KEY", "")
DEAPI_BASE = os.environ.get("DEAPI_BASE_URL", "https://api.deapi.ai/api/v1").rstrip("/")
DEAPI_MODEL = os.environ.get("DEAPI_MUSIC_MODEL", "ace-step-1.5")

SUNO_KEY = os.environ.get("SUNO_API_KEY", "")
SUNO_BASE = os.environ.get("SUNO_BASE_URL", "https://api.302.ai").rstrip("/")

PROVIDER = os.environ.get("AI_MUSIC_PROVIDER", "deapi").lower()


@app.post("/music")
async def generate_music(req: MusicReq):
    provider = PROVIDER
    if provider == "deapi":
        return await _deapi(req)
    if provider in ("suno-302", "suno", "302"):
        return await _suno_302(req)
    if provider in ("kokoro-pc", "kokoro"):
        return await _kokoro_pc_fallback(req)
    return JSONResponse({"ok": False, "error": f"Unknown provider: {provider}"}, status_code=400)


async def _deapi(req: MusicReq):
    # Try txt2audio style first; if unavailable, attempt /client/txt2audio style endpoints
    candidates = [
        (f"{DEAPI_BASE}/client/txt2audio", {"model": DEAPI_MODEL, "prompt": req.prompt, "seconds": req.seconds, "bpm": req.bpm, "key": req.key, "instrumental": req.instrumental}),
        (f"{DEAPI_BASE}/txt2audio", {"model": DEAPI_MODEL, "prompt": req.prompt, "seconds": req.seconds, "bpm": req.bpm, "key": req.key, "instrumental": req.instrumental}),
        (f"{DEAPI_BASE}/music/generate", {"model": DEAPI_MODEL, "prompt": req.prompt, "seconds": req.seconds, "bpm": req.bpm, "key": req.key, "instrumental": req.instrumental}),
    ]
    last_status = 404
    for url, body in candidates:
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {DEAPI_KEY}", "Content-Type": "application/json"}, json=body, timeout=120)
            ctype = r.headers.get("Content-Type", "")
            if r.status_code == 200 and ctype.startswith("audio/"):
                return Response(content=r.content, media_type=ctype)
            if r.status_code == 200:
                data = r.json()
                audio_url = (((data.get("data") or [{}])[0]).get("url") or (((data.get("choices") or [{}])[0]).get("audio_url")))
                if audio_url:
                    ra = requests.get(audio_url, timeout=120)
                    if ra.status_code == 200:
                        return Response(content=ra.content, media_type=ra.headers.get("Content-Type", "audio/mpeg"))
            last_status = r.status_code
        except requests.RequestException:
            pass
    return JSONResponse({"ok": False, "error": f"DEAPI music failed, last status={last_status}"}, status_code=502)


async def _suno_302(req: MusicReq):
    url = f"{SUNO_BASE}/suno/submit/music"
    body = {"model": "chirp-crow", "prompt": req.prompt, "lyric": "", "seconds": req.seconds, "title": "Editor Instrumental", "custom": False}
    if SUNO_KEY:
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {SUNO_KEY}", "Content-Type": "application/json"}, json=body, timeout=30)
            if r.status_code == 200:
                return JSONResponse({"ok": True, "provider": "suno-302", "data": r.json()})
        except requests.RequestException:
            pass
    return JSONResponse({"ok": False, "error": "Suno 302 unavailable"}, status_code=502)


async def _kokoro_pc_fallback(req: MusicReq):
    return JSONResponse({"ok": False, "error": "Kokoro PC TTS cannot generate music. Use ACE Step 1.5 local or Suno/KIE cloud."}, status_code=501)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("MUSIC_PORT", "8787")))
