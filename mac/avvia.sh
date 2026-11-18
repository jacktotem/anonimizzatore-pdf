#!/bin/bash
# ============================================================
# Anonimizzatore PDF - Avvio rapido (macOS)
# ============================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [[ ! -f "venv/bin/activate" ]]; then
    osascript -e 'display alert "Errore" message "L'\''app non è ancora installata. Lancia prima installa.sh nella stessa cartella." as critical'
    exit 1
fi

echo ""
echo "============================================"
echo " Anonimizzatore PDF"
echo " Avvio in corso..."
echo "============================================"
echo ""
echo "L'app si aprirà nel browser su http://127.0.0.1:8501"
echo "Per chiudere: CTRL+C in questo terminale"
echo ""

# Homebrew (e quindi Tesseract) non è sempre nel PATH del Terminale
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
# Al primo avvio Streamlit si fermerebbe a chiedere un indirizzo email:
# non serve, e l'app non deve inviare nulla. Le versioni che non
# conoscono l'opzione la ignorano.
export STREAMLIT_SERVER_SHOW_EMAIL_PROMPT=false

source venv/bin/activate
# NET-01: solo questo computer. Senza --server.address Streamlit ascolta
# su tutte le interfacce e l'app è raggiungibile dalla rete locale.
streamlit run app.py --server.headless false --server.address 127.0.0.1 --browser.gatherUsageStats false
