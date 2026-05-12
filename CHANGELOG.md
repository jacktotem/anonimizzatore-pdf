# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.2] - 2026-05-12

Security release in risposta all'audit esterno post-v1.1.1. Chiude tutte
le 10 issue aperte (`#1` – `#10`).

### Security
- **Sanitize JS:** rimosso il guard inesistente `doc.get_js()` che
  intrappolava silenziosamente un `AttributeError`. Il loop di pulizia
  degli xref JavaScript non era **mai** eseguito da v1.0.0: PDF con
  `/OpenAction` JavaScript sopravvivevano alla "sanitizzazione". (`#2`)
- **Sanitize catalog:** dopo lo svuotamento degli xref JS, vengono ora
  strippati anche i riferimenti `/OpenAction`, `/AA` e
  `/Names/JavaScript` dal catalog. Il PDF anonimizzato non annuncia più
  di aver mai contenuto JavaScript. (`#3`)
- **Sanitize attachments:** `embfile_del()` ora viene chiamato per indice
  intero invece che per filename. La vecchia logica cancellava solo la
  prima occorrenza di nomi duplicati — comune nei PDF prodotti da Acrobat
  o Word export, dove un allegato `.docx` con PII poteva sopravvivere
  silenziosamente. (`#4`)
- **Installer Windows:** corretto il SHA256 di Python 3.12.8. Il valore
  pinnato precedente non corrispondeva al file reale di python.org,
  quindi l'installer falliva sempre la verifica di integrità su macchine
  senza Python pre-installato. (`#1`)
- **Installer Windows:** hash placeholder o vuoto ora fa fallire il
  setup in produzione, tranne se viene passato esplicitamente
  `-DevMode`. La vecchia logica accettava silenziosamente download non
  verificati, vanificando la claim di hash pinning. (`#1`)

### Added
- `tests/` con suite pytest minima e PDF fixtures riproducibili.
  Regression guard per `#2`, `#3`, `#4`, più verifica della claim di
  azzeramento metadata. (`#8`)
- `.streamlit/config.toml` con `maxUploadSize = 100` MB e
  `gatherUsageStats = false`. Più un guard difensivo in app per messaggio
  d'errore esplicito al posto del precedente OOM silenzioso. (`#7`)
- `scripts/release-checks.sh` + `.github/workflows/release-checks.yml`:
  CI che fallisce il build su placeholder email residui, hash SHA256
  placeholder, o entry CHANGELOG mancante per il tag corrente. (`#5`,
  `#1`, `#10`)
- `requirements-dev.txt` con pytest, separato dal `requirements.txt` di
  runtime. (`#8`)
- Nota in `docs/SECURITY-ADVISORY-v1.1.0.md` che documenta esplicitamente
  l'asimmetria di trust macOS↔Windows nell'installer (TLS chain Homebrew
  vs hash pinning). (`#6`)

### Changed
- `windows/setup-dependencies.ps1` legge la versione mostrata all'utente
  da una sola variabile `$AppVersion`. Banner di log e dialog di
  successo non sono più disallineati con `installer.iss` e `src/app.py`. (`#9`)
- Placeholder `[inserire email]` / `[inserire email security]` sostituiti
  con `info@jacoporomani.it` in 8 file (SECURITY.md,
  README.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, mac/README-MAC.md,
  docs/FAQ.md, docs/PRIVACY-GDPR.md, docs/ARCHITECTURE.md). Il CI guard
  rifiuta il merge finché non sono sostituiti con un'email reale. (`#5`)
- `docs/ARCHITECTURE.md` sezione "Test e qualità" ora descrive la suite
  reale (`tests/`) invece di una directory che non esisteva, con i test
  storicamente proposti elencati come roadmap. (`#8`)
- `docs/RELEASE-GUIDE.md` aggiornato per il nuovo pattern placeholder e
  il guard CI. (`#5`)

### Deprecated
- Vecchio `CHANGELOG.md` (che era una procedura di rilascio v1.0.0→v1.1.0)
  spostato a `docs/RELEASE-PROCEDURE-v1.1.0.md`. Conservato per
  riferimento storico, non viene più aggiornato. (`#10`)

### Known issues
- Il guard CI fallisce il build finché:
  - L'email reale del maintainer non sostituisce
    `info@jacoporomani.it` (`#5`)
  - Gli SHA256 reali di Tesseract e Tessdata non sostituiscono
    `AGGIORNARE_AL_PRIMO_RILASCIO` in `windows/setup-dependencies.ps1`
    (`#1`)
- Versione unica letta da un file `VERSION` in repo root (così
  `installer.iss`, `setup-dependencies.ps1` e `src/app.py` condividono una
  sola fonte) è ancora todo — per v1.2.0.

## [1.1.1] - 2026-05-11

### Fixed
- Il metadata `producer` del PDF output è ora una stringa vuota invece di
  "Anonimizzatore PDF", che identificava il software anche dopo
  l'anonimizzazione.
- La detection di immagini inline usa `abs(page.mediabox.*)` invece di
  `page.rect.*` per gestire correttamente pagine ruotate.

### Changed
- `st.set_page_config(menu_items={})` per rimuovere i link Streamlit di
  default "Report a bug" e "About".

## [1.1.0] - 2026-04 (data esatta da `git log`)

Security hardening release. **Nota retroattiva (v1.1.2):** l'audit esterno
ha rivelato che diverse claim di questa release non erano realmente
applicate dal codice — vedi i fix `#1`, `#2`, `#3`, `#4` in v1.1.2.

### Added
- Installer Windows con (intento di) verifica SHA256 per ogni binario
  scaricato — vedi `docs/SECURITY-ADVISORY-v1.1.0.md`.
- `sanitize_pdf_objects()`: rimozione di annotazioni, AcroForm, allegati
  embedded e oggetti JavaScript a livello di documento.
- `sanitize_pdf_metadata()`: azzeramento metadata standard + rimozione
  XMP stream.
- Logger strutturato, `$ErrorActionPreference = "Stop"` nell'installer
  per fail-fast.

### Security
- TLS 1.2+ forzato in tutti i download dell'installer.
- URL ufficiali per tutti i binari di terze parti (no mirror non
  verificati).

## [1.0.0] - 2026

Initial public release.

### Added
- Streamlit UI con detection automatica di:
  - PII generiche via Microsoft Presidio + spaCy `it_core_news_lg`
  - Entità italiane custom: `IT_FISCAL_CODE`, `IT_VAT_CODE`,
    `IT_IDENTITY_CARD`, `IT_DRIVER_LICENSE`, `IT_PASSPORT`
  - Termini personalizzati definiti dall'utente
- OCR Tesseract per PDF scansionati (rilevamento automatico delle pagine
  che ne hanno bisogno).
- Redazione fisica via PyMuPDF (testo rimosso, non solo coperto).
- Supporto Windows 10/11 e macOS 12+ (Intel + Apple Silicon).
- Licenza AGPL v3 con offerta licenza commerciale alternativa.

[Unreleased]: https://github.com/jacktotem/anonimizzatore-pdf/compare/v1.1.2...HEAD
[1.1.2]: https://github.com/jacktotem/anonimizzatore-pdf/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/jacktotem/anonimizzatore-pdf/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/jacktotem/anonimizzatore-pdf/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/jacktotem/anonimizzatore-pdf/releases/tag/v1.0.0
