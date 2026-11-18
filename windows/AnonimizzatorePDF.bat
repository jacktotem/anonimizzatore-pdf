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
echo L'app si aprira' nel browser predefinito su http://127.0.0.1:8501
echo.
echo Per chiudere l'app: chiudere questa finestra (CTRL+C o X)
echo.

call venv\Scripts\activate.bat
rem Al primo avvio Streamlit si fermerebbe a chiedere un indirizzo email
rem (che poi invia ai propri server): non serve. Le versioni che non
rem conoscono l'opzione la ignorano.
set STREAMLIT_SERVER_SHOW_EMAIL_PROMPT=false

rem NET-01: solo questo computer. Senza --server.address Streamlit ascolta
rem su tutte le interfacce e l'app e' raggiungibile dalla rete locale.
python -m streamlit run app.py --server.headless false --server.address 127.0.0.1 --browser.gatherUsageStats false

pause
