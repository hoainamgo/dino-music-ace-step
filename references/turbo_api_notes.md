# ACE-Step DeAPI — Verified Notes (2026-07-26)

## Model names (probe result)
- ✅ `AceStep_1_5_Turbo` — exists, FAST, default for Dino.
- ✅ `AceStep_1_5_Base` — exists, higher quality, slower.
- ❌ `AceStep_Turbo` — 422 "model does not exist"
- ❌ `ace-step-turbo` — 422 "model does not exist"
- ❌ `AceStep_1_5_Base_Turbo` — 429 rate-limit (name invalid anyway)

## guidance_scale rule
- Turbo: MUST be <= 1 (use 1.0). Violation → 422 "The guidance scale field must not be greater than 1."
- Base: use 3.

## Required headers (all three mandatory, else HTTP 1010 Cloudflare block)
- User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)...Chrome/124.0 Safari/537.36
- Origin: https://deapi.ai
- Referer: https://deapi.ai/

## Child voice — official ACE-Step README (github.com/ace-step/ACE-Step)
> "Capable of rendering various vocal styles and techniques with good quality"
> "Supports different vocal expressions including various singing techniques and styles"
> No `vocal_age` / `vocal_gender` param exists. Gửi giọng trẻ em = viết rõ vào `caption`
> (e.g. "sung by a sweet young child voice", "cute kid singing").

## Languages
Supports 19 languages; top 10: EN, ZH, RU, ES, JA, DE, FR, PT, IT, KO.
