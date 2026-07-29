import { useCallback, useEffect, useRef, useState } from "react";

import { buildEnglishMusicPrompt, createAiMusicFileName, translateMusicDescriptionToEnglish } from "../lib/aiMusicPrompt.js";
import { repeatPcm16WavAtBestBoundary } from "../lib/aiMusicLoop.js";
import { decodeWaveform } from "../lib/media.js";
import { getModelSourcePreference } from "../lib/modelSources.js";
import { resolveBackend } from "../config/modelBackend.js";

export function useAiMusicGeneration({ activeLanguage, imageUrlRefs, setActiveTool, setMediaTab, setSelectedLibraryAssetId, setUserAssets }) {
  const workerRef = useRef(null);
  const [job, setJob] = useState({ state: "idle", progress: 0, phase: "", error: "" });

  const cancel = useCallback(() => {
    workerRef.current?.terminate();
    workerRef.current = null;
    setJob({ state: "idle", progress: 0, phase: "", error: "" });
  }, []);

  useEffect(() => cancel, [cancel]);

  const generate = useCallback(async (selection) => {
    setJob({ state: "running", progress: 0.64, phase: "translating", error: "" });
    let prompt;
    try {
      const descriptionEnglish = await translateMusicDescriptionToEnglish(selection.description || "", activeLanguage);
      prompt = buildEnglishMusicPrompt({ ...selection, descriptionEnglish });
    } catch (error) {
      setJob({ state: "error", progress: 0, phase: "", error: error?.message || String(error) });
      return;
    }

    const backend = resolveBackend("music");
    const requestedSeconds = Number(selection.seconds) || 30;

    if (backend === "deapi") {
      setJob({ state: "running", progress: 0.1, phase: "deapi-submitting", error: "" });
      try {
        const baseUrl = BACKENDS.deapi.baseUrl;
        const apiKey = BACKENDS.deapi.apiKey || "";
        const res = await fetch(`${baseUrl}/txt2audio`, {
          method: "POST",
          headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
          body: JSON.stringify({
            text: prompt,
            voice: process.env.VITE_DEAPI_MUSIC_VOICE || "Serena",
            model: process.env.VITE_DEAPI_MUSIC_MODEL || "ace-step-1.5",
            lang: "English",
            format: "mp3",
            sample_rate: 24000,
          }),
        });
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`DeAPI music failed: ${res.status} ${text}`);
        }
        const blob = await res.blob();
        const src = URL.createObjectURL(blob);
        imageUrlRefs.current.add(src);
        const asset = {
          id: crypto.randomUUID(), type: "audio", kind: "music",
          name: createAiMusicFileName(selection), meta: `AI music · ${requestedSeconds}s`,
          src, previewSrc: src, blob, duration: requestedSeconds, peaks: [],
          provider: `DeAPI ${process.env.VITE_DEAPI_MUSIC_MODEL || "ace-step-1.5"}`,
          generated: true, prompt,
        };
        setUserAssets((current) => [asset, ...current]);
        setSelectedLibraryAssetId(asset.id);
        setActiveTool("media"); setMediaTab("mine");
        setJob({ state: "complete", progress: 1, phase: "complete", error: "" });
        return;
      } catch (error) {
        setJob({ state: "error", progress: 0, phase: "", error: error?.message || String(error) });
        return;
      }
    }

    if (backend === "local") {
      setJob({ state: "running", progress: 0.1, phase: "local-submitting", error: "" });
      try {
        const musicUrl = BACKENDS.local.musicUrl;
        const res = await fetch(musicUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt, seconds: requestedSeconds }),
        });
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`Local music failed: ${res.status} ${text}`);
        }
        const blob = await res.blob();
        const src = URL.createObjectURL(blob);
        imageUrlRefs.current.add(src);
        const asset = {
          id: crypto.randomUUID(), type: "audio", kind: "music",
          name: createAiMusicFileName(selection), meta: `AI music · ${requestedSeconds}s`,
          src, previewSrc: src, blob, duration: requestedSeconds, peaks: [],
          provider: "Local music backend", generated: true, prompt,
        };
        setUserAssets((current) => [asset, ...current]);
        setSelectedLibraryAssetId(asset.id);
        setActiveTool("media"); setMediaTab("mine");
        setJob({ state: "complete", progress: 1, phase: "complete", error: "" });
        return;
      } catch (error) {
        setJob({ state: "error", progress: 0, phase: "", error: error?.message || String(error) });
        return;
      }
    }

    await navigator.storage?.persist?.().catch(() => false);
    const worker = workerRef.current ?? new Worker(new URL("../workers/ai-music.worker.js", import.meta.url), { type: "module" });
    const warmRuntime = Boolean(workerRef.current);
    workerRef.current = worker;
    setJob({ state: "running", progress: warmRuntime ? 0.64 : 0.01, phase: warmRuntime ? "conditioning" : "download", error: "" });
    worker.onmessage = async ({ data }) => {
      if (data.type === "progress") {
        setJob((current) => ({ ...current, progress: data.progress, phase: data.phase }));
        return;
      }
      if (data.type === "error") {
        worker.terminate();
        workerRef.current = null;
        setJob({ state: "error", progress: 0, phase: "", error: data.message });
        return;
      }
      if (data.type !== "complete") return;
      const wav = requestedSeconds > 60
        ? repeatPcm16WavAtBestBoundary(data.wav, 2, 5)
        : data.wav;
      const wavBlob = new Blob([wav], { type: "audio/wav" });
      const src = URL.createObjectURL(wavBlob);
      imageUrlRefs.current.add(src);
      const decoded = await decodeWaveform(wavBlob, 96);
      const asset = {
        id: crypto.randomUUID(),
        type: "audio",
        kind: "music",
        name: createAiMusicFileName(selection),
        meta: `AI music · ${decoded.duration.toFixed(1)}s`,
        src,
        previewSrc: src,
        blob: wavBlob,
        duration: decoded.duration,
        peaks: decoded.peaks,
        provider: "Stable Audio 3 Small · ONNX",
        generated: true,
        prompt,
      };
      setUserAssets((current) => [asset, ...current]);
      setSelectedLibraryAssetId(asset.id);
      setActiveTool("media");
      setMediaTab("mine");
      setJob({ state: "complete", progress: 1, phase: "complete", error: "" });
    };
    worker.onerror = (event) => {
      worker.terminate();
      workerRef.current = null;
      setJob({ state: "error", progress: 0, phase: "", error: event.message || "Music generation failed." });
    };
    worker.postMessage({
      type: "generate",
      prompt,
      seconds: requestedSeconds / (requestedSeconds > 60 ? 2 : 1),
      steps: 8,
      seed: Math.floor(Math.random() * 0x7fffffff),
      modelSourcePreference: getModelSourcePreference(activeLanguage),
    });
  }, [activeLanguage, imageUrlRefs, setActiveTool, setMediaTab, setSelectedLibraryAssetId, setUserAssets]);

  return { job, generate, cancel };
}
