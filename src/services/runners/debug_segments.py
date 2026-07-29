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

seg_texts = [
  ('sep1', 'Hai anh em, hai le vat, hai tam long rat khac nhau.'),
  ('sep2', 'Ca-in la nong dan.'),
  ('sep3', 'A-ben la nguoi chan chien.'),
]

rows=[]
for i,(name,txt) in enumerate(seg_texts,1):
    audio,_ = model.synthesize(txt, speed=1.0)
    dur = len(audio)/24000
    wav = outdir / f'{name}.wav'
    sf.write(str(wav), np.asarray(audio, dtype=np.float32), 24000)
    print(f'{name} text={txt!r} dur={dur:.2f}s')
    rows.append(name)
print('DONE', flush=True)
