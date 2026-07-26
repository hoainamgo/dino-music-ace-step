---
name: dino-music-ace-step
description: Tạo nhạc AI cho Dino Universe (hướng thiếu nhi 2-8 tuổi) qua DeAPI endpoint txt2music. MẶC ĐỊNH model AceStep_1_5_Turbo (nhanh, nhẹ). Sinh giọng trẻ em ấm áp bằng caption + lyrics từ audio/musics.json. Dùng khi cần bài hát Dino (anthem, kids songs, nhạc nền). Thay thế Suno/Mureka cho Dino.
version: 1.0.0
github: https://github.com/hoainamgo/dino-music-ace-step
default_model: AceStep_1_5_Turbo
---

# Dino Music — ACE-Step via DeAPI

Tạo nhạc thiếu nhi cho Dino Universe bằng DeAPI `txt2music`.
**MẶC ĐỊNH dùng `AceStep_1_5_Turbo`** (nhanh, nhẹ). Base = `AceStep_1_5_Base` (chất hơn, chậm hơn).
Giọng hát trẻ em (child voice) gợi qua **caption**, không có param age chính thức.

## 1. AUTH
Token: `ID|SECRET` → `Authorization: Bearer <ID|SECRET>`.
Dùng env `DEAPI_TOKEN`. KHÔNG hardcode.
Token hiện dùng (2026-07-26, do anh Hoài cấp, ROTATE thường): `14312|H3pl18tKf0D2KkSuOcd1wfMeua8KSXW4EA7gWsBm9f839ddc`
→ Đừng in ra chat.

## 2. ENDPOINT (đã verify 2026-07-26)
`POST https://api.deapi.ai/api/v1/client/txt2music`
Headers (bắt buộc CÙNG LÚC, thiếu 1 → 1010 Cloudflare):
- `Authorization: Bearer $DEAPI_TOKEN`
- `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)...Chrome/124.0 Safari/537.36`
- `Origin: https://deapi.ai`
- `Referer: https://deapi.ai/`
- `accept: application/json`
- `Content-Type: application/json`

Payload (JSON):
```json
{
  "caption": "gentle children's song, sung by a sweet young child voice, soft ukulele, warm and soothing, bedtime lullaby for kids age 2-8",
  "lyrics": "Little Rex is sleeping now\nDreams of stars and moonlit skies",
  "model": "AceStep_1_5_Turbo",
  "duration": 30,
  "inference_steps": 8,
  "guidance_scale": 1,
  "seed": -1,
  "format": "flac",
  "vocal_language": "en"
}
```
Response: `{"data":{"request_id":"<uuid>"}}`

Poll: `GET https://api.deapi.ai/api/v1/client/request-status/{rid}`
Khi `data.status ∈ done|completed|success` →
lấy URL theo thứ tự: `data.result_url` → `output` → `data.output` → `data.result`
(URL là S3/pre-signed, hết hạn ~5h → tải ngay).

## 3. MODEL: Turbo vs Base (QUAN TRỌNG)
- `AceStep_1_5_Turbo` ✅ tồn tại, NHANH → **MẶC ĐỊNH**.
  - Bắt buộc `guidance_scale <= 1` (đặt 1.0). Nếu >1 → 422 "guidance scale field must not be greater than 1."
- `AceStep_1_5_Base` ✅ tồn tại, chất lượng cao hơn, dùng `guidance_scale: 3`.
- Tên SAI (422 "model does not exist"): `AceStep_Turbo`, `ace-step-turbo`, `AceStep_1_5_Base_Turbo`.
- File output tự gắn hậu tố: `*_turbo.flac` / `*_base.flac` (script xử lý).

## 4. CHILD VOICE (quan trọng)
ACE-Step KHÔNG có param `vocal_age`/`vocal_gender` chính thức (xác nhận từ README GitHub ace-step).
Cách gợi giọng trẻ em = viết rõ vào **caption**:
- "sung by a sweet young child voice"
- "cute kid singing"
- "little children's choir"
- kết hợp style nhạc thiếu nhi (ukulele, soft, playful)
Docs ghi: *"Supports different vocal expressions including various singing techniques and styles"* → caption là đúng cách.

## 5. NGÔN NGỮ
Dino hướng US/Quốc tế → `vocal_language: "en"`.
ACE-Step hỗ trợ 19 ngôn ngữ (top: EN, ZH, RU, ES, JA, DE, FR, PT, IT, KO).

## 6. LẤY LỜI TỪ LIST NHẠC DINO
File: `audio/musics.json` (trong Dino Universe root).
Cấu trúc: `DinoUniverseMusics.Anthem` + `DinoUniverseMusics.KidsSongsForSuno[]`.
Mỗi bài có `StructuredLyrics` (Intro/Verse1/Chorus/Verse2/Bridge/Outro) + `SunoPrompt`.
Cách build `lyrics` gửi API: nối các phần (bỏ tag `[...]` trong ngoặc vuông):
```
Verse1 lines
Chorus lines
Verse2 lines
Chorus2 lines
```
`caption` = lấy từ `SunoPrompt` + thêm "sung by a sweet young child voice".

## 7. RATE-LIMIT
- Serialize 1 bài/call. Đợi ~30-60s giữa các bài.
- Nếu 429 → backoff 10→20→40→80s, retry ≤6.
- Quota ~600 req/account. Triage qua header `x-ratelimit-*`.

## 8. WRAPPER SCRIPT
`scripts/gen_dino_music.py`:
- load musics.json → chọn bài `--id N` / `--title NAME` / `--all`
- `--model AceStep_1_5_Turbo` (mặc định) hoặc `--model AceStep_1_5_Base`
- build caption+lyrics → submit → poll → download về `audio/generated/<id>_<slug>_<modeltag>.flac`
- Resume-safe (skip nếu file tồn tại >10KB)
- Ví dụ: `DEAPI_TOKEN=... python3 gen_dino_music.py --id 1` (tạo Rex's Morning Song Turbo)

## 9. PITFALLS
- Thiếu 1 trong 3 header (UA/Origin/Referer) → HTTP 1010 block.
- **Turbo bắt `guidance_scale <= 1`** (Base dùng 3). Sai → 422.
- `format: flac` → file .flac; đổi `mp3` nếu cần.
- URL kết quả hết hạn ~5h → tải ngay, đừng để qua đêm.
- Caption TIẾNG ANH bắt buộc (API reject non-ASCII).
- Giọng trẻ em chỉ gợi bằng caption, không có param riêng → viết càng cụ thể càng tốt.
- Không hardcode token vào script; luôn qua `DEAPI_TOKEN`.
- Tên model sai → 422 "model does not exist". Chỉ `AceStep_1_5_Turbo` và `AceStep_1_5_Base` hợp lệ.

## 10. VERIFIED RUN (2026-07-26)
- Token `14312|...` sống, balance OK.
- Test submit `txt2music` → 200 + request_id (cả Turbo & Base).
- Poll + download thành công.
- Bài demo: "Rex's Morning Song" (ID 1) → Turbo → `1_rex_s_morning_song_turbo.flac` (16.7MB, valid FLAC), giọng child voice ukulele.
- Chưa push GitHub (cần GitHub PAT; repo dự kiến `dino-music-ace-step`).

Xem `references/turbo_api_notes.md` để biết danh sách model đã verify + trích dẫn docs ACE-Step về giọng hát.
