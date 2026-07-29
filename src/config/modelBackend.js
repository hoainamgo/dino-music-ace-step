export const MODEL_BACKEND = (import.meta?.env?.VITE_MODEL_BACKEND || "browser").toString().toLowerCase();

export const BACKENDS = {
  browser: { music: "browser", asr: "browser", tts: "browser", ocr: "browser" },
  local: {
    music: "local",
    asr: "local",
    tts: "local",
    ocr: "local",
    musicUrl: import.meta?.env?.VITE_LOCAL_MUSIC_URL || "http://localhost:8787/music",
    asrUrl: import.meta?.env?.VITE_LOCAL_ASR_URL || "http://localhost:8788/asr",
    ttsUrl: import.meta?.env?.VITE_LOCAL_TTS_URL || "http://localhost:8789/tts",
    ocrUrl: import.meta?.env?.VITE_LOCAL_OCR_URL || "http://localhost:8790/ocr",
  },
  deapi: {
    music: "deapi",
    asr: "browser",
    tts: "browser",
    ocr: "browser",
    baseUrl: import.meta?.env?.VITE_DEAPI_BASE_URL || "https://api.deapi.ai/api/v1",
    musicModel: import.meta?.env?.VITE_DEAPI_MUSIC_MODEL || "ace-step-1.5",
    apiKey: import.meta?.env?.VITE_DEAPI_KEY || "",
  },
};

export function resolveBackend(domain) {
  const mode = MODEL_BACKEND;
  return BACKENDS[mode]?.[domain] ?? BACKENDS.browser[domain];
}
