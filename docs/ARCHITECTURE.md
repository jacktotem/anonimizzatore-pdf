# 🏗️ Architettura del progetto

Documento tecnico per sviluppatori che vogliono contribuire o capire come funziona Anonimizzatore PDF.

---

## 📦 Struttura del repository

```
anonimizzatore-pdf/
├── README.md                   # Documentazione principale
├── LICENSE                     # GNU AGPL v3.0
├── NOTICE                      # Attribuzioni open source
├── CONTRIBUTING.md             # Linee guida contributori
├── CODE_OF_CONDUCT.md          # Codice di condotta
├── SECURITY.md                 # Security disclosure policy
├── CHANGELOG.md                # Storia versioni
├── requirements.txt            # Dipendenze Python
├── .gitignore
│
├── src/                        # ✨ Codice sorgente
│   └── app.py                  # App Streamlit principale (~600 LOC)
│
├── windows/                    # 🪟 Tutto per Windows
│   ├── installer.iss           # Script Inno Setup
│   ├── setup-dependencies.ps1  # Setup automatico
│   ├── AnonimizzatorePDF.bat   # Launcher
│   ├── README-UTENTE.txt       # Guida utente
│   ├── COMPILA-INSTALLER.md    # Come compilare
│   └── app/                    # Cartella inclusa nell'installer
│       └── app.py              # Copia di src/app.py
│
├── mac/                        # 🍎 Tutto per Mac
│   ├── installa.sh             # Setup automatico
│   ├── avvia.sh                # Avvio rapido
│   ├── app.py                  # Copia di src/app.py
│   ├── icon-1024.png           # Sorgente icona .icns
│   └── README-MAC.md           # Guida utente Mac
│
├── docs/                       # 📚 Documentazione estesa
│   ├── ARCHITECTURE.md         # Questo file
│   ├── FAQ.md
│   ├── PRIVACY-GDPR.md
│   ├── RELEASE-GUIDE.md
│   └── images/
│
└── .github/                    # 🐙 Template GitHub
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.md
    │   ├── feature_request.md
    │   ├── commercial.md
    │   └── config.yml
    ├── PULL_REQUEST_TEMPLATE.md
    └── FUNDING.yml
```

---

## 🔁 Flusso di elaborazione

### 1. Upload del PDF

```
Utente carica PDF
       ↓
Streamlit st.file_uploader()
       ↓
File salvato in /tmp (variabile in memoria)
```

### 2. Analisi del PDF

```
PyMuPDF (fitz) apre il file
       ↓
Per ogni pagina:
  ├─ Estrai testo (page.get_text())
  ├─ Se testo < 50 caratteri → pagina scansionata
  └─ Altrimenti → pagina testuale
```

### 3. OCR (se necessario)

```
Per ogni pagina scansionata:
  ├─ Renderizza pagina a DPI scelto (default 200)
  ├─ Tesseract analizza l'immagine
  ├─ Ottiene parole + bounding box + confidence
  └─ Filtra parole con confidence < 30
```

### 4. Riconoscimento entità

```
Presidio AnalyzerEngine
  ├─ Recognizer Italiani (regex custom):
  │   ├─ Codice fiscale: ^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$
  │   ├─ Partita IVA: ^\d{11}$
  │   ├─ Carta identità: ^[A-Z]{2}\d{7}$
  │   ├─ Patente: ^[A-Z0-9]{8,10}$
  │   └─ Passaporto: ^[A-Z]{2}\d{7}$
  │
  ├─ Recognizer globali Presidio:
  │   ├─ PERSON (spaCy NER)
  │   ├─ EMAIL_ADDRESS
  │   ├─ PHONE_NUMBER
  │   ├─ LOCATION
  │   ├─ IBAN_CODE
  │   ├─ CREDIT_CARD
  │   └─ ...
  │
  ├─ Termini specifici (custom recognizer):
  │   └─ Match esatto su ogni stringa fornita dall'utente
  │
  └─ Risultato: lista di RecognizerResult con:
      - entity_type
      - start, end (offset nel testo)
      - score (confidence)
```

### 5. Redazione

```
Per ogni entità rilevata:
  ├─ Trova la posizione fisica nel PDF (search_for)
  ├─ Aggiungi redact_annotation()
  └─ apply_redactions(): rimuove fisicamente il testo

Per pagine OCR:
  ├─ Calcola bounding box delle entità sulla pagina
  ├─ Disegna rettangoli neri sull'immagine
  ├─ Sostituisci la pagina con l'immagine modificata
  └─ Risultato: la pagina è ora solo un'immagine (non testo)
```

### 6. Output

```
PDF risultante salvato come bytes in memoria
       ↓
Streamlit st.download_button()
       ↓
Utente scarica
```

---

## 🧩 Componenti principali del codice

### `app.py` — Struttura

```python
# 1. Import e configurazione
import streamlit as st
import fitz  # PyMuPDF
from presidio_analyzer import AnalyzerEngine, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
# ...

# 2. Recognizer italiani (regex)
italian_recognizers = [
    PatternRecognizer(supported_entity="IT_FISCAL_CODE", ...),
    PatternRecognizer(supported_entity="IT_VAT_CODE", ...),
    # ...
]

# 3. Setup engine NLP italiano
@st.cache_resource
def get_analyzer():
    configuration = {"nlp_engine_name": "spacy", "models": [{"lang_code": "it", "model_name": "it_core_news_lg"}]}
    nlp_engine = NlpEngineProvider(nlp_configuration=configuration).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["it"])
    for r in italian_recognizers:
        analyzer.registry.add_recognizer(r)
    return analyzer

# 4. UI Streamlit
def main():
    st.title("🔒 Anonimizzatore PDF")
    
    # Sidebar: configurazione entità
    # Area centrale: upload PDF
    # Area destra: termini specifici
    
    if pdf_uploaded:
        # Esegui pipeline
        result_pdf = process_pdf(pdf, entities, custom_terms, ocr_mode)
        st.download_button("Scarica", result_pdf)
```

### Funzioni chiave

| Funzione | Responsabilità |
|----------|---------------|
| `get_analyzer()` | Carica e cachea Presidio + spaCy |
| `extract_text_from_page(page)` | Estrae testo da una pagina (testuale) |
| `ocr_page(page, dpi)` | Esegue OCR su una pagina (immagine) |
| `analyze_text(text, entities)` | Restituisce le entità rilevate |
| `redact_page_text(page, entities)` | Redazione su pagina testuale |
| `redact_page_image(page, entities, ocr_data)` | Redazione su pagina OCR |
| `process_pdf(...)` | Orchestratore principale |

---

## 🎨 UI e UX

### Layout Streamlit

```
┌─────────────────────────────────────────────┐
│              HEADER (titolo)                │
├──────────┬──────────────────┬───────────────┤
│ SIDEBAR  │                  │  PANNELLO     │
│          │   AREA CENTRALE  │  DESTRO       │
│ Entità   │   - File upload  │  - Termini    │
│ da rile- │   - Status       │    specifici  │
│ vare     │   - Bottone      │  - Modalità   │
│          │     Anonimizza   │    OCR        │
│ Globali  │   - Download     │  - Soglia     │
│ Italiane │     button       │    confidence │
│          │   - Report       │               │
├──────────┴──────────────────┴───────────────┤
│              FOOTER (diagnostic)            │
└─────────────────────────────────────────────┘
```

### Stati dell'app

1. **Idle** — nessun file caricato
2. **Loaded** — file caricato, mostra preview e configurazione
3. **Processing** — elaborazione in corso, spinner attivo
4. **Done** — risultato disponibile, download attivo
5. **Error** — qualcosa è andato storto, log visibili

---

## 🧪 Testing

> Una suite minima di regression test è stata aggiunta in v1.1.2 in
> risposta alla issue N-04 (#8). Storicamente la directory `tests/` era
> descritta in questo documento ma non esisteva; uno smoke test minimo
> avrebbe intercettato la issue #2 (`doc.get_js()` AttributeError) prima
> di v1.0.0.

### Struttura attuale (v1.1.2+)

```
tests/
├── conftest.py                        # fixture pytest condivise, autouse fixtures dir
├── build_fixtures.py                  # genera i PDF di prova riproducibilmente
├── test_sanitize_javascript.py        # regression guard per #2 e #3
├── test_sanitize_attachments.py       # regression guard per #4
├── test_sanitize_metadata.py          # verifica claim azzeramento metadata
└── fixtures/                          # generate al primo run di pytest
    ├── plain.pdf
    ├── with_js_and_openaction.pdf
    └── with_duplicate_attachments.pdf
```

### Come eseguirli

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Le fixture sono generate dal primo run via `build_fixtures.py` (autouse
fixture in `conftest.py`), quindi non sono committate come binari opachi.

### Aree ancora da coprire (roadmap)

I test attuali coprono solo il livello di sanitizzazione PDF (l'area in cui
si concentravano i bug dell'audit). Manca tuttora una suite per:

**Test unitari sui riconoscitori Presidio:**

```python
# Esempio futuro: tests/test_recognizers.py
def test_fiscal_code_recognition():
    cf = "RSSMRA80A01H501Z"
    results = analyzer.analyze(cf, language="it")
    assert any(r.entity_type == "IT_FISCAL_CODE" for r in results)
```

**Test end-to-end sulla pipeline di redazione:**

```python
# Esempio futuro: tests/test_pipeline.py
def test_full_pdf_anonymization():
    input_pdf = open("tests/fixtures/sample_legal.pdf", "rb").read()
    output_pdf = process_pdf(input_pdf, entities=["PERSON", "IT_FISCAL_CODE"])
    # Verifica che "Mario Rossi" e "RSSMRA80A01H501Z" siano stati oscurati.
```

**Test di regressione su PDF reali** (anonimizzati prima del commit) con
expected output:

```
tests/fixtures/
├── sample_legal_textual.pdf
├── sample_legal_scanned.pdf
├── sample_with_iban.pdf
└── expected_outputs/
    └── sample_legal_textual_redacted.pdf
```

Contributi benvenuti — vedi `CONTRIBUTING.md`.

---

## 🚀 Performance

### Bottleneck principali

1. **Caricamento modello spaCy** (~5-10s al primo avvio)
   - Mitigato con `@st.cache_resource`
2. **OCR di pagine scansionate** (~3-10s per pagina)
   - Mitigato dalla detection automatica (solo se necessario)
3. **Rendering finale del PDF** (~1-2s)
   - Trascurabile

### Ottimizzazioni possibili

- ⚡ Multithreading per OCR di pagine multiple
- ⚡ Cache dei risultati di analisi entità
- ⚡ Modello spaCy più piccolo per uso "veloce" (`it_core_news_sm`)
- ⚡ Pre-caricamento in background

---

## 🔮 Roadmap tecnica

### v1.x
- ✅ Anonimizzazione PDF italiani
- ✅ OCR integrato
- ✅ Installer Windows + Mac

### v2.x (idee)
- 🌐 Internazionalizzazione (i18n) → supporto multilingua
- 🔄 Batch processing → elaborare più PDF contemporaneamente
- 🎨 UI migliorata (custom CSS Streamlit o frontend dedicato)
- 📊 Dashboard delle redazioni effettuate
- 🧪 Suite di test automatizzati

### v3.x (Enterprise)
- 👥 Multi-utente con autenticazione
- 📝 Audit log persistente (DB)
- 🔌 API REST
- 🐳 Docker / Kubernetes
- 🔐 SSO (SAML, OAuth)

---

## 📞 Contatti tecnici

- **GitHub Issues** per discussioni pubbliche
- **GitHub Discussions** per Q&A
- **Email**: REPLACE-BEFORE-MERGE@example.invalid per privato

Buon coding! 🚀
