# 🚀 Guida al rilascio (per maintainer)

Questa guida è per **te** (Jacopo), per gestire le release del progetto su GitHub.

---

## 📋 Prima della prima release

### 1. Aggiorna i placeholder

Cerca e sostituisci nel repository:
- `[username]` → il tuo username GitHub effettivo
- `info@jacoporomani.it` → la tua email reale (commerciale + security)
- `[inserire sito]` → l'URL della landing page (quando ce l'avrai)
- `[inserire LinkedIn]` → il tuo profilo LinkedIn

> ⚠️ Il check `scripts/release-checks.sh` (eseguito in CI) fallisce il build
> se trova ancora `info@jacoporomani.it` in qualsiasi file
> tracciato. Vedi issue N-01 (#5).

Comando rapido (su Mac/Linux):
```bash
grep -rl "\[username\]" . | xargs sed -i '' 's/\[username\]/jacopo-romani/g'
grep -rl "info@jacoporomani.it" . | \
    xargs sed -i '' 's/info@jacoporomani.it/tua@email.it/g'
```

### 2. Scarica il testo completo della licenza AGPL v3

```bash
curl -O https://www.gnu.org/licenses/agpl-3.0.txt
mv agpl-3.0.txt LICENSE
```

Poi aggiungi in cima al file le righe di copyright che trovi nel `LICENSE` attuale.

### 3. Verifica i file

```bash
# Controlla che siano tutti presenti
ls -la
# Devi avere: README.md, LICENSE, NOTICE, CONTRIBUTING.md, CHANGELOG.md, .gitignore
```

---

## 📤 Pubblicare la repository

### Opzione A — Dall'interfaccia web GitHub (più semplice)

1. Vai su https://github.com/new
2. Compila:
   - **Repository name**: `anonimizzatore-pdf`
   - **Description**: "Anonimizzazione automatica e GDPR-compliant di documenti PDF per studi legali italiani"
   - **Public** ✅
   - **NON** spuntare "Initialize with README" (ce l'hai già)
3. Clicca **Create repository**
4. GitHub ti dà i comandi da lanciare nel terminale — segui quelli

### Opzione B — Da terminale (più professionale)

```bash
cd anonimizzatore-pdf

# Inizializza git
git init
git branch -M main

# Aggiungi tutti i file
git add .
git commit -m "Initial release v1.0.0"

# Collega al repo remoto
git remote add origin https://github.com/[username]/anonimizzatore-pdf.git

# Push
git push -u origin main
```

---

## 🏷️ Creare una release

Le **release** di GitHub sono il modo "ufficiale" per distribuire i file compilati (es. `.exe`).

### 1. Compila l'installer Windows

Sul tuo PC Windows:
1. Apri `windows/installer.iss` con Inno Setup
2. Premi F9
3. Si crea `windows/installer/AnonimizzatorePDF-Setup.exe`

### 2. Crea il tag della versione

```bash
git tag -a v1.0.0 -m "Prima release pubblica"
git push origin v1.0.0
```

### 3. Crea la release su GitHub

1. Vai sulla tua repository GitHub
2. Clicca **Releases** → **Draft a new release**
3. Compila:
   - **Tag**: seleziona `v1.0.0`
   - **Title**: `v1.0.0 — Prima release pubblica`
   - **Description**: copia il contenuto della sezione [1.0.0] dal `CHANGELOG.md`
4. **Allega i file**:
   - `AnonimizzatorePDF-Setup.exe` (installer Windows)
   - Eventualmente uno zip della cartella `mac/`
5. Clicca **Publish release**

Ora chiunque può scaricare i file dalla pagina Releases del repository.

---

## 🔄 Workflow per release future

```
1. Modifica codice in src/app.py
   ↓
2. Aggiorna CHANGELOG.md (sezione [Unreleased] → [1.x.x])
   ↓
3. Aggiorna versione nei file:
   - windows/installer.iss → MyAppVersion
   - mac/installa.sh → versione nel bundle .app
   - README.md (se necessario)
   ↓
4. Commit + push
   ↓
5. git tag -a v1.x.x -m "Descrizione"
   ↓
6. Compila .exe Windows
   ↓
7. Crea release su GitHub con .exe allegato
   ↓
8. Annuncia la release (email clienti, LinkedIn, ecc.)
```

---

## 🎨 Setup avanzato (opzionale, ma utile)

### GitHub Pages (landing page gratuita)

1. Crea una cartella `docs/site/` con dentro un `index.html` semplice
2. Vai su **Settings → Pages** del tuo repository
3. Source: `Deploy from a branch`
4. Branch: `main`, folder: `/docs/site` (o `/docs`)
5. Save → dopo qualche minuto la pagina è online su `https://[username].github.io/anonimizzatore-pdf`

### Domain personalizzato

Se compri un dominio (es. `anonimizzatorepdf.it`):
1. Configura il DNS per puntare a `[username].github.io`
2. Su GitHub Pages → Custom domain → inserisci il dominio
3. Aspetta la verifica (può richiedere ore)

### Pulsanti Sponsor

Nel file `.github/FUNDING.yml`:
```yaml
github: [tuo-username]
custom: ["https://anonimizzatorepdf.it/dona"]
```

### Topics GitHub

Vai sulla pagina del repository → bottone ⚙️ accanto a "About" → aggiungi topics:
- `pdf-anonymization`
- `gdpr`
- `legal-tech`
- `italian`
- `presidio`
- `streamlit`
- `privacy`

Migliora la discoverability.

---

## 💰 Strategie commerciali

### Step 1 — Validation (mese 1-2)

- Pubblica su GitHub
- Pubblica su LinkedIn
- Contatta 5-10 studi legali per beta testing gratuito
- Raccogli feedback e testimonianze

### Step 2 — Landing page (mese 2-3)

- Sito semplice con prezzi
- Form di contatto
- 2-3 testimonianze da beta tester
- Demo video (Loom/screencast)

### Step 3 — Vendite (mese 3+)

- Email outreach a studi legali italiani
- Partecipazione a eventi/webinar del settore legale
- Articoli su Altalex, Diritto.it, ecc.
- Google Ads su keyword tipo "anonimizzazione PDF studio legale"

### Pricing iniziale suggerito

Per i primi 5 clienti, prezzo **scontato**:
- Professional: **€290** invece di €490
- Enterprise: **€59/mese** invece di €99/mese

Dopo i primi 5: prezzo pieno.

---

## 📞 Quando hai bisogno di me

Quando vuoi:
- Aggiungere nuove feature
- Risolvere bug
- Creare la landing page
- Scrivere copy commerciale
- Preparare presentazioni per i clienti
- Tradurre l'app in inglese
- Sviluppare la versione Enterprise

Chiedi pure! 🚀
