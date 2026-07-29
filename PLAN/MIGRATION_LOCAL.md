# Plan: switch ai-music, ASR, TTS and OCR off browser ONNX onto local/PC services

## Goals
- Keep the editor UI and timeline unchanged.
- Add a backend selector: `browser` (default current) vs `local`.
- Replace/override:
  - music: Stable Audio 3 ONNX → ACE Step 1.5 via DEAPI/HTTP
  - ASR: Whisper small q8 ONNX → Whisper on PC HTTP
  - TTS: Kokoro 82M browser → Kokoro on PC HTTP (EN + VN)
  - OCR/verify: YOLOS/MODNet optional → Vilao deepseek Vision for caption verification

## Files to change
- `src/config/modelBackend.js` NEW
- `src/hooks/useAiMusicGeneration.js` PATCH
- `src/workers/ai-music.worker.js` PATCH
- `src/hooks/useAutoCaptions.js` PATCH
- `src/hooks/useVoiceGeneration.js` PATCH
- `src/lib/vision.js` PATCH
- `src/workers/vision.worker.js` PATCH
- `.env.example` NEW
