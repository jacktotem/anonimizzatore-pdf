# ❓ Domande frequenti

## 🎯 Generali

### Cos'è Anonimizzatore PDF?

Uno strumento open source che anonimizza automaticamente documenti PDF, oscurando nomi, codici fiscali, IBAN, indirizzi e altri dati sensibili. È pensato per studi legali italiani ma può essere usato da chiunque debba anonimizzare documenti.

### Perché un altro tool di anonimizzazione?

Le alternative attuali hanno problemi:

- **Tool gratuiti online** → richiedono di caricare i documenti su cloud (problema GDPR)
- **Tool gratuiti desktop** → richiedono redazione manuale, una entità alla volta
- **Tool a pagamento (Adobe, etc.)** → costano centinaia di euro l'anno, non focalizzati su lingua italiana

Anonimizzatore PDF è **gratis** (open source), **automatico** e **GDPR-compliant by design**.

### Quanto costa?

- **Versione Community** (questo repo): **Gratis**
- **Versione Professional** (installazione assistita + supporto): **€490 una tantum**
- **Versione Enterprise** (multi-utente + server interno): **€99/mese o €990/anno**

Vedi il [README](../README.md#-versioni-disponibili) per i dettagli.

---

## 🔒 Privacy e sicurezza

### I miei documenti vengono inviati a server esterni?

**No, mai.** L'elaborazione è 100% locale. Vedi [PRIVACY-GDPR.md](PRIVACY-GDPR.md).

### È GDPR-compliant?

Sì, by design. Niente cloud, niente API esterne, niente telemetria.

### Il testo oscurato può essere recuperato?

**No.** Il testo viene fisicamente rimosso dal PDF, non solo coperto. Le pagine OCR vengono ricostruite come immagini pure, non recuperabili con copy-paste.

### Posso usarlo offline?

Sì, dopo la prima installazione (che richiede internet per scaricare le dipendenze).

---

## ⚙️ Installazione

### Quali sistemi operativi sono supportati?

- ✅ Windows 10 e 11 (64-bit)
- ✅ macOS 12 Monterey e successivi (Intel e Apple Silicon)
- ✅ Linux (Ubuntu 22.04+ testato, altre distribuzioni dovrebbero funzionare)

### Quanto spazio occupa?

Circa **3 GB**, principalmente per:
- Modello linguistico italiano spaCy (~580 MB)
- Python e librerie (~1.5 GB)
- Tesseract OCR (~500 MB)

### L'installazione richiede privilegi admin?

Sì, su Windows e Mac, perché installa Python e Tesseract a livello di sistema.

### Posso installarlo senza internet?

No, almeno la prima volta. Servono ~2 GB di download. Dopo, l'app funziona offline.

---

## 🖱️ Uso

### Quali tipi di PDF posso anonimizzare?

- ✅ PDF testuali (creati da Word, LibreOffice, ecc.)
- ✅ PDF scansionati (foto/scan di documenti cartacei) — usa OCR
- ✅ PDF misti (parte testuale, parte scansionata)
- ❌ PDF protetti da password (rimuovere prima la password)
- ❌ Formato non-PDF (DOC, immagini, ecc. — usa convertitori prima)

### Quanto è preciso il riconoscimento?

Dipende dal tipo di documento:

- **PDF testuali ben formattati**: 90-95% di accuratezza
- **PDF scansionati di buona qualità**: 80-90%
- **Scansioni di bassa qualità o caratteri inusuali**: variabile

**Usa sempre il campo "termini specifici"** per i nomi più importanti — è una sicurezza in più.

### Quanto è veloce?

- Documento testuale di 10 pagine: ~10-30 secondi
- Documento scansionato di 10 pagine: ~1-3 minuti (l'OCR è lento)
- Documento di 100+ pagine: minuti o decine di minuti

Streamlit mostra una progress bar durante l'elaborazione.

### Posso elaborare più PDF contemporaneamente?

In modalità Community: un PDF alla volta.
La modalità batch è prevista in una versione futura o Enterprise.

### L'app sbaglia, come posso correggerla?

Hai 3 opzioni:
1. **Aggiungi i termini critici** nel campo "termini specifici"
2. **Disabilita le categorie problematiche** dalla sidebar
3. **Verifica e ritocca manualmente** il PDF risultante con strumenti come Adobe Acrobat o Foxit

---

## 🔧 Tecnico

### Posso modificare il codice?

Sì! È open source AGPL v3. Vedi [CONTRIBUTING.md](../CONTRIBUTING.md).

### Posso integrarlo nel mio software?

Dipende dalla licenza del tuo software. AGPL v3 è "copyleft forte": se distribuisci o offri come servizio una modifica, devi rendere disponibile il codice sorgente.

Se ti serve una licenza commerciale diversa (es. per software proprietario), [contattami](mailto:[inserire-email]).

### Aggiungete altre lingue?

Per ora solo italiano. L'aggiunta di altre lingue è possibile (Presidio + spaCy supportano molte lingue) ma richiede lavoro. PR benvenute!

### Posso usarlo via API o riga di comando?

Non in modalità Community (è solo UI web). Le versioni Enterprise possono includere API.

### Posso usarlo per documenti non legali?

Certo! Funziona con qualsiasi PDF italiano. È stato pensato per il mondo legale ma è general purpose.

---

## 💼 Versione Professional / Enterprise

### Cosa include la versione Professional?

- ✅ Installazione assistita via TeamViewer/AnyDesk (fino a 3 PC)
- ✅ Configurazione personalizzata
- ✅ Training di 1 ora per gli avvocati
- ✅ Supporto email 12 mesi
- ✅ Aggiornamenti inclusi

### Cosa include la versione Enterprise?

Tutto della Professional, più:
- ✅ Hosting su server interno dello studio
- ✅ Gestione utenti multipli con login
- ✅ Audit log completo
- ✅ Supporto telefonico prioritario
- ✅ SLA garantito

### Come si paga?

Bonifico o carta. La fattura viene emessa con P.IVA italiana.

### Posso provare prima di acquistare?

Sì, ti facciamo una **demo gratuita** sui tuoi documenti reali (anonimizzati per la demo).

### Posso annullare?

La versione Professional è una tantum (no abbonamento).
La versione Enterprise è mensile/annuale, annullabile in qualsiasi momento per il ciclo successivo.

---

## 🆘 Problemi comuni

### L'app non si avvia

1. Riavvia il computer
2. Verifica che Python sia installato (`py --version` su Windows, `python3.12 --version` su Mac)
3. Controlla i log nella cartella `logs/`
4. Apri una issue su GitHub

### "Module not found"

Hai cancellato o rovinato l'ambiente virtuale. Reinstalla l'app.

### L'OCR non funziona

Verifica che Tesseract italiano sia installato:
- Windows: `tesseract --list-langs`
- Mac: `brew list | grep tesseract`

Deve apparire `ita` nell'elenco delle lingue.

### Il browser non si apre automaticamente

Apri manualmente `http://localhost:8501` nel tuo browser.

### Errori inattesi

1. Controlla la sezione [Issues su GitHub](../../issues)
2. Se non c'è già una issue per il tuo problema, aprine una nuova con:
   - Sistema operativo
   - Messaggio di errore completo
   - Log della cartella `logs/`

---

## 📞 Hai altre domande?

- **Issues su GitHub** per domande tecniche pubbliche
- **Email**: REPLACE-BEFORE-MERGE@example.invalid per domande commerciali o private
- **Discussions**: per chiacchierare con la community
