#!/bin/bash
# ============================================================
# sync-app.sh
#
# Mantiene src/app.py come UNICA fonte di verità.
# Copia in windows/app/app.py e mac/app.py prima della build.
#
# RISOLVE: I-03 (drift di sicurezza tra copie del file)
#
# Uso:
#   bash scripts/sync-app.sh
#
# Da lanciare PRIMA di:
# - Compilare l'installer Windows
# - Distribuire la cartella mac/
# - Pushare una release
# ============================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

SOURCE="$REPO_ROOT/src/app.py"
TARGETS=(
    "$REPO_ROOT/windows/app/app.py"
    "$REPO_ROOT/mac/app.py"
)

if [[ ! -f "$SOURCE" ]]; then
    echo "❌ Errore: $SOURCE non esiste"
    exit 1
fi

echo "📋 Sincronizzazione app.py da $SOURCE"

for target in "${TARGETS[@]}"; do
    target_dir="$( dirname "$target" )"
    mkdir -p "$target_dir"
    cp "$SOURCE" "$target"
    echo "  ✓ $target"
done

# Verifica che siano tutti uguali (hash check)
SOURCE_HASH=$( shasum -a 256 "$SOURCE" | awk '{print $1}' )
echo ""
echo "🔍 Verifica integrità (SHA256):"
echo "  src/app.py:         $SOURCE_HASH"

for target in "${TARGETS[@]}"; do
    target_hash=$( shasum -a 256 "$target" | awk '{print $1}' )
    if [[ "$target_hash" == "$SOURCE_HASH" ]]; then
        echo "  $( basename $( dirname "$target" ) )/app.py: $target_hash ✓"
    else
        echo "  $( basename $( dirname "$target" ) )/app.py: $target_hash ❌ MISMATCH"
        exit 1
    fi
done

echo ""
echo "✅ Sincronizzazione completata. Tutte le copie sono identiche."
