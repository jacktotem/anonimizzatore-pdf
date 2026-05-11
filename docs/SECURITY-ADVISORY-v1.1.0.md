# 🛡️ Security Advisory — v1.0.0 → v1.1.0

**Data:** 11 maggio 2026
**Versioni interessate:** 1.0.0
**Versione patched:** 1.1.0
**Stato:** Risolto

---

## Riepilogo

A seguito di una analisi di sicurezza esterna, sono stati identificati **uno
problema HIGH**, **quattro MEDIUM** e **tre LOW** nella versione 1.0.0.
Tutti sono stati risolti in v1.1.0.

Gli utenti della v1.0.0 sono invitati ad aggiornare quanto prima.

---

## Problemi risolti

### 🔴 HIGH

#### H-01 — Installer Windows scaricava binari senza verifica integrità

**File:** `windows/setup-dependencies.ps1`

**Descrizione:** lo script PowerShell, eseguito con privilegi amministratore,
scaricava Python, Tesseract e tessdata da fonti remote senza verificare hash
SHA256 né firme. Una compromissione del mirror universitario non ufficiale
(`digi.bib.uni-mannheim.de`) o di una CA avrebbe consentito Remote Code
Execution come admin sul PC dell'utente.

**Fix in v1.1.0:**
- URL Tesseract cambiato da `digi.bib.uni-mannheim.de` (mirror non ufficiale)
  a `github.com/UB-Mannheim/tesseract/releases` (fonte ufficiale firmata)
- URL `it.traineddata` pinnato a tag stabile `4.1.0` invece di branch `main`
- SHA256 obbligatorio per ogni binario tramite `Get-FileHash`
- TLS 1.2+ forzato (default Windows può usare TLS 1.0)
- `$ErrorActionPreference = "Stop"` per fail-fast invece di "Continue"
- Verifica finale post-install che tutti i moduli siano importabili

---

### 🟠 MEDIUM

#### M-01 — Metadata PDF non sanitizzati

**File:** `src/app.py`

**Descrizione:** dopo l'anonimizzazione il PDF di output conservava i metadata
del file originale (autore, titolo, oggetto, creator, XMP). Un PDF generato
da Word con autore "Mario Rossi" rimaneva tracciabile via `pdfinfo` o qualsiasi
PDF reader. **Falsificava la promessa di anonimizzazione GDPR-compliant.**

**Fix in v1.1.0:** funzione `sanitize_pdf_metadata()` chiamata prima del save
finale. Azzera title/author/subject/keywords/creator/dates e rimuove l'XMP
stream con `del_xml_metadata()`.

---

#### M-02 — Immagini inline in pagine testuali non venivano OCRate

**File:** `src/app.py`

**Descrizione:** la heuristica `is_scanned_page()` decideva l'applicazione
OCR in base alla quantità di testo (<50 caratteri = scansionata). Una pagina
testuale contenente foto di carta d'identità, firme scansionate o timbri
veniva trattata come "testuale": **le immagini con PII restavano integre.**

**Fix in v1.1.0:**
- Nuova funzione `has_inline_images()` rileva immagini significative (>5%
  dell'area pagina)
- Warning esplicito nell'UI quando rilevate immagini in modalità "auto"
- Suggerimento di passare a modalità "Forza OCR su tutto"
- Documentazione aggiornata con il caso d'uso

---

#### M-03 — Annotazioni, allegati, AcroForm e JavaScript non rimossi

**File:** `src/app.py`

**Descrizione:** `apply_redactions()` di PyMuPDF rimuove testo selezionabile
ma **non tocca**: commenti/sticky note (spesso contengono nomi), valori dei
form fields (dati inseriti dall'utente), file embedded come allegati, e
JavaScript a livello documento (potenziale exfiltration). Vettori PII residui.

**Fix in v1.1.0:** funzione `sanitize_pdf_objects()` itera su:
- `page.annots()` → rimuove tutte le annotazioni
- `page.widgets()` → svuota i valori dei form
- `doc.embfile_count()` / `embfile_del()` → rimuove allegati
- Oggetti XRef con `/JavaScript` o `/JS` → svuota le azioni

Report nell'UI mostra il count di ciò che è stato rimosso.

---

#### M-04 — Dipendenze permissive, no lockfile

**File:** `requirements.txt`

**Descrizione:** dipendenze dichiarate solo con minima permissiva (`>=10.0.0`).
- `Pillow ≥ 10.0.0` includeva versioni con CVE-2023-50447 (RCE via
  `PIL.ImageMath.eval`, fix in 10.2.0)
- `streamlit ≥ 1.30` includeva CVE-2024-42474 (path traversal Windows,
  fix in 1.37)
- Nessun lockfile/hash check per i wheel installati

Nota: in pratica `pip install` prende l'ultima versione disponibile e quindi
la fixed; tuttavia le versioni minime devono essere esplicite per garantire
che ambienti già installati o offline non eseguano versioni vulnerabili.

**Fix in v1.1.0:**
- `Pillow >= 10.2.0,<12.0.0` (CVE-2023-50447 chiusa)
- `streamlit >= 1.37.0,<2.0.0` (CVE-2024-42474 chiusa)
- Bound massime esplicite (semver protection)
- Rimossa `presidio-anonymizer` (non era usata — I-01)

---

### 🟡 LOW

#### L-01 — `try/except: pass` mascherava errori di detection Tesseract

**File:** `src/app.py:50`

**Fix in v1.1.0:** sostituito con logging strutturato (`logging` module).
La causa dell'errore viene salvata in `TESSERACT_INIT_ERROR` e mostrata
nell'UI diagnostica.

---

#### L-02 — Path Tesseract preferiva `%LOCALAPPDATA%` prima di `Program Files`

**Files:** `src/app.py:35-42`, `windows/setup-dependencies.ps1`

**Descrizione:** l'ordine di ricerca cercava prima nelle directory utente,
permettendo in teoria a un binario `tesseract.exe` malevolo in
`%LOCALAPPDATA%` di essere eseguito al posto di quello di sistema.

**Fix in v1.1.0:** ordine invertito. Prima `C:\Program Files\Tesseract-OCR\`
(modificabile solo con admin), poi le directory utente come fallback.

---

#### L-03 — Stacktrace nei messaggi UI potevano leakare frammenti di PDF

**File:** `src/app.py:137,197,261`

**Descrizione:** `st.error(f"... {e}")` mostrava il messaggio completo
dell'eccezione, che poteva contenere frammenti del testo del PDF processato.
Rischio leak via screencast/screenshot.

**Fix in v1.1.0:** funzione `safe_error_message()` mostra solo il tipo
dell'eccezione (`TypeError`, `ValueError`, ecc.) nell'UI, mentre i dettagli
completi vengono salvati nei log locali.

---

### 🔵 INFO

#### I-01 — `presidio-anonymizer` importato ma non usato

Rimosso da `requirements.txt`. La redazione è sempre stata fatta da PyMuPDF.

#### I-02 — `$ErrorActionPreference = "Continue"` mascherava fallimenti

Cambiato a `"Stop"` (fail-fast). Aggiunta verifica finale post-install che
testa l'importabilità di tutti i moduli.

#### I-03 — `app.py` duplicato in 3 cartelle

Mantenuto solo `src/app.py` come fonte di verità. Le copie in `windows/app/`
e `mac/` sono ora generate da `scripts/sync-app.sh` prima del build.

---

## Come aggiornare

### Utenti Windows

1. Disinstalla la v1.0.0 dal Pannello di Controllo
2. Scarica `AnonimizzatorePDF-Setup-v1.1.0.exe` dalle Releases
3. Esegui il nuovo installer

I documenti già anonimizzati con v1.0.0 **vanno rielaborati** con v1.1.0 se
contengono metadata sensibili o se la pagina aveva immagini di documenti
d'identità non OCRate.

### Utenti Mac

```bash
cd anonimizzatore-pdf
git pull
cd mac
./installa.sh
```

Lo script aggiornerà tutte le dipendenze e ricreerà l'app bundle.

---

## Crediti

Ringraziamenti allo sviluppatore esterno (anonimo su richiesta) per
l'analisi di sicurezza approfondita che ha portato a questa release.

Per segnalare future vulnerabilità: vedi [SECURITY.md](../SECURITY.md).
