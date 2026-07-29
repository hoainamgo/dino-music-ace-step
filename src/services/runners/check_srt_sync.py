import sys, os, re, subprocess, pathlib
sys.stdout.reconfigure(encoding='utf-8')
os.environ['HF_HOME'] = r'C:\Apps\Model_TTS\hf_cache'
sys.path.insert(0, r'C:\Apps\Model_TTS\Kokoro-Vietnamese\src')
from kokoro_vietnamese import KokoroVietnamese
import numpy as np, soundfile as sf

def parse_srt(path):
    text = pathlib.Path(path).read_text(encoding='utf-8')
    blocks = re.split(r'\n\s*\n', text.strip())
    items = []
    for b in blocks:
        lines = b.strip().splitlines()
        if len(lines) < 3:
            continue
        m = re.match(r'(\d+):(\d+):([\d.]+)\s*-->\s*(\d+):(\d+):([\d.]+)', lines[1])
        if not m:
            continue
        start = int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))
        end = int(m.group(4))*3600+int(m.group(5))*60+float(m.group(6))
        items.append({'idx': lines[0].strip(), 'start': start, 'end': end, 'text': ' '.join(lines[2:])})
    return items

outdir = pathlib.Path('seg_wavs')
outdir.mkdir(exist_ok=True)
model = KokoroVietnamese(voice='my_yen')
items = parse_srt('input_short_vi.srt')
rows = []
for i, it in enumerate(items, 1):
    wav = outdir / f'seg_{i:02d}.wav'
    audio, _ = model.synthesize(it['text'], speed=1.0)
    sf.write(str(wav), np.asarray(audio, dtype=np.float32), 24000)
    p = subprocess.run(['ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=duration','-of','default=noprint_wrappers=1:nokey=1',str(wav)], capture_output=True, text=True)
    dur = float(p.stdout.strip() or '0')
    window = it['end'] - it['start']
    diff = dur - window
    rows.append((it['idx'], window, dur, diff))

print(f"{'#':<3}{'window':<10}{'gen_dur':<10}{'diff':<10}vietnamese")
for idx, window, dur, diff in rows:
    print(f"{idx:<3}{window:<10.2f}{dur:<10.2f}{diff:<+10.2f}")
print(f"\nTOTAL window={sum(r[1] for r in rows):.2f}s gen={sum(r[2] for r in rows):.2f}s diff={sum(r[3] for r in rows):+.2f}s")
