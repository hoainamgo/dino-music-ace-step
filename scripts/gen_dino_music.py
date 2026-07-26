#!/usr/bin/env python3
"""
gen_dino_music.py — Generate Dino Universe kids songs via DeAPI txt2music (DEFAULT: AceStep_1_5_Turbo)
Usage:
  export DEAPI_TOKEN="ID|SECRET"
  python3 gen_dino_music.py --id 1            # generate KidsSongs ID 1 (Rex's Morning Song) [Turbo]
  python3 gen_dino_music.py --title "Anthem"  # generate the Anthem [Turbo]
  python3 gen_dino_music.py --all             # generate all (serialized, 45s gap) [Turbo]
  python3 gen_dino_music.py --id 1 --model AceStep_1_5_Base  # higher quality variant
"""
import os, sys, json, time, re, requests, argparse

TOKEN = os.environ.get("DEAPI_TOKEN")
HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Origin": "https://deapi.ai",
    "Referer": "https://deapi.ai/",
    "Authorization": f"Bearer {TOKEN}" if TOKEN else "",
    "accept": "application/json",
    "Content-Type": "application/json",
}
BASE = "https://api.deapi.ai/api/v1/client"
URL = f"{BASE}/txt2music"
MUSICS = "/mnt/c/home/xiaoyen/Dino Universe/audio/musics.json"
OUTDIR = "/mnt/c/home/xiaoyen/Dino Universe/audio/generated"

def slugify(s):
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')

def load_songs():
    with open(MUSICS, encoding="utf-8") as f:
        d = json.load(f)
    songs = []
    ant = d["DinoUniverseMusics"].get("Anthem")
    if ant:
        songs.append({"_key": "Anthem", **ant})
    for s in d["DinoUniverseMusics"].get("KidsSongsForSuno", []):
        songs.append(s)
    return songs

def build_lyrics(song):
    sl = song.get("StructuredLyrics", {})
    lines = []
    # order: Verse1, Chorus, Verse2, Bridge, Chorus2, Outro
    order = ["Verse1", "Chorus", "Verse2", "Bridge", "Chorus2", "Outro"]
    # if no numbered, try generic keys
    if not any(k in sl for k in order):
        for k, v in sl.items():
            if isinstance(v, list):
                lines += v
    for k in order:
        v = sl.get(k)
        if isinstance(v, list):
            lines += v
        elif isinstance(v, str):
            lines.append(v)
    # strip [stage directions]
    lines = [l for l in lines if l and not (l.strip().startswith("[") and l.strip().endswith("]"))]
    return "\n".join(lines)

def build_caption(song):
    base = song.get("SunoPrompt", "")
    style = song.get("Style", "")
    child_hint = "sung by a sweet young child voice, cute kid singing"
    parts = [f"{style}" if style else "", base, child_hint]
    return ", ".join(p for p in parts if p)

def submit(payload):
    r = requests.post(URL, headers=HDR, json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"SUBMIT_FAIL {r.status_code} {r.text[:300]}")
    return r.json()["data"]["request_id"]

def poll(rid, timeout=600):
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        r = requests.get(f"{BASE}/request-status/{rid}", headers=HDR, timeout=30)
        j = r.json()
        st = j.get("data", {}).get("status") or j.get("status")
        if st != last:
            print("  STATUS:", st); last = st
        if str(st).lower() in ("done", "completed", "success", "succeeded"):
            d = j.get("data", {})
            for k in ("result_url", "output", "result"):
                if k in d and d[k]:
                    v = d[k]
                    return v if isinstance(v, str) else (v[0] if isinstance(v, list) else v.get("url"))
            return d.get("url")
        time.sleep(8)
    return None

def download(url, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = requests.get(url, headers=HDR, timeout=300)
    if r.status_code == 200 and len(r.content) > 1000:
        ext = "flac"
        if "audio/mpeg" in r.headers.get("Content-Type", ""): ext = "mp3"
        if url.endswith(".mp3"): ext = "mp3"
        if url.endswith(".wav"): ext = "wav"
        path = out if out.endswith(f".{ext}") else f"{out}.{ext}"
        with open(path, "wb") as f:
            f.write(r.content)
        print("  SAVED", path, len(r.content)//1024, "KB")
        return path
    print("  DL_FAIL", r.status_code, len(r.content))
    return None

def gen_one(song, gap=45, model="AceStep_1_5_Base"):
    title = song.get("Title", song.get("_key", "song"))
    sid = song.get("ID", song.get("_key", "x"))
    model_tag = "turbo" if "Turbo" in model else "base"
    slug = slugify(f"{sid}_{title}_{model_tag}")
    out = os.path.join(OUTDIR, slug)
    if os.path.exists(out) or any(os.path.exists(out + e) for e in (".flac", ".mp3", ".wav")):
        print(f"[SKIP] {title} (exists)")
        return
    print(f"[GEN] {title}")
    lyrics = build_lyrics(song)
    caption = build_caption(song)
    dur = 30
    m = re.search(r"(\d+):(\d+)", str(song.get("Duration", "")))
    if m:
        dur = int(m.group(1)) * 60 + int(m.group(2))
        dur = min(max(dur, 20), 240)
    payload = {
        "caption": caption,
        "lyrics": lyrics,
        "model": model,
        "duration": dur,
        "inference_steps": 8,
        # AceStep_1_5_Turbo requires guidance_scale <= 1
        "guidance_scale": 1.0 if "Turbo" in model else 3,
        "seed": -1,
        "format": "flac",
        "vocal_language": "en",
    }
    print("  CAPTION:", caption[:120])
    rid = submit(payload)
    url = poll(rid)
    if url:
        download(url, out)
    else:
        print("  NO_URL")
    if gap:
        print(f"  wait {gap}s...")
        time.sleep(gap)

def main():
    if not TOKEN:
        print("NO DEAPI_TOKEN"); sys.exit(1)
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int)
    ap.add_argument("--title", type=str)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--model", type=str, default="AceStep_1_5_Turbo",
                    help="Model name, default AceStep_1_5_Turbo (fast). Use AceStep_1_5_Base for higher quality.")
    args = ap.parse_args()
    songs = load_songs()
    if args.all:
        for s in songs: gen_one(s, model=args.model)
    elif args.id is not None:
        s = next((x for x in songs if x.get("ID") == args.id), None)
        if not s: print("ID not found"); sys.exit(1)
        gen_one(s, gap=0, model=args.model)
    elif args.title:
        s = next((x for x in songs if getattr(x,'get',lambda k:None) and (args.title.lower() in x.get("Title","").lower() or args.title.lower() in x.get("_key","").lower())), None)
        if not s: print("Title not found"); sys.exit(1)
        gen_one(s, gap=0, model=args.model)
    else:
        print("Use --id N | --title NAME | --all"); sys.exit(1)

if __name__ == "__main__":
    main()
