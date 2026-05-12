# 🤝 Contribuire ad Anonimizzatore PDF

Grazie per il tuo interesse! Ogni contributo è benvenuto: bug report, suggerimenti, pull request, documentazione, traduzioni.

---

## 🐛 Segnalare un bug

1. Controlla prima nelle [Issue esistenti](../../issues) che non sia già stato segnalato
2. Apri una nuova issue usando il template "Bug report"
3. Includi:
   - **Sistema operativo** e versione (Windows 11, macOS 14, ecc.)
   - **Passi per riprodurre** il bug
   - **Comportamento atteso** vs **comportamento osservato**
   - **Screenshot** o log se disponibili
   - **PDF di esempio** (anonimizzato, senza dati reali!) se rilevante

---

## 💡 Proporre una funzionalità

1. Apri una issue usando il template "Feature request"
2. Spiega:
   - **Problema** che la feature risolverebbe
   - **Soluzione proposta**
   - **Alternative** considerate
   - **Casi d'uso** concreti

Le feature più richieste hanno priorità.

---

## 🔧 Setup di sviluppo

### Requisiti

- Python 3.12
- Tesseract OCR con lingua italiana
- Git

### Setup locale

```bash
# Clona il repository
git clone https://github.com/[username]/anonimizzatore-pdf.git
cd anonimizzatore-pdf

# Ambiente virtuale
python3.12 -m venv venv
source venv/bin/activate  # su Windows: venv\Scripts\activate

# Dipendenze
pip install -r requirements.txt
pip install -r requirements-dev.txt  # se presente
python -m spacy download it_core_news_lg

# Avvia in modalità sviluppo
streamlit run src/app.py
```

### Struttura del progetto

```
anonimizzatore-pdf/
├── src/                    # Codice sorgente Python
│   └── app.py             # App Streamlit principale
├── windows/                # Script e installer per Windows
├── mac/                    # Script di installazione per macOS
├── docs/                   # Documentazione estesa
├── .github/                # Templates GitHub e workflow
├── README.md
├── LICENSE                 # AGPL v3
├── NOTICE                  # Attribuzioni open source
├── CONTRIBUTING.md         # Questo file
├── CHANGELOG.md            # Storia dei rilasci
└── requirements.txt        # Dipendenze Python
```

---

## 📝 Linee guida per le pull request

### Prima di iniziare

1. **Apri una issue** per discutere la modifica prima di lavorarci, soprattutto per cambiamenti grossi
2. **Fork** del repository
3. Crea un **branch dedicato**: `git checkout -b feat/nome-feature` o `fix/nome-bug`

### Convenzioni di codice

- **Stile Python**: PEP 8 (usa `ruff` o `black` se preferisci)
- **Commenti**: in italiano (per coerenza con il dominio) o inglese — basta che siano chiari
- **Funzioni piccole**: una funzione, una responsabilità
- **Type hints** sono benvenuti

### Convenzioni dei commit

Usa il formato [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: aggiunge supporto per documenti DOC oltre a PDF
fix: corregge falso positivo su date in formato italiano
docs: aggiorna README con istruzioni Linux
refactor: semplifica funzione di estrazione testo
test: aggiunge test per regex codice fiscale
chore: aggiorna versione spaCy a 3.7.5
```

### Apertura della PR

1. Fai push del branch sul tuo fork
2. Apri una Pull Request verso il branch `main` del repository principale
3. Descrivi:
   - **Cosa** cambia
   - **Perché** cambia (linka l'issue se esiste)
   - **Come testare** il cambiamento
4. Aspetta la review

### Code review

- Le PR vengono revisionate il prima possibile (di solito entro 1 settimana)
- Possono essere richieste modifiche — non prenderlo sul personale, è normale
- Una volta approvata, la PR viene mergiata in `main`

---

## 🧪 Test

Al momento il progetto non ha una suite di test automatizzata completa. Contributi in questa direzione sono **molto graditi**:

- Test unitari per le funzioni di riconoscimento entità
- Test di integrazione su PDF reali (anonimizzati)
- Benchmark di precisione/recall

---

## 🌐 Traduzioni

L'app è in italiano. Per tradurla in altre lingue:

1. Apri una issue specificando la lingua
2. Le stringhe sono in `src/app.py` — al momento sparse, non c'è un sistema i18n
3. Una PR potrebbe iniziare con l'estrazione delle stringhe in un file separato

---

## ⚖️ Licenza dei contributi

Inviando una pull request, accetti che il tuo contributo sia distribuito sotto la stessa licenza del progetto: **GNU AGPL v3.0**.

Mantieni il copyright dei tuoi contributi, ma concedi una licenza perpetua, irrevocabile, mondiale, gratuita.

---

## 🙋 Domande?

- **Issue su GitHub** per domande tecniche pubbliche
- **Email**: REPLACE-BEFORE-MERGE@example.invalid per questioni private o commerciali
- **Discussioni**: usa la sezione [Discussions](../../discussions) per chiacchierare

---

## 🌟 Codice di condotta

Sii rispettoso. Critica le idee, non le persone. Aiuta i nuovi arrivati. Vedi [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) per i dettagli.

---

**Grazie per contribuire! 🙏**
