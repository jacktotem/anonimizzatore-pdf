#!/bin/bash
# ============================================================
# Anonimizzatore PDF
# Installazione automatica per macOS
# Compatibile con Apple Silicon (M1/M2/M3/M4) e Intel
# ============================================================

# -e: ci si ferma al primo errore. pipefail: vale anche per i comandi
# il cui output passa da `tee` per finire nel log — senza, lo stato era
# quello di tee e un pip o un download falliti non fermavano nulla:
# lo script arrivava comunque a "INSTALLAZIONE COMPLETATA" (audit F2).
set -eo pipefail

# Con ANONIMIZZATORE_NON_INTERATTIVO=1 non si fanno domande (test in CI).
NON_INTERATTIVO="${ANONIMIZZATORE_NON_INTERATTIVO:-0}"

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/install-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_step() {
    echo ""
    echo -e "${GREEN}▶ $1${NC}"
    log "STEP: $1"
}

print_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    log "WARN: $1"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    log "ERROR: $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    log "OK: $1"
}

# Qualunque errore non gestito: messaggio chiaro, non un'uscita muta.
errore_imprevisto() {
    print_error "Installazione interrotta da un errore (riga $1)."
    echo "L'app NON è installata correttamente. Dettagli nel log:"
    echo "  $LOG_FILE"
}
trap 'errore_imprevisto $LINENO' ERR

# Elenco delle lingue di Tesseract. Catturato in una variabile: con
# pipefail, `tesseract --list-langs | grep -q` può dare falso anche se
# la lingua c'è (grep chiude la pipe appena trova la riga).
tesseract_ha_italiano() {
    local lingue
    lingue="$(tesseract --list-langs 2>&1 || true)"
    grep -q "^ita$" <<< "$lingue"
}

detect_arch() {
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        echo "Apple Silicon"
    else
        echo "Intel"
    fi
}

check_macos() {
    if [[ "$(uname)" != "Darwin" ]]; then
        print_error "Questo script funziona solo su macOS"
        exit 1
    fi
    
    MACOS_VERSION=$(sw_vers -productVersion)
    log "macOS versione: $MACOS_VERSION"
    print_success "macOS $MACOS_VERSION rilevato"
}

install_xcode_tools() {
    if xcode-select -p &> /dev/null; then
        print_success "Xcode Command Line Tools già installati"
        return 0
    fi
    
    print_step "Installazione Xcode Command Line Tools..."
    print_warn "Si aprirà una finestra di sistema. Clicca 'Installa' e attendi il completamento."
    
    xcode-select --install 2>/dev/null || true
    
    until xcode-select -p &> /dev/null; do
        sleep 5
        echo -n "."
    done
    echo ""
    
    print_success "Xcode Command Line Tools installati"
}

install_homebrew() {
    if command -v brew &> /dev/null; then
        print_success "Homebrew già installato"
        return 0
    fi
    
    print_step "Installazione Homebrew..."
    print_warn "Ti potrebbe essere chiesta la password del Mac. È normale."
    
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" 2>&1 | tee -a "$LOG_FILE"
    
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    if ! command -v brew &> /dev/null; then
        print_error "Installazione Homebrew fallita"
        exit 1
    fi
    
    print_success "Homebrew installato"
}

install_python() {
    if command -v python3.12 &> /dev/null; then
        print_success "Python 3.12 già installato"
        return 0
    fi
    
    print_step "Installazione Python 3.12 via Homebrew..."
    brew install python@3.12 2>&1 | tee -a "$LOG_FILE"
    
    if ! command -v python3.12 &> /dev/null; then
        brew link --overwrite python@3.12 2>&1 | tee -a "$LOG_FILE" || true
    fi
    
    if ! command -v python3.12 &> /dev/null; then
        print_error "Python 3.12 non disponibile dopo installazione"
        exit 1
    fi
    
    print_success "Python 3.12 installato"
}

install_tesseract() {
    if command -v tesseract &> /dev/null; then
        print_success "Tesseract già installato"
        
        if tesseract_ha_italiano; then
            print_success "Lingua italiana Tesseract già presente"
        else
            print_step "Installazione lingua italiana per Tesseract..."
            brew install tesseract-lang 2>&1 | tee -a "$LOG_FILE"
        fi
        return 0
    fi
    
    print_step "Installazione Tesseract OCR + pacchetti lingua..."
    brew install tesseract tesseract-lang 2>&1 | tee -a "$LOG_FILE"
    
    if ! command -v tesseract &> /dev/null; then
        print_error "Installazione Tesseract fallita"
        exit 1
    fi
    
    print_success "Tesseract installato con supporto italiano"
}

setup_venv() {
    print_step "Creazione ambiente virtuale Python..."
    
    if [[ -d "venv" ]]; then
        rm -rf venv
    fi
    
    python3.12 -m venv venv 2>&1 | tee -a "$LOG_FILE"
    
    if [[ ! -f "venv/bin/activate" ]]; then
        print_error "Creazione venv fallita"
        exit 1
    fi
    
    print_success "Ambiente virtuale creato"
    
    print_step "Installazione pacchetti Python..."
    source venv/bin/activate
    
    pip install --upgrade pip setuptools wheel 2>&1 | tee -a "$LOG_FILE"
    
    # F1: le librerie si leggono da requirements.txt, lo stesso elenco di
    # Windows e di aggiorna.sh. Prima qui c'era una copia a mano senza i
    # limiti superiori: un Mac appena installato riceveva PyMuPDF 2.x e
    # Pillow 13, versioni che il progetto esclude e che nessun test copre.
    if [[ ! -f "$REPO_ROOT/requirements.txt" ]]; then
        print_error "Manca requirements.txt nella cartella superiore a mac/."
        echo "Scarica la cartella completa del progetto, non solo mac/."
        exit 1
    fi
    print_step "Installazione librerie..."
    pip install --only-binary=:all: -r "$REPO_ROOT/requirements.txt" 2>&1 | tee -a "$LOG_FILE"
    shasum -a 256 "$REPO_ROOT/requirements.txt" | awk '{print $1}' > venv/.requirements-installati

    print_success "Pacchetti Python installati"
}

install_spacy_model() {
    print_step "Download modello linguistico italiano spaCy (~580 MB)..."
    print_warn "Questo passaggio richiede alcuni minuti..."
    
    source venv/bin/activate

    # Stesso file e stessa impronta che usa l'installer Windows: download
    # diretto dal rilascio ufficiale, verifica SHA256, installazione dal
    # file locale. La versione del modello (3.7.0) segue quella di spaCy
    # in requirements.txt (>=3.7.0,<3.8.0).
    local url="https://github.com/explosion/spacy-models/releases/download/it_core_news_lg-3.7.0/it_core_news_lg-3.7.0-py3-none-any.whl"
    local atteso="f48bd152621c872c1f177dbe21929fbb28751e73eb3c61714cf6344c6d582bbf"
    local cartella file ottenuto
    cartella="$(mktemp -d)"
    file="$cartella/it_core_news_lg-3.7.0-py3-none-any.whl"

    if ! curl -fL --retry 3 --retry-delay 5 -o "$file" "$url" 2>&1 | tee -a "$LOG_FILE"; then
        rm -rf "$cartella"
        print_error "Download del modello linguistico fallito (controlla la connessione)"
        exit 1
    fi
    ottenuto="$(shasum -a 256 "$file" | awk '{print $1}')"
    if [[ "$ottenuto" != "$atteso" ]]; then
        rm -rf "$cartella"
        print_error "Il modello scaricato non corrisponde all'impronta attesa: non viene installato"
        log "SHA256 atteso $atteso, ottenuto $ottenuto"
        exit 1
    fi
    pip install --no-deps "$file" 2>&1 | tee -a "$LOG_FILE"
    rm -rf "$cartella"

    print_success "Modello linguistico italiano installato"
}

create_app_bundle() {
    print_step "Creazione applicazione .app sul Desktop..."
    # Lo stesso script viene usato da aggiorna.sh per rigenerare l'icona
    # delle copie già installate.
    bash "$SCRIPT_DIR/crea-icona.sh" 2>&1 | tee -a "$LOG_FILE"
    print_success "App creata sul Desktop"
}

run_tests() {
    print_step "Verifica installazione..."
    
    source venv/bin/activate
    
    # Con pipefail ognuna di queste verifiche, se fallisce, ferma lo
    # script: "INSTALLAZIONE COMPLETATA" compare solo se sono passate.
    python -c "import streamlit, pyarrow, fitz, pytesseract, spacy; from presidio_analyzer import AnalyzerEngine; print('✓ Tutti i pacchetti Python importati')" 2>&1 | tee -a "$LOG_FILE"
    python -c "import spacy; nlp = spacy.load('it_core_news_lg'); print('✓ Modello italiano caricato')" 2>&1 | tee -a "$LOG_FILE"
    # Le librerie lavorano insieme? Tabella (pyarrow + numpy + pandas, il
    # guasto della 2.1.5) e redazione in due passate (PyMuPDF abbastanza
    # recente, e non una versione fuori dai limiti di requirements.txt).
    python - <<'PY' 2>&1 | tee -a "$LOG_FILE"
import inspect
import fitz, pandas, pyarrow
pyarrow.Table.from_pandas(pandas.DataFrame({"a": [1, 2]}))
assert "text" in inspect.signature(fitz.Page.apply_redactions).parameters, "PyMuPDF troppo vecchio"
assert hasattr(fitz.Document, "bake"), "PyMuPDF troppo vecchio"
assert int(fitz.VersionBind.split(".")[0]) < 2, f"PyMuPDF {fitz.VersionBind} fuori dai limiti"
print(f"✓ Librerie coerenti (PyMuPDF {fitz.VersionBind}, pyarrow {pyarrow.__version__})")
PY

    if ! tesseract_ha_italiano; then
        print_error "Tesseract non ha la lingua italiana: l'OCR leggerebbe male nomi e accenti"
        echo "Prova: brew install tesseract-lang   e rilancia questo script."
        exit 1
    fi
    log "✓ Tesseract italiano disponibile"

    print_success "Verifica completata"
}

main() {
    print_header "ANONIMIZZATORE PDF - INSTALLAZIONE MAC"
    
    log "Inizio installazione"
    log "Directory: $SCRIPT_DIR"
    log "Architettura: $(detect_arch)"
    
    echo "Questo script installerà:"
    echo "  • Xcode Command Line Tools (se mancanti)"
    echo "  • Homebrew (se mancante)"
    echo "  • Python 3.12 (se mancante)"
    echo "  • Tesseract OCR con italiano (se mancante)"
    echo "  • Tutte le librerie Python necessarie"
    echo "  • Il modello linguistico italiano (~580 MB)"
    echo ""
    echo "Tempo stimato: 10-20 minuti."
    echo ""
    if [[ "$NON_INTERATTIVO" != "1" ]]; then
        read -p "Premi INVIO per continuare, o CTRL+C per annullare..."
    fi
    
    check_macos
    install_xcode_tools
    install_homebrew
    install_python
    install_tesseract
    setup_venv
    install_spacy_model
    create_app_bundle
    run_tests
    
    print_header "✅ INSTALLAZIONE COMPLETATA"
    
    echo "L'app è ora disponibile sul Desktop come:"
    echo "  📱 \"Anonimizzatore PDF\""
    echo ""
    echo "Doppio click per avviarla."
    echo ""
    echo "Log dell'installazione salvato in:"
    echo "  $LOG_FILE"
    echo ""
    
    if [[ "$NON_INTERATTIVO" != "1" ]]; then
        read -p "Vuoi aprire l'app ora? (s/n): " open_now
        if [[ "$open_now" == "s" || "$open_now" == "S" ]]; then
            open "$HOME/Desktop/Anonimizzatore PDF.app"
        fi
    fi
}

main "$@"
