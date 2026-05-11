# 📋 Changelog

Tutti i cambiamenti rilevanti di questo progetto sono documentati in questo file.

Il formato segue [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), e questo progetto aderisce al [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### In sviluppo
- Internazionalizzazione (i18n) per supporto multilingua
- Suite di test automatizzati
- Versione Enterprise con login multi-utente

---

## [1.0.0] - 2026-05-11

### 🎉 Prima release pubblica

#### Aggiunto
- Anonimizzazione automatica di PDF italiani
- Riconoscimento di entità globali (nomi, email, telefoni, indirizzi)
- Riconoscimento di entità italiane (CF, P.IVA, CI, patente, passaporto)
- Riconoscimento di IBAN e carte di credito
- Campo "termini specifici" per oscurare nomi/società custom
- OCR integrato con Tesseract per PDF scansionati
- Modalità OCR: Automatica / Forza tutto / Mai
- Report dettagliato delle redazioni applicate
- Pannello diagnostico integrato
- Installer Windows .exe basato su Inno Setup
- Script di installazione macOS (Intel + Apple Silicon)
- Documentazione utente in italiano

#### Tecnico
- Stack: Python 3.12 + Streamlit + Presidio + spaCy + PyMuPDF + Tesseract
- Modello linguistico: `it_core_news_lg`
- Redazione fisica del testo (non solo copertura visiva)
- Pagine OCR ricostruite come immagini per massima sicurezza
- Architettura 100% locale, GDPR-compliant by design

---

## Tipologie di cambiamento

- **Aggiunto** — per nuove funzionalità
- **Modificato** — per cambiamenti in funzionalità esistenti
- **Deprecato** — per funzionalità che saranno presto rimosse
- **Rimosso** — per funzionalità rimosse in questa release
- **Risolto** — per bug fix
- **Sicurezza** — in caso di vulnerabilità

[Unreleased]: https://github.com/[username]/anonimizzatore-pdf/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/[username]/anonimizzatore-pdf/releases/tag/v1.0.0
