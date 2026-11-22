@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found - creating one and installing dependencies...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -q -r requirements-translate.txt
    rem NVIDIA GPU present? Install the CUDA libraries so transcription runs on it
    rem (several times faster - see README "GPU transcription").
    where nvidia-smi >nul 2>nul && (
        echo NVIDIA GPU detected - installing GPU transcription support...
        ".venv\Scripts\python.exe" -m pip install -q -r requirements-gpu.txt
    )
    rem Download via the OS certificate store, so this also works behind
    rem antivirus/proxies that re-sign HTTPS (plain `spacy download` fails there).
    ".venv\Scripts\python.exe" -c "import truststore; truststore.inject_into_ssl(); from spacy.cli import download; download('en_core_web_sm')"
)

".venv\Scripts\python.exe" run.py %*

echo.
pause
