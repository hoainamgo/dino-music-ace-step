@echo off
ffmpeg -y -i input_short_vi_dub.mp4 -vf "subtitles=input_short_vi.srt" -c:a copy input_short_vi_final.mp4
