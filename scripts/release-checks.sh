#!/usr/bin/env bash
# Pre-release sanity checks. Eseguire dalla repo root.
# Invocato da .github/workflows/test.yml a ogni PR e a ogni push su main.
#
# Copre:
#   #5  — placeholder email mai sostituiti (REPLACE-BEFORE-MERGE / [inserire email])
#   #1  — placeholder hash mai sostituiti (AGGIORNARE_AL_PRIMO_RILASCIO)
#   #10 — entry CHANGELOG mancante per il tag corrente
#   #11 — versione non coerente tra app.py, installer.iss e CHANGELOG
set -euo pipefail

fail=0

echo "Checking for unsubstituted email placeholders (#5)..."
# Esclude:
#   - RELEASE-GUIDE.md / RELEASE-PROCEDURE-*.md: doc della procedura di
#     sostituzione, contengono il pattern by design
#   - CHANGELOG.md: descrive cosa è successo nel placeholder (#5)
# I .txt sono inclusi: windows/README-UTENTE.txt viene mostrato a fine
# installazione e per mesi ha riportato "scrivi a: [inserire email]".
if grep -rn --include='*.md' --include='*.txt' \
        --exclude='RELEASE-GUIDE.md' \
        --exclude='RELEASE-PROCEDURE-*.md' \
        --exclude='CHANGELOG.md' \
        -e 'REPLACE-BEFORE-MERGE@example\.invalid' \
        -e '\[inserire email' \
        . 2>/dev/null; then
    echo "::error::Sostituire i placeholder email prima del tag (#5)"
    fail=1
fi

echo "Checking for unsubstituted hash placeholders (#1)..."
if grep -rn 'AGGIORNARE_AL_PRIMO_RILASCIO' windows/ 2>/dev/null \
        | grep -v 'IsNullOrEmpty\|placeholder\|TODO(release)\|#' ; then
    echo "::error::Sostituire i placeholder SHA256 prima del tag (#1)"
    fail=1
fi

echo "Checking CHANGELOG entry for current tag (#10)..."
# GITHUB_REF_NAME è popolato da GitHub Actions su tag push (es. "v1.1.2").
if [ -n "${GITHUB_REF_NAME:-}" ] && [[ "$GITHUB_REF_NAME" =~ ^v[0-9] ]]; then
    version="${GITHUB_REF_NAME#v}"
    if ! grep -q "^## \[$version\]" CHANGELOG.md; then
        echo "::error::CHANGELOG.md non ha entry per $GITHUB_REF_NAME (#10)"
        fail=1
    fi
fi

echo "Checking version consistency (#11)..."
v_app=$(grep -m1 '^__version__' src/app.py | sed 's/[^0-9.]*//g')
v_iss=$(grep -m1 '#define MyAppVersion' windows/installer.iss | sed 's/[^0-9.]*//g')
v_log=$(grep -m1 -E '^## \[[0-9]' CHANGELOG.md | sed -E 's/^## \[([0-9.]+)\].*/\1/')
if [ "$v_app" != "$v_iss" ] || [ "$v_app" != "$v_log" ]; then
    echo "::error::Versioni diverse: app.py $v_app, installer.iss $v_iss, CHANGELOG $v_log (#11)"
    fail=1
fi
if [ -n "${GITHUB_REF_NAME:-}" ] && [[ "$GITHUB_REF_NAME" =~ ^v[0-9] ]] \
        && [ "${GITHUB_REF_NAME#v}" != "$v_app" ]; then
    echo "::error::Il tag $GITHUB_REF_NAME non corrisponde alla versione di app.py ($v_app) (#11)"
    fail=1
fi

if [ "$fail" -eq 0 ]; then
    echo "All release checks passed."
fi
exit "$fail"
