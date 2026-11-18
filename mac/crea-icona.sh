#!/bin/bash
# ============================================================
# Anonimizzatore PDF - Icona sul Desktop (macOS)
#
# Crea (o ricrea) "Anonimizzatore PDF.app" sul Desktop: un piccolo
# launcher che apre il Terminale e avvia l'app da questa cartella.
# Lo chiamano installa.sh e aggiorna.sh; si può lanciare anche da solo
# se l'icona è stata cancellata o la cartella è stata spostata.
#
# Uso:  ./crea-icona.sh
# ============================================================

set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

generate_icon() {
    if [[ -f "$SCRIPT_DIR/AppIcon.icns" ]]; then
        :
        return 0
    fi
    
    if [[ ! -f "$SCRIPT_DIR/icon-1024.png" ]]; then
        echo "⚠️  PNG sorgente icona non trovato, l'app userà l'icona di default"
        return 0
    fi
    
    echo "▶ Generazione icona macOS .icns..."
    
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
    
    # l'icona è un abbellimento: se non si genera, si va avanti
    iconutil -c icns "$ICONSET_DIR" -o "$SCRIPT_DIR/AppIcon.icns" || true
    rm -rf "$ICONSET_DIR"
    
    if [[ -f "$SCRIPT_DIR/AppIcon.icns" ]]; then
        echo "✅ Icona .icns generata"
    fi
}

create_app_bundle() {
    echo "▶ Creazione applicazione .app sul Desktop..."
    
    APP_NAME="Anonimizzatore PDF"
    DESKTOP_PATH="$HOME/Desktop"
    APP_PATH="$DESKTOP_PATH/$APP_NAME.app"
    
    if [[ -d "$APP_PATH" ]]; then
        rm -rf "$APP_PATH"
    fi
    
    mkdir -p "$APP_PATH/Contents/MacOS"
    mkdir -p "$APP_PATH/Contents/Resources"

    local versione
    versione="$(grep -m1 '^__version__' "$SCRIPT_DIR/app.py" | sed 's/[^0-9.]*//g')"
    versione="${versione:-0.0.0}"

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
    <string>$versione</string>
    <key>CFBundleShortVersionString</key>
    <string>$versione</string>
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
    
    # Il percorso della cartella entra nel launcher con %q e passa ad
    # AppleScript come argomento ("quoted form of"): funziona anche con
    # spazi e apostrofi ("Documenti dell'avvocato"), che prima rompevano
    # il comando.
    # - PATH: Homebrew non è nel PATH di un Terminale appena aperto se
    #   l'utente non ha completato i suoi "Next steps"; senza, l'app
    #   partirebbe senza Tesseract.
    # - STREAMLIT_SERVER_SHOW_EMAIL_PROMPT: al primo avvio Streamlit si
    #   fermerebbe a chiedere un indirizzo email (che poi invia ai propri
    #   server). Le versioni che non conoscono l'opzione la ignorano.
    {
        echo '#!/bin/bash'
        printf 'INSTALL_DIR=%q\n' "$SCRIPT_DIR"
        cat <<'LAUNCHER'
if [[ ! -f "$INSTALL_DIR/venv/bin/activate" ]]; then
    osascript -e 'display alert "Errore" message "Ambiente virtuale non trovato. Lancia di nuovo installa.sh." as critical'
    exit 1
fi

osascript - "$INSTALL_DIR" <<'APPLESCRIPT'
on run argv
    set cartella to item 1 of argv
    tell application "Terminal"
        activate
        do script "cd " & quoted form of cartella & " && export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH STREAMLIT_SERVER_SHOW_EMAIL_PROMPT=false && source venv/bin/activate && streamlit run app.py --server.headless false --server.address 127.0.0.1 --browser.gatherUsageStats false"
    end tell
end run
APPLESCRIPT
LAUNCHER
    } > "$APP_PATH/Contents/MacOS/launch"
    
    chmod +x "$APP_PATH/Contents/MacOS/launch"
    
    if [[ -f "$SCRIPT_DIR/AppIcon.icns" ]]; then
        cp "$SCRIPT_DIR/AppIcon.icns" "$APP_PATH/Contents/Resources/AppIcon.icns"
    fi
    
    echo "✅ App creata: $APP_PATH"
}

generate_icon
create_app_bundle
