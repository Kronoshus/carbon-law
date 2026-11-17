@echo off
rem Double-click to start the avatar: runs the server (if it is not already running) and opens the page
rem in the default browser. Optional first argument: the page to open, for example "?guion=guion-plan&lang=en".
rem Uses the voice-venv Python (free local voices + Whisper) when it is installed.
cd /d "%~dp0"
set "PAGE=%~1"
set PY=python
if exist "%USERPROFILE%\avatar-tools\voice-venv\Scripts\python.exe" set PY="%USERPROFILE%\avatar-tools\voice-venv\Scripts\python.exe"
curl -s -o nul http://127.0.0.1:8765/ && goto open
start "Avatar server - close this window to stop" /min %PY% server.py
rem wait until the server answers (up to about 60 seconds)
for /l %%i in (1,1,60) do (
  curl -s -o nul http://127.0.0.1:8765/ && goto open
  timeout /t 1 /nobreak >nul
)
echo The avatar server did not start. Look at the "Avatar server" window for the error.
pause
exit /b 1
:open
start "" "http://127.0.0.1:8765/%PAGE%"
