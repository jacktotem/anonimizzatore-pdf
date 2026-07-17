#!/bin/bash
# ============================================================
# Anonimizzatore PDF - Aggiornamento all'ultima versione (macOS)
#
# Scarica l'ultima versione dal repository e aggiorna le librerie
# SOLO se sono cambiate. Tipicamente ci mette pochi secondi.
#
# Uso:  ./aggiorna.sh
# ============================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$REPO_ROOT"

echo ""
echo "============================================"
echo " Anonimizzatore PDF - Aggiornamento"
echo "============================================"
echo ""

if [[ ! -d .git ]]; then
    echo "❌ Questa copia non è stata scaricata con git clone, quindi non"
    echo "   può aggiornarsi da sola. Scarica l'ultima versione da:"
    echo ""
    echo "   https://github.com/jacktotem/anonimizzatore-pdf/releases/latest"
    echo ""
    exit 1
fi

if [[ ! -f "$SCRIPT_DIR/venv/bin/activate" ]]; then
    echo "❌ App non ancora installata. Lancia prima installa.sh"
    exit 1
fi

echo "📥 Controllo l'ultima versione..."
git fetch origin main

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [[ "$LOCAL" == "$REMOTE" ]]; then
    echo "✅ Sei già all'ultima versione."
    exit 0
fi

REQ_BEFORE=$(shasum "$REPO_ROOT/requirements.txt" | awk '{print $1}')

echo "📦 Scarico gli aggiornamenti..."
git pull --ff-only origin main

REQ_AFTER=$(shasum "$REPO_ROOT/requirements.txt" | awk '{print $1}')

if [[ "$REQ_BEFORE" != "$REQ_AFTER" ]]; then
    echo "🔧 Le librerie sono cambiate: le aggiorno (può volerci qualche minuto)..."
    source "$SCRIPT_DIR/venv/bin/activate"
    pip install -r "$REPO_ROOT/requirements.txt"
else
    echo "✓ Librerie invariate: nessun download necessario."
fi

VERSIONE=$(grep -m1 '__version__' "$REPO_ROOT/src/app.py" | sed 's/[^0-9.]*//g')
echo ""
echo "✅ Aggiornamento completato: ora sei alla versione ${VERSIONE:-più recente}."
echo "   Se l'app era aperta, chiudila e rilanciala con avvia.sh"
