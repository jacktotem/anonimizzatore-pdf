# 🚀 Come applicare la v1.1.0 su GitHub

Questa guida ti spiega esattamente cosa fare per portare la repository da v1.0.0 a v1.1.0.

**Tempo stimato:** 15 minuti.

---

## 📁 File nello zip

```
fix-v1.1/
├── app.py                              ← VA IN: src/app.py
├── setup-dependencies.ps1              ← VA IN: windows/setup-dependencies.ps1
├── installer.iss                       ← VA IN: windows/installer.iss
├── requirements.txt                    ← VA IN: requirements.txt (root)
├── CHANGELOG.md                        ← VA IN: CHANGELOG.md (root)
├── sync-app.sh                         ← VA IN: scripts/sync-app.sh (cartella nuova)
└── SECURITY-ADVISORY-v1.1.0.md         ← VA IN: docs/SECURITY-ADVISORY-v1.1.0.md
```

---

## 📝 Procedura (su GitHub dal browser)

### 1. Aggiorna `src/app.py`

1. Vai sul tuo repository GitHub
2. Apri `src/app.py`
3. In alto a destra clicca l'icona **matita** (✏️) per modificare
4. **Cancella tutto il contenuto** (Cmd+A → Delete)
5. Apri il file `app.py` dello zip con un editor di testo (TextEdit, VS Code, ecc.)
6. Copia tutto il contenuto e incollalo nella pagina GitHub
7. In fondo, **Commit message**: `fix(security): v1.1.0 - sanitize metadata, annotations, attachments`
8. Clicca **Commit changes**

### 2. Aggiorna `windows/setup-dependencies.ps1`

Stessa procedura del punto 1, ma per `windows/setup-dependencies.ps1`.
Commit message: `fix(security): hash pinning + URL ufficiali per binari installer`

### 3. Aggiorna `windows/installer.iss`

Stessa procedura, per `windows/installer.iss`.
Commit message: `chore: bump versione installer a 1.1.0`

### 4. Aggiorna `requirements.txt`

Stessa procedura, per `requirements.txt` (root).
Commit message: `fix(security): pin minimum secure versions (Pillow, streamlit)`

### 5. Aggiorna `CHANGELOG.md`

Stessa procedura, per `CHANGELOG.md` (root).
Commit message: `docs: changelog v1.1.0`

### 6. Aggiorna le copie di `app.py` (windows e mac)

⚠️ **Importante**: devi anche aggiornare `windows/app/app.py` e `mac/app.py`
con lo stesso contenuto di `src/app.py`.

Procedura identica al punto 1, ma per:
- `windows/app/app.py`
- `mac/app.py`

Commit message: `chore: sync app.py copies (windows + mac)`

### 7. Crea nuovi file

**`scripts/sync-app.sh`** — file nuovo:

1. Sulla home del repo, clicca **"Add file" → "Create new file"**
2. Nel nome del file scrivi: `scripts/sync-app.sh`
   (lo slash crea automaticamente la cartella `scripts/`)
3. Incolla il contenuto di `sync-app.sh` dallo zip
4. Commit message: `feat: add sync-app.sh script per evitare drift`
5. **Commit changes**

**`docs/SECURITY-ADVISORY-v1.1.0.md`** — file nuovo:

1. Vai dentro la cartella `docs/`
2. **"Add file" → "Create new file"**
3. Nome: `SECURITY-ADVISORY-v1.1.0.md`
4. Incolla il contenuto del file dallo zip
5. Commit message: `docs: security advisory v1.1.0`

---

## 🏷️ Creare la nuova Release v1.1.0

Dopo che tutti i file sono aggiornati:

### Sul tuo PC Windows

1. **Scarica il repository aggiornato:**
   - Vai sulla pagina del repository GitHub
   - **Code → Download ZIP** (o `git pull` se l'hai clonato)

2. **Apri `windows/installer.iss`** con Inno Setup

3. **Verifica che `windows/app/app.py` sia stato aggiornato!**

4. Premi **F9** per compilare

5. Si crea **`AnonimizzatorePDF-Setup-v1.1.0.exe`**

### Su GitHub

1. Vai su **Releases → Draft a new release**

2. **Choose a tag**: scrivi `v1.1.0` → "Create new tag: v1.1.0 on publish"

3. **Release title**: `v1.1.0 — Security Update`

4. **Description** (copia questo testo):

```markdown
# 🛡️ Release di sicurezza

Risolve **1 HIGH**, **4 MEDIUM** e **3 LOW** identificati in v1.0.0.

**Aggiornamento fortemente consigliato per tutti gli utenti.**

## Fix principali

- 🔴 **HIGH**: l'installer Windows ora verifica SHA256 di tutti i binari scaricati; URL Tesseract spostato dal mirror universitario al repo ufficiale GitHub
- 🟠 **MEDIUM**: i metadata del PDF (autore/titolo/XMP) vengono sanitizzati automaticamente
- 🟠 **MEDIUM**: annotazioni, allegati embedded, form fields e JavaScript rimossi dall'output
- 🟠 **MEDIUM**: warning UI per immagini inline non OCRate (firme, foto di ID in pagine testuali)
- 🟠 **MEDIUM**: versioni minime di sicurezza per Pillow (CVE-2023-50447) e streamlit (CVE-2024-42474)
- 🟡 **LOW**: ordine path Tesseract corretto contro path hijacking
- 🟡 **LOW**: messaggi di errore UI sanitizzati per evitare leak di frammenti PDF

Dettagli completi: [SECURITY-ADVISORY-v1.1.0.md](docs/SECURITY-ADVISORY-v1.1.0.md)

## Come aggiornare

### Windows
1. Disinstalla v1.0.0 dal Pannello di Controllo
2. Scarica `AnonimizzatorePDF-Setup-v1.1.0.exe` qui sotto e lancialo

### Mac
```bash
cd anonimizzatore-pdf
git pull
cd mac
./installa.sh
```

## Ringraziamenti

Grazie allo sviluppatore esterno (anonimo su richiesta) per l'analisi di sicurezza approfondita.
```

5. **Allega**: trascina `AnonimizzatorePDF-Setup-v1.1.0.exe` nell'area "Attach binaries"

6. ✅ Spunta **"Set as the latest release"**

7. Clicca **Publish release**

---

## 🎯 Bonus: convertire la v1.0.0 in pre-release

Per evitare che nuovi utenti scarichino la versione vulnerabile:

1. Vai su Releases → v1.0.0 → **Edit** (matita)
2. Spunta **"Set as a pre-release"**
3. Update release

Così v1.1.0 diventa l'unica "latest" e v1.0.0 appare con un badge "Pre-release".

---

## ✅ Checklist finale

- [ ] `src/app.py` aggiornato
- [ ] `windows/app/app.py` aggiornato
- [ ] `mac/app.py` aggiornato
- [ ] `windows/setup-dependencies.ps1` aggiornato
- [ ] `windows/installer.iss` aggiornato
- [ ] `requirements.txt` aggiornato
- [ ] `CHANGELOG.md` aggiornato
- [ ] `scripts/sync-app.sh` creato
- [ ] `docs/SECURITY-ADVISORY-v1.1.0.md` creato
- [ ] Compilato nuovo installer su Windows
- [ ] Release v1.1.0 pubblicata con .exe allegato
- [ ] v1.0.0 marcata come pre-release

---

## 📞 Dubbi?

Se qualcosa non funziona o hai domande sul fix, chiedimi!

