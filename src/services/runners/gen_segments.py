import sys, os, re, subprocess, pathlib, json
sys.stdout.reconfigure(encoding='utf-8')
os.environ['HF_HOME'] = r'C:\Apps\Model_TTS\hf_cache'
sys.path.insert(0, r'C:\Apps\Model_TTS\Kokoro-Vietnamese\src')
from kokoro_vietnamese import KokoroVietnamese
import numpy as np, soundfile as sf

VOICE = 'my_yen'
basedir = pathlib.Path('C:/home/Lydia/ai-video-editor')
outdir = basedir / 'seg_wavs_v2'
outdir.mkdir(exist_ok=True)
model = KokoroVietnamese(voice=VOICE)

# Parse SRT
text = (basedir / 'input_short_vi.srt').read_text(encoding='utf-8')
blocks = re.split(r'\n\s*\n', text.strip())
items=[]
for b in blocks:
    lines=b.strip().splitlines()
    if len(lines)<3: continue
    m=re.match(r'(\d+):(\d+):([\d.]+)\s*-->\s*(\d+):(\d+):([\d.]+)', lines[1])
    if not m: continue
    s=int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))
    e=int(m.group(4))*3600+int(m.group(5))*60+float(m.group(6))
    items.append({'idx':lines[0],'start':s,'end':e,'text':' '.join(lines[2:])})

# Generate each segment
for i,it in enumerate(items,1):
    wav = outdir / f'seg_{i:02d}.wav'
    audio, _ = model.synthesize(it['text'], speed=1.0)
    sf.write(str(wav), np.asarray(audio, dtype=np.float32), 24000)
    print(f"{i:02d} win={it['end']-it['start']:.2f}s gen={len(audio)/24000:.2f}s text={it['text'][:40]}")

# Concatenate via file list
seg_files = [str((outdir / f'seg_{i+1:02d}.wav').resolve()) for i in range(len(items))]
concat_txt = outdir / 'concat.txt'
concat_txt.write_text('\n'.join(f"file '{p}'" for p in seg_files), encoding='utf-8')
out_wav = basedir / 'input_short_vi.wav'
p = subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat_txt),'-c','pcm_s16le','-ar','24000',str(out_wav)], capture_output=True, text=True)
print('FFMPEG_RC', p.returncode, flush=True)
if p.returncode != 0:
    print(p.stderr[-400:], flush=True)
else:
    print('WROTE', out_wav, flush=True)
