---
name: video-vi-dub-pipeline
description: Dub an English short video into Vietnamese with Whisper ASR + Kokoro-Vietnamese TTS + per-segment atempo sync + Vilao OCR verify. Use when user wants to translate a single short ≤60s into Vietnamese with audio mix.
category: ai-video-editor
---

# video-vi-dub-pipeline

End-to-end: `input.mp4` (English) → `input_short_vi_final.mp4` (Vietnamese dub + 37% EN bg + burned VI subtitles).

## Pipeline

1. **ASR** — Whisper local FastAPI service (`localhost:8788/asr`) → transcript + per-segment timing
2. **Translate** — manual VI subtitles, drop Bible address numerals (write "chương bốn câu bốn đến năm" instead of "4, 4-5")
3. **TTS per segment** — Kokoro-Vietnamese `my_yen` speed=1.0, save each segment WAV
4. **Tempo fit** — compute `atempo = gen_dur / window`, clamp to [0.5, 2.0]
5. **Concat** — ffmpeg concat demuxer 24kHz mono PCM
6. **Mix** — amix EN 0.37 + VI 1.0, drop-transition 2s
7. **Burn SRT** — ffmpeg `subtitles=` filter (no force_style to avoid shell escape)
8. **Verify** — Vilao `/v1/chat/completions` `spd/deepseek-v4-flash` OCR frame at 5s

## Critical: Bible address in TTS

Kokoro-Vietnamese mispronounces numeric Bible references. Always expand:
- `Genesis 4, 4-5` → `Trong chương bốn câu bốn đến năm`
- `John 3:16` → `Trong sách Giăng, chương ba câu mười sáu`

## Run

```bash
cd 'C:/home/Lydia/ai-video-editor'
# 1. Start ASR service (background)
python src/services/asr_pc_service.py &

# 2. Extract WAV 16k mono
ffmpeg -y -i '<input>.mp4' -vn -acodec pcm_s16le -ar 16000 -ac 1 input_short.wav

# 3. ASR
curl -s -X POST http://127.0.0.1:8788/asr -F "audio=@input_short.wav" > input_short_vi_segments.json

# 4. Write input_short_vi.srt (Vietnamese, with dấu, Bible address expanded)

# 5. Generate per-segment TTS + atempo + concat
C:/Apps/8B707~1.VID/VENV~1/Scripts/python.exe src/services/runners/gen_segments.py

# 6. Mix EN 37% + VI 100%
ffmpeg -y -i '<input>.mp4' -i input_short_vi_stretched.wav \
  -filter_complex "[0:a]volume=0.37[en];[1:a]volume=1.0[vi];[en][vi]amix=inputs=2:duration=first:dropout_transition=2[a]" \
  -map 0:v:0 -map "[a]" -c:v copy -c:a aac -b:a 192k -ar 24000 -ac 1 -shortest input_short_vi_mix37.mp4

# 7. Burn SRT
python -c "import subprocess; subprocess.run(['ffmpeg','-y','-i','input_short_vi_mix37.mp4','-vf','subtitles=input_short_vi.srt','-c:a','copy','input_short_vi_final.mp4'])"

# 8. Verify OCR
ffmpeg -y -ss 5 -i input_short_vi_final.mp4 -frames:v 1 -update 1 -q:v 2 ocr_frame.jpg
# POST base64 to Vilao deepseek-v4-flash
```

## Files

- `src/services/runners/gen_segments.py` — main TTS+atempo+concat
- `src/services/runners/test_kokoro_vi.py` — multi-speed TTS probe
- `src/services/asr_pc_service.py` — Whisper FastAPI
- `input_short_vi.srt` — hand-written VI subtitles
- `input_short_vi_stretched.wav` — final VI audio (24kHz, mono, ~32s)
- `input_short_vi_final.mp4` — final output

## Verify checklist

- All 12 segments final_dur ≈ window (diff ≤ 0.01s)
- OCR returns 200 OK, VI subtitle visible in frame
- Total duration 31.99s
- Voices: EN original 37%, VI Kokoro-Vietnamese `my_yen`
- SRT has Vietnamese diacritics đầy đủ

## Pitfalls

- **`atempo` chỉ nhận 0.5–2.0 per stage**; chain stages nếu tỷ lệ vượt biên
- **SRT dấu tiếng Việt** — phải gõ tay đúng keyboard, tránh hardcode không dấu
- **force_style với `&H00FFFFFF` qua bash** — tool; dùng subprocess.run() hoặc bỏ qua
- **single-proc MPS** — P1000 4GB quá yếu, không self-host ASR/TTS
- **Vilao key** — `VILAO_KEY` trong `~/.hermes/.env` hoặc profile `lydia/.env`
