@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found - creating one and installing dependencies...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -q -r requirements-translate.txt
    ".venv\Scripts\python.exe" -m spacy download en_core_web_sm
)

".venv\Scripts\python.exe" run.py %*

echo.
pause
