"""
PC-side Whisper ASR service for ai-video-editor.
Run on Windows host: expose POST /asr -> JSON {text, segments[]}
"""
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn, os, json, subprocess, tempfile
from pathlib import Path

app = FastAPI()
WHISPER_VENV = Path(r"C:\Apps\8. Video lingo\.venv\Scripts\python.exe")
WAV_PATH = Path(tempfile.gettempdir()) / "ai_editor_asr.wav"

@app.post("/asr")
async def transcribe(audio: UploadFile = File(...)):
    data = await audio.read()
    WAV_PATH.write_bytes(data)
    env = os.environ.copy()
    cmd = [str(WHISPER_VENV), "-c",
        "import json,sys; sys.stdout.reconfigure(encoding='utf-8'); "
        "f=r'{}'; import whisper; m=whisper.load_model('small'); "
        "r=m.transcribe(str(f),language='en'); print(json.dumps(r, ensure_ascii=False))".format(str(WAV_PATH).replace("\\","/"))]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if p.returncode != 0:
        return JSONResponse({"ok": False, "text": "", "segments": [], "stderr": p.stderr[-300:]}, status_code=500)
    try:
        r = json.loads(p.stdout)
        segments = [{"text": s.get("text",""), "start": s.get("start",0), "end": s.get("end",0)} for s in r.get("segments",[])]
        return {"ok": True, "text": r.get("text",""), "segments": segments}
    except Exception as e:
        return JSONResponse({"ok": False, "text": "", "segments": [], "parse_error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("ASR_PORT", "8788")))
