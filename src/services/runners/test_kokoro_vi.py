import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
os.environ['HF_HOME'] = r'C:\Apps\Model_TTS\hf_cache'
sys.path.insert(0, r'C:\Apps\Model_TTS\Kokoro-Vietnamese\src')
from kokoro_vietnamese import KokoroVietnamese
import numpy as np, soundfile as sf
text = open('input_short_vi.txt','r',encoding='utf-8').read()
print('TEXT_LEN', len(text))
model = KokoroVietnamese(voice='my_yen')
t0 = time.time()
audio, _ = model.synthesize(text, speed=1.0)
print('SYNTH_DUR', len(audio)/24000, 'GEN_TIME', time.time()-t0)
sf.write('input_short_vi.wav', np.asarray(audio, dtype=np.float32), 24000)
print('WROTE input_short_vi.wav')
