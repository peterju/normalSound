@echo off
pyinstaller --add-binary "env/Lib/site-packages/tkinterdnd2:tkinterdnd2" --add-data "ffmpeg/ffmpeg.exe:ffmpeg" --name=音量一致化工具 main.py