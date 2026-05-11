#!/bin/bash
# ============================================================
# Anonimizzatore PDF
# Installazione automatica per macOS
# Compatibile con Apple Silicon (M1/M2/M3/M4) e Intel
# ============================================================

set -e

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
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
        
        if tesseract --list-langs 2>&1 | grep -q "^ita$"; then
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
    
    print_step "Installazione librerie..."
    pip install --only-binary=:all: \
        "streamlit>=1.30.0" \
        "pymupdf>=1.23.0" \
        "presidio-analyzer>=2.2.0" \
        "presidio-anonymizer>=2.2.0" \
        "spacy>=3.7.0,<3.8.0" \
        "pytesseract>=0.3.10" \
        "Pillow>=10.0.0" 2>&1 | tee -a "$LOG_FILE"
    
    print_success "Pacchetti Python installati"
}

install_spacy_model() {
    print_step "Download modello linguistico italiano spaCy (~580 MB)..."
    print_warn "Questo passaggio richiede alcuni minuti..."
    
    source venv/bin/activate
    python -m spacy download it_core_news_lg 2>&1 | tee -a "$LOG_FILE"
    
    if [[ $? -ne 0 ]]; then
        print_error "Download modello spaCy fallito"
        exit 1
    fi
    
    print_success "Modello linguistico italiano installato"
}

generate_icon() {
    if [[ -f "$SCRIPT_DIR/AppIcon.icns" ]]; then
        log "Icona .icns già presente"
        return 0
    fi
    
    if [[ ! -f "$SCRIPT_DIR/icon-1024.png" ]]; then
        print_warn "PNG sorgente icona non trovato, l'app userà l'icona di default"
        return 0
    fi
    
    print_step "Generazione icona macOS .icns..."
    
    ICONSET_DIR="$SCRIPT_DIR/AppIcon.iconset"
    mkdir -p "$ICONSET_DIR"
    
    sips -z 16 16     "$SCRIPT_DIR/icon-1024.png" --out "$ICONSET_DIR/icon_16x16.png" &> /dev/null
    sips -z 32 32     "$SCRIPT_DIR/icon-1024.png" --out "$ICONSET_DIR/icon_16x16@2x.png" &> /dev/null
    sips -z 32 32     "$SCRIPT_DIR/icon-1024.png" --out "$ICONSET_DIR/icon_32x32.png" &> /dev/null
    sips -z 64 64     "$SCRIPT_DIR/icon-1024.png" --out "$ICONSET_DIR/icon_32x32@2x.png" &> /dev/null
    sips -z 128 128   "$SCRIPT_DIR/icon-1024.png" --out "$ICONSET_DIR/icon_128x128.png" &> /dev/null
    sips -z 256 256   "$SCRIPT_DIR/icon-1024.png" --out "$ICONSET_DIR/icon_128x128@2x.png" &> /dev/null
    sips -z 256 256   "$SCRIPT_DIR/icon-1024.png" --out "$ICONSET_DIR/icon_256x256.png" &> /dev/null
    sips -z 512 512   "$SCRIPT_DIR/icon-1024.png" --out "$ICONSET_DIR/icon_256x256@2x.png" &> /dev/null
    sips -z 512 512   "$SCRIPT_DIR/icon-1024.png" --out "$ICONSET_DIR/icon_512x512.png" &> /dev/null
    cp "$SCRIPT_DIR/icon-1024.png" "$ICONSET_DIR/icon_512x512@2x.png"
    
    iconutil -c icns "$ICONSET_DIR" -o "$SCRIPT_DIR/AppIcon.icns" 2>&1 | tee -a "$LOG_FILE"
    rm -rf "$ICONSET_DIR"
    
    if [[ -f "$SCRIPT_DIR/AppIcon.icns" ]]; then
        print_success "Icona .icns generata"
    fi
}

create_app_bundle() {
    print_step "Creazione applicazione .app sul Desktop..."
    
    APP_NAME="Anonimizzatore PDF"
    DESKTOP_PATH="$HOME/Desktop"
    APP_PATH="$DESKTOP_PATH/$APP_NAME.app"
    
    if [[ -d "$APP_PATH" ]]; then
        rm -rf "$APP_PATH"
    fi
    
    mkdir -p "$APP_PATH/Contents/MacOS"
    mkdir -p "$APP_PATH/Contents/Resources"
    
    cat > "$APP_PATH/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launch</string>
    <key>CFBundleIdentifier</key>
    <string>com.anonimizzatorepdf.app</string>
    <key>CFBundleName</key>
    <string>Anonimizzatore PDF</string>
    <key>CFBundleDisplayName</key>
    <string>Anonimizzatore PDF</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
EOF
    
    cat > "$APP_PATH/Contents/MacOS/launch" <<EOF
#!/bin/bash
INSTALL_DIR="$SCRIPT_DIR"
cd "\$INSTALL_DIR"

if [[ ! -f "\$INSTALL_DIR/venv/bin/activate" ]]; then
    osascript -e 'display alert "Errore" message "Ambiente virtuale non trovato. Lancia di nuovo installa.sh." as critical'
    exit 1
fi

osascript <<APPLESCRIPT
tell application "Terminal"
    activate
    do script "cd '\$INSTALL_DIR' && source venv/bin/activate && streamlit run app.py --server.headless false --browser.gatherUsageStats false"
end tell
APPLESCRIPT
EOF
    
    chmod +x "$APP_PATH/Contents/MacOS/launch"
    
    if [[ -f "$SCRIPT_DIR/AppIcon.icns" ]]; then
        cp "$SCRIPT_DIR/AppIcon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
    fi
    
    print_success "App creata: $APP_PATH"
}

run_tests() {
    print_step "Verifica installazione..."
    
    source venv/bin/activate
    
    python -c "import streamlit, fitz, pytesseract, spacy; from presidio_analyzer import AnalyzerEngine; print('✓ Tutti i pacchetti Python importati')" 2>&1 | tee -a "$LOG_FILE"
    python -c "import spacy; nlp = spacy.load('it_core_news_lg'); print('✓ Modello italiano caricato')" 2>&1 | tee -a "$LOG_FILE"
    
    if tesseract --list-langs 2>&1 | grep -q "^ita$"; then
        log "✓ Tesseract italiano disponibile"
    fi
    
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
    read -p "Premi INVIO per continuare, o CTRL+C per annullare..."
    
    check_macos
    install_xcode_tools
    install_homebrew
    install_python
    install_tesseract
    setup_venv
    install_spacy_model
    generate_icon
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
    
    read -p "Vuoi aprire l'app ora? (s/n): " open_now
    if [[ "$open_now" == "s" || "$open_now" == "S" ]]; then
        open "$HOME/Desktop/Anonimizzatore PDF.app"
    fi
}

main "$@"
