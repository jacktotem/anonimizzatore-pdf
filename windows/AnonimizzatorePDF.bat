@echo off
chcp 65001 >nul
title Anonimizzatore PDF

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo.
    echo ============================================
    echo  ERRORE: ambiente virtuale non trovato
    echo ============================================
    echo.
    echo L'applicazione non e' stata configurata correttamente.
    echo Reinstallare usando AnonimizzatorePDF-Setup.exe
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Anonimizzatore PDF
echo  Avvio in corso...
echo ============================================
echo.
echo L'app si aprira' nel browser predefinito su http://localhost:8501
echo.
echo Per chiudere l'app: chiudere questa finestra (CTRL+C o X)
echo.

call venv\Scripts\activate.bat
python -m streamlit run app.py --server.headless false --browser.gatherUsageStats false

pause
