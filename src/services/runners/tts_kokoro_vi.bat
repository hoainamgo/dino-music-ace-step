@echo off
setlocal
set HF_HOME=C:\Apps\Model_TTS\hf_cache
set PYTHONNOUSERSITE=1
"C:\Apps\8B707~1.VID\VENV~1\Scripts\python.exe" -c ^
"import os, sys; os.environ['HF_HOME']=r'C:\Apps\Model_TTS\hf_cache'; sys.path=[r'C:\Apps\8B707~1.VID\VENV~1\lib\site-packages', r'C:\Apps\Model_TTS\Kokoro-Vietnamese\kokoro']; from kokoro import KokoroVietnamese; import numpy as np, soundfile as sf; model=KokoroVietnamese(voice='my_yen'); audio,_=model.synthesize(sys.argv[1], speed=float(sys.argv[2])); out=sys.argv[3]; sf.write(out, np.asarray(audio, dtype=np.float32), 24000); print('WROTE', out, len(audio)/24000)"
%~1 %~2 %~3
