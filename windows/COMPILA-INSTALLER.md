# 🛠️ Come creare l'installer .exe — Guida rapida

Questa guida ti spiega come trasformare i file di questa cartella in un singolo file `AnonimizzatorePDF-Setup.exe` pronto da distribuire.

---

## ⏱️ Tempo richiesto: 10 minuti (solo la prima volta)

---

## 1️⃣ Installa Inno Setup (gratuito)

1. Vai su https://jrsoftware.org/isdl.php
2. Scarica **innosetup-6.x.x.exe** (versione "Stable")
3. Installa normalmente (next, next, finish)

---

## 2️⃣ Prepara la cartella

Nella cartella `windows/` devi avere questa struttura:

```
windows/
├── installer.iss                ← script principale
├── setup-dependencies.ps1       ← script setup
├── AnonimizzatorePDF.bat        ← launcher
├── README-UTENTE.txt            ← guida utente
├── COMPILA-INSTALLER.md         ← questo file
└── app/
    └── app.py                   ← copia di src/app.py
```

**Importante**: copia `src/app.py` dentro `windows/app/` prima di compilare!

```bash
# Su Windows (cmd):
copy ..\src\app.py app\app.py

# Su Mac/Linux:
cp ../src/app.py app/app.py
```

---

## 3️⃣ Compila l'installer

1. **Doppio click** su `installer.iss`
   → Si apre Inno Setup Compiler
2. Premi **F9** (oppure menu **Build → Compile**)
3. Aspetta 5-10 secondi
4. Al termine vedrai: **"Successful compile"**
5. Si crea la cartella `installer/` con dentro:
   - **`AnonimizzatorePDF-Setup.exe`** ← QUESTO è il file da distribuire!

Dimensione finale: circa **5 MB**.

---

## 4️⃣ Test dell'installer

Prima di distribuirlo, testalo su un PC pulito (o virtual machine):

1. Copia `AnonimizzatorePDF-Setup.exe` sul PC di test
2. Doppio click → ti chiede privilegi admin → OK
3. Compare wizard: "Avanti → Avanti → Installa"
4. Durante l'installazione mostra una progress bar
5. Lo script PowerShell:
   - Scarica Python 3.12 se non presente
   - Scarica Tesseract OCR (con italiano)
   - Crea ambiente virtuale
   - Installa tutti i pacchetti Python
   - Scarica il modello linguistico italiano
6. Al termine: icona sul Desktop + scorciatoia nel Menu Start
7. Doppio click sull'icona → app pronta!

**Tempo totale prima installazione:** 10-15 minuti (dipende dalla connessione)

---

## 5️⃣ Distribuzione

Il file `AnonimizzatorePDF-Setup.exe` può essere:

- **Caricato come release** su GitHub (`Releases` → `Create a new release`)
- **Inviato per email** (5 MB, entra ovunque)
- **Caricato su Google Drive / OneDrive**
- **Pubblicato su un sito** (es. landing page commerciale)

---

## 🔄 Aggiornamenti futuri

1. Modifica `src/app.py`
2. Ricopia in `windows/app/app.py`
3. Incrementa la versione in `installer.iss` (riga `#define MyAppVersion "1.0.0"` → `"1.1.0"`)
4. Aggiorna `CHANGELOG.md`
5. Ricompila con F9
6. Distribuisci il nuovo `.exe` o pubblica una nuova release su GitHub

---

## ⚠️ Note importanti

- **Privilegi admin richiesti**: l'installer chiede i privilegi di amministratore. Normale.
- **Antivirus**: alcuni antivirus possono segnalare un installer non firmato. Per uso interno non è un problema. Per distribuzioni esterne andrebbe acquistato un certificato di firma codice (~€100/anno).
- **Connessione internet**: necessaria durante la prima installazione.
- **Windows supportati**: Windows 10 e Windows 11, 64-bit.

---

## 🆘 Troubleshooting

**"Cannot create output directory"**
→ Lancia Inno Setup come amministratore, o cambia `OutputDir` in `installer.iss`

**"File not found: app\app.py"**
→ Hai dimenticato di copiare `src/app.py` in `windows/app/app.py`

**Errori durante l'esecuzione su PC di test**
→ Controlla i log in `C:\Program Files\AnonimizzatorePDF\logs\install-*.log`
