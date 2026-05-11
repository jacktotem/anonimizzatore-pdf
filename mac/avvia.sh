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
echo "L'app si aprirà nel browser su http://localhost:8501"
echo "Per chiudere: CTRL+C in questo terminale"
echo ""

source venv/bin/activate
streamlit run app.py --server.headless false --browser.gatherUsageStats false
