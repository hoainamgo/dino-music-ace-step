---
name: ace-step-1.5
description: Local ACE Step 1.5 music generation, requires RTX 3090+ GPU.
---

# ACE Step 1.5 — Local Music Generation

Apache-2.0, 3.5B. RTF 15–34x on A100. Needs RTX 3090/4090/A100 GPU. Not for Quadro P1000 4GB.

## Service contract
- Endpoint: `POST http://<host>:8787/music`
- Body: `{ prompt: string, seconds: number, bpm?: number, key?: string, instrumental?: boolean }`
- Returns: `audio/*` blob (MP3/WAV)

## Frontend routing
- `src/hooks/useAiMusicGeneration.js` already routes `backend === "local"` → `BACKENDS.local.musicUrl`
- Env: `.env.local` → `MODEL_BACKEND=local`, `LOCAL_MUSIC_URL=http://<host>:8787/music`

## Workflow
1. Build prompt: `buildEnglishMusicPrompt(selection)`
2. POST to local ACE Step 1.5 HTTP service
3. Receive audio blob → push into timeline as `audio/music` asset

## Fallback
If local service unreachable: fall back to browser Stable Audio 3 ONNX.

## Commercial
Apache-2.0 → DistroKid-safe for instrumental/backing tracks. Sung vocals still go through Suno/KIE.
