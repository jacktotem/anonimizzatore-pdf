#!/bin/bash
# ============================================================
# Anonimizzatore PDF - Aggiornamento all'ultima versione (macOS)
#
# Porta questa copia all'ULTIMA VERSIONE RILASCIATA e allinea le
# librerie. Tipicamente ci mette pochi secondi.
#
# Uso:  ./aggiorna.sh
# ============================================================

set -eo pipefail

# Tutto dentro una funzione: bash legge il file man mano che lo esegue,
# e l'aggiornamento sostituisce proprio questo file.
main() {
    local SCRIPT_DIR REPO_ROOT
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
        echo "   poi lancia installa.sh nella nuova cartella."
        exit 1
    fi

    if [[ ! -f "$SCRIPT_DIR/venv/bin/activate" ]]; then
        echo "❌ App non ancora installata. Lancia prima installa.sh"
        exit 1
    fi

    # --- 1. Programma: ultima versione RILASCIATA, non l'ultimo commit ---
    # Prima si scaricava il ramo main: qualunque modifica appena unita,
    # anche non ancora rilasciata né provata, arrivava subito sui Mac.
    echo "📥 Controllo l'ultima versione rilasciata..."
    git fetch -q --tags origin

    local ULTIMA ATTUALE META
    ULTIMA="$(git tag -l 'v[0-9]*' --sort=-v:refname | sed -n 1p)"
    if [[ -z "$ULTIMA" ]]; then
        echo "❌ Non trovo versioni rilasciate. Controlla la connessione e riprova."
        exit 1
    fi
    ATTUALE="$(git rev-parse HEAD)"
    META="$(git rev-parse "$ULTIMA^{commit}")"

    if [[ "$ATTUALE" == "$META" ]]; then
        echo "✅ Il programma è già all'ultima versione ($ULTIMA)."
    else
        if ! git diff --quiet || ! git diff --cached --quiet; then
            echo "❌ In questa cartella ci sono file del programma modificati a mano:"
            git status --short | sed 's/^/     /'
            echo "   Per non sovrascriverli mi fermo. Rimetti a posto quei file"
            echo "   (o scarica una copia nuova) e rilancia."
            exit 1
        fi
        echo "📦 Passo alla versione $ULTIMA..."
        git checkout -q --detach "$ULTIMA"
    fi

    # --- 2. Librerie: allineate a requirements.txt ---
    # Si confronta con l'impronta dell'ultima installazione RIUSCITA, non
    # con lo stato di git: se un aggiornamento precedente si è interrotto
    # a metà, qui viene ripreso invece di dire "sei già aggiornato".
    local REQ MARCA
    REQ="$(shasum -a 256 "$REPO_ROOT/requirements.txt" | awk '{print $1}')"
    MARCA="$SCRIPT_DIR/venv/.requirements-installati"
    if [[ ! -f "$MARCA" || "$(cat "$MARCA")" != "$REQ" ]]; then
        echo "🔧 Allineo le librerie (può volerci qualche minuto)..."
        # shellcheck disable=SC1091
        source "$SCRIPT_DIR/venv/bin/activate"
        pip install --only-binary=:all: -r "$REPO_ROOT/requirements.txt"
        python -c "import streamlit, pyarrow, fitz, pytesseract, spacy; from presidio_analyzer import AnalyzerEngine"
        echo "$REQ" > "$MARCA"
        echo "✓ Librerie aggiornate."
    else
        echo "✓ Librerie già allineate: nessun download necessario."
    fi

    # --- 3. Icona sul Desktop ---
    # Ha il comando di avvio scritto dentro: va rigenerata, altrimenti
    # resterebbe quello della versione con cui è stata creata. Solo se
    # l'icona c'è già: chi l'ha tolta non se la ritrova.
    if [[ -d "$HOME/Desktop/Anonimizzatore PDF.app" && -f "$SCRIPT_DIR/crea-icona.sh" ]]; then
        bash "$SCRIPT_DIR/crea-icona.sh" > /dev/null
        echo "✓ Icona sul Desktop aggiornata."
    fi

    local VERSIONE
    VERSIONE="$(grep -m1 '^__version__' "$SCRIPT_DIR/app.py" | sed 's/[^0-9.]*//g')"
    echo ""
    echo "✅ Fatto: versione ${VERSIONE:-più recente}."
    echo "   Se l'app era aperta, chiudila e rilanciala."
}

main "$@"; exit $?
