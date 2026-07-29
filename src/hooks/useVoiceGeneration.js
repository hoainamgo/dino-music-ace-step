import { useCallback } from "react";
import { MODEL_ID } from "../config/editor.js";
import { isBuiltInPinyinVoice, predictPiperVoice } from "../lib/piperVoiceRuntime.js";
import { predictMmsVoice } from "../lib/mmsVoiceRuntime.js";
import { isModelDownloadError, loadFromModelHubs } from "../lib/modelSources.js";
import { clearPiperCacheIfStorageTight, isPiperSymbolError, isStorageQuotaError, prepareTextForVoice, TtsInputError } from "../lib/ttsText.js";
import { resolveBackend } from "../config/modelBackend.js";

export function useVoiceGeneration(d) {
  return useCallback(async (captionSegment = null) => {
    const rawText = (captionSegment?.text ?? d.script).trim();
    if (!rawText || d.status === "generating" || d.status === "captioning") return;
    let prepared;
    try { prepared = prepareTextForVoice(rawText, d.selectedVoice); }
    catch (error) {
      const message = error instanceof TtsInputError ? d.t(error.code) : error instanceof Error ? error.message : d.t("ttsErrorVoiceMismatch");
      d.setStatus("error"); d.setStatusText(message); d.setProgress(0); d.notify(message); return;
    }

    const backend = resolveBackend("tts");
    if (backend === "local") {
      d.setVoiceTab("synthesis"); d.setStatus("generating"); d.setStatusText("TTS via local backend"); d.setProgress(10);
      try {
        const url = BACKENDS.local.ttsUrl;
        const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: prepared.text, voiceId: d.selectedVoice.id, speed: d.speed }) });
        if (!res.ok) { const t = await res.text(); throw new Error(`Local TTS failed: ${res.status} ${t}`); }
        const blob = await res.blob();
        await d.commitAudio(blob, `${d.selectedVoice.name} · ${d.t("ttsGenerated")}`, { captionSegment, script: rawText });
        d.notify(d.t("ttsNoticeGenerated")); return;
      } catch (error) {
        d.setStatus("error"); d.setStatusText(error instanceof Error ? error.message : d.t("ttsErrorGenerationFailed")); d.setProgress(0); d.notify(d.t("ttsErrorGenerationFailed")); return;
      }
    }

    if (backend === "deapi") {
      d.setVoiceTab("synthesis"); d.setStatus("generating"); d.setStatusText("TTS via DeAPI"); d.setProgress(10);
      try {
        const baseUrl = import.meta?.env?.VITE_DEAPI_BASE_URL || "https://api.deapi.ai/api/v1";
        const apiKey = import.meta?.env?.VITE_DEAPI_KEY || "";
        const res = await fetch(`${baseUrl}/client/txt2audio`, { method: "POST", headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" }, body: JSON.stringify({ text: prepared.text, voice: d.selectedVoice.id === "mai_linh" ? "Mai" : d.selectedVoice.id === "my_yen" ? "MyYen" : "Serena", model: "Qwen3_TTS_12Hz_1_7B_CustomVoice", lang: "English", format: "mp3", sample_rate: 24000, speed: d.speed }) });
        if (!res.ok) { const t = await res.text(); throw new Error(`DeAPI TTS failed: ${res.status} ${t}`); }
        const blob = await res.blob();
        await d.commitAudio(blob, `${d.selectedVoice.name} · ${d.t("ttsGenerated")}`, { captionSegment, script: rawText });
        d.notify(d.t("ttsNoticeGenerated")); return;
      } catch (error) {
        d.setStatus("error"); d.setStatusText(error instanceof Error ? error.message : d.t("ttsErrorGenerationFailed")); d.setProgress(0); d.notify(d.t("ttsErrorGenerationFailed")); return;
      }
    }

    d.setVoiceTab("synthesis"); d.setStatus("generating"); d.setStatusText("ttsStatusPreparingModel"); d.setProgress(6);
    if (prepared.warningKey) d.notify(d.t(prepared.warningKey));
    try {
      let blob;
      if (d.selectedVoice.engine === "piper") {
        // Xiao Ya and Chaowen use our dedicated ONNX runtime. Avoid loading the
        // separate vits-web bundle on their first run; it is only needed by the
        // remaining Piper catalog voices.
        const builtInPinyinVoice = isBuiltInPinyinVoice(d.selectedVoice.id);
        const tts = builtInPinyinVoice ? null : await import("@diffusionstudio/vits-web");
        if (tts && await clearPiperCacheIfStorageTight(tts)) d.notify(d.t("ttsNoticePiperCacheCleared"));
        d.setStatusText(d.selectedVoice.language === "中文"
          ? "ttsStatusLoadingChineseModel"
          : "ttsStatusPreparingModel");
        const progress = (event) => {
          if (event?.phase === "initializing") d.setStatusText("ttsStatusInitializingModel");
          if (event?.phase === "generating" || event?.backend) d.setStatusText(event.backend === "webgpu" ? "ttsStatusGeneratingWebGpu" : "ttsStatusGeneratingWasm");
          if (event?.total) {
            d.setProgress((current) => Math.max(
              current,
              Math.min(88, Math.max(12, Math.round((event.loaded / event.total) * 76))),
            ));
          }
        };
        const input = { text: prepared.text, voiceId: d.selectedVoice.id };
        try { blob = await predictPiperVoice(tts, input, progress); }
        catch (error) {
          if (!isStorageQuotaError(error)) throw error;
          d.setStatusText("ttsStatusClearingCache"); await tts?.flush?.(); blob = await predictPiperVoice(tts, input, progress);
        }
      } else if (d.selectedVoice.engine === "mms") {
        d.setStatusText("ttsStatusPreparingModel");
        blob = await predictMmsVoice({ text: prepared.text, voiceId: d.selectedVoice.id }, (event) => {
          if (event?.backend) d.setStatusText("ttsStatusGeneratingWasm");
          if (Number.isFinite(event?.progress)) d.setProgress((current) => Math.max(current, Math.min(86, Math.round(event.progress))));
        });
      } else if (d.selectedVoice.engine === "supertonic") {
        d.setStatusText("ttsStatusPreparingModel");
        const { predictSupertonicVoice } = await import("../lib/supertonicVoiceRuntime.js");
        blob = await predictSupertonicVoice({ text: prepared.text, speed: d.speed }, (event) => {
          if (event?.backend) d.setStatusText("ttsStatusGeneratingWasm");
          if (Number.isFinite(event?.progress)) d.setProgress((current) => Math.max(current, Math.min(86, Math.round(event.progress))));
        });
      } else {
        // Kokoro and the editor share the same Transformers runtime. Disable
        // its second Cache Storage layer before Kokoro starts loading; the
        // project service worker already owns persistent model caching.
        const [{ env: transformersEnv }, { KokoroTTS }] = await Promise.all([
          import("@huggingface/transformers"),
          import("kokoro-js"),
        ]);
        transformersEnv.useBrowserCache = false;
        d.setStatusText("ttsStatusLoadingKokoro");
        const progressCallback = (event) => { if (event?.progress) d.setProgress((current) => Math.max(current, Math.min(86, Math.max(10, Math.round(event.progress))))); };
        let tts;
        const webGpuAdapter = globalThis.navigator?.gpu
          ? await globalThis.navigator.gpu.requestAdapter().catch(() => null)
          : null;
        if (webGpuAdapter) {
          try {
            d.setStatusText("ttsStatusLoadingWebGpu");
            tts = await loadFromModelHubs(transformersEnv, () => KokoroTTS.from_pretrained(MODEL_ID, {
              dtype: "fp32",
              device: "webgpu",
              progress_callback: progressCallback,
            }));
            d.setStatusText("ttsStatusGeneratingWebGpu");
            blob = (await tts.generate(prepared.text, { voice: d.selectedVoice.id, speed: d.speed })).toBlob();
          } catch (error) {
            console.warn("Kokoro WebGPU failed; retrying with WASM.", error);
            d.setStatusText("ttsStatusFallingBackWasm");
          }
        }
        if (!blob) {
          tts = await loadFromModelHubs(transformersEnv, () => KokoroTTS.from_pretrained(MODEL_ID, {
            dtype: "q8",
            device: "wasm",
            progress_callback: progressCallback,
          }));
          d.setStatusText("ttsStatusGeneratingWasm");
          blob = (await tts.generate(prepared.text, { voice: d.selectedVoice.id, speed: d.speed })).toBlob();
        }
      }
      d.setStatusText("ttsStatusDecodingWaveform");
      await d.commitAudio(blob, `${d.selectedVoice.name} · ${d.t("ttsGenerated")}`, {
        captionSegment,
        script: rawText,
      });
      d.notify(d.t("ttsNoticeGenerated"));
    } catch (error) {
      console.error(error);
      const message = error instanceof TtsInputError ? d.t(error.code)
        : d.selectedVoice.engine === "piper" && isPiperSymbolError(error) ? d.t("ttsErrorUnsupportedPiperSymbols")
          : isStorageQuotaError(error) ? d.t("ttsErrorStorageQuota")
            : isModelDownloadError(error) ? d.t("ttsErrorModelDownload")
              : error instanceof Error ? error.message : d.t("ttsErrorGenerationFailed");
      d.setStatus("error"); d.setStatusText(message); d.setProgress(0); d.notify(message);
    }
  }, [d]);
}
