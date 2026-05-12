# 🍎 Anonimizzatore PDF — Versione Mac

Strumento di anonimizzazione automatica di documenti PDF in italiano, basato su Microsoft Presidio + Tesseract OCR. Funziona completamente in locale.

Compatibile con **Mac Intel** e **Mac Apple Silicon** (M1/M2/M3/M4).

---

## 📋 Requisiti

- macOS 12 (Monterey) o superiore
- ~3 GB di spazio libero su disco
- Connessione internet (solo per l'installazione iniziale)
- Privilegi amministratore del Mac

---

## 🚀 Installazione (una sola volta, ~15 minuti)

### Passo 1 — Scarica e estrai

1. Scarica il repository:
   ```bash
   git clone https://github.com/[username]/anonimizzatore-pdf.git
   ```
   Oppure scarica lo zip dalla pagina GitHub e estrailo.

2. Entra nella cartella:
   ```bash
   cd anonimizzatore-pdf/mac
   ```

### Passo 2 — Lancia l'installazione

Nel Terminale digita:

```bash
chmod +x installa.sh
./installa.sh
```

### Passo 3 — Segui l'installazione

Lo script ti chiederà:

- **All'inizio**: premi Invio per confermare
- **Password Mac**: quando lo richiede (per Homebrew). Digita la tua password (non vedrai i caratteri mentre digiti). Premi Invio.
- **Xcode Command Line Tools**: se si apre una finestra di sistema, clicca "Installa"
- **Alla fine**: ti chiede se vuoi aprire l'app subito → premi `s`

Tempo totale: 10-20 minuti.

### Cosa viene installato

- **Homebrew** (gestore pacchetti per Mac)
- **Python 3.12**
- **Tesseract OCR** con supporto italiano
- **Librerie Python** (Streamlit, Presidio, spaCy, ecc.)
- **Modello linguistico italiano** (~580 MB)

---

## ▶️ Uso quotidiano

Dopo l'installazione trovi sul **Desktop** un'icona blu con un lucchetto:

📱 **Anonimizzatore PDF**

**Doppio click** → si apre il Terminale (è normale) e dopo qualche secondo si apre il browser con l'app.

**Per chiudere**: chiudi la finestra del Terminale.

---

## 📝 Come usare l'app

1. **Carica il PDF** dal pulsante centrale
2. **Sidebar sinistra**: lascia i flag predefiniti
3. **Termini specifici**: inserisci nomi, ragioni sociali, indirizzi specifici
4. **Modalità OCR**: lascia su "Automatica"
5. Clicca **🔒 Anonimizza documento**
6. Scarica il PDF risultante

⚠️ **VERIFICA SEMPRE** il PDF finale prima di inviarlo.

---

## 🔧 Aggiornamenti

```bash
cd anonimizzatore-pdf
git pull
```

Oppure scarica solo il nuovo `app.py` da GitHub e sostituiscilo nella cartella `mac/`.

Nessuna reinstallazione necessaria.

---

## ❌ Disinstallazione

1. Trascina l'icona "Anonimizzatore PDF" dal Desktop nel Cestino
2. Elimina la cartella `anonimizzatore-pdf`

Per disinstallare anche Tesseract e Python:
```bash
brew uninstall tesseract tesseract-lang
brew uninstall python@3.12
```

---

## 🆘 Problemi comuni

### "Non posso aprire l'app perché viene da uno sviluppatore non identificato"

Tasto destro sull'icona → "Apri" → conferma. Necessario solo la prima volta.

### "Ambiente virtuale non trovato"

Hai spostato la cartella `mac/` dopo l'installazione. Rilancia `installa.sh` dalla nuova posizione.

### "Tesseract non trova l'italiano"

```bash
brew install tesseract-lang
```

### Log dettagliati

I log dell'installazione sono in:
```
mac/logs/install-YYYYMMDD-HHMMSS.log
```

---

## 🔒 Privacy

- **Niente cloud**: i documenti restano sempre sul Mac
- **Niente telemetria**: l'app non invia dati a nessuno
- **Redazione vera**: il testo viene fisicamente rimosso dal PDF

---

## 📞 Supporto

- **Issues GitHub**: per problemi tecnici pubblici
- **Email commerciale**: REPLACE-BEFORE-MERGE@example.invalid per supporto a pagamento
