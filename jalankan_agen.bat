@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==============================================
echo   AI YouTube Agent
echo ==============================================

where python >nul 2>nul
if errorlevel 1 (
    echo Python belum terpasang. Unduh dari https://www.python.org/downloads/
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo Node.js belum terpasang. Unduh dari https://nodejs.org
    pause
    exit /b 1
)

if not exist venv (
    echo Membuat lingkungan Python untuk pertama kali...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet --disable-pip-version-check

if not exist .env (
    echo.
    echo File .env belum ada. Salin .env.example menjadi .env, lalu isi GEMINI_API_KEY.
    pause
    exit /b 1
)

REM Tambahkan --tanpa-upload di belakang nama file ini kalau hanya mau uji coba video
python main_agent.py %*

echo.
pause
