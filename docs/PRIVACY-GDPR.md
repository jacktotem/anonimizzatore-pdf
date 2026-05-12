# 🔒 Privacy e GDPR

Questo documento spiega come Anonimizzatore PDF tratta i dati e perché è compatibile con il Regolamento Generale sulla Protezione dei Dati (GDPR, Regolamento UE 2016/679).

---

## 🎯 Principio fondamentale: zero trasferimento di dati

> **I tuoi documenti non lasciano mai il tuo computer.**

Tutta l'elaborazione (estrazione testo, OCR, riconoscimento entità, redazione) avviene **localmente** sulla macchina dell'utente. Nessun dato viene inviato a server esterni, cloud, API di terze parti.

---

## 📊 Trattamento dei dati per fase

### Fase 1 — Caricamento PDF

| Cosa accade | Dove |
|-------------|------|
| L'utente carica un PDF tramite browser | Localmente |
| Streamlit riceve il file via WebSocket sulla porta 8501 | Localmente (localhost) |
| Il PDF viene scritto temporaneamente in `/tmp` o `%TEMP%` | Localmente |

**Nessun trasferimento di rete esterno.**

### Fase 2 — Estrazione testo

| Cosa accade | Dove |
|-------------|------|
| PyMuPDF legge le pagine del PDF | Localmente |
| Per pagine scansionate, Tesseract fa OCR | Localmente |

### Fase 3 — Riconoscimento entità

| Cosa accade | Dove |
|-------------|------|
| Microsoft Presidio analizza il testo | Localmente |
| spaCy carica il modello NLP italiano | Localmente (modello pre-scaricato) |

**Il modello spaCy viene scaricato solo una volta in fase di installazione.** Dopo, l'app funziona completamente offline.

### Fase 4 — Redazione e output

| Cosa accade | Dove |
|-------------|------|
| PyMuPDF rimuove fisicamente il testo | Localmente |
| Il PDF risultante viene messo a disposizione per il download | Localmente |
| Una volta scaricato, il file temporaneo viene eliminato | Localmente |

---

## 🚫 Cosa NON facciamo

❌ **Niente cloud upload** — il PDF non viene mai inviato a server esterni
❌ **Niente API esterne** — non si chiamano servizi di terze parti
❌ **Niente telemetria** — Streamlit usage statistics è disabilitato esplicitamente
❌ **Niente analytics** — non si tracciano metriche d'uso
❌ **Niente backup automatico** — l'utente decide cosa salvare
❌ **Niente account** — non c'è registrazione né login

---

## ✅ Cosa facciamo per la sicurezza

✅ **Codice sorgente aperto** — chiunque può verificare cosa fa l'app
✅ **Redazione fisica** — il testo viene rimosso, non solo coperto
✅ **OCR ricostruito** — le pagine OCR diventano immagini pure, non recuperabili con copy-paste
✅ **Metadati rimossi** — i metadati sensibili del PDF originale (autore, titolo, ecc.) vengono cancellati

---

## ⚖️ Conformità GDPR — Articolo per articolo

### Art. 5 — Principi del trattamento

| Principio | Come lo rispettiamo |
|-----------|---------------------|
| Liceità, correttezza, trasparenza | Codice open source, documentazione completa |
| Limitazione della finalità | Unico scopo: anonimizzare |
| Minimizzazione | Solo i dati strettamente necessari vengono elaborati |
| Esattezza | L'utente verifica il risultato |
| Limitazione della conservazione | Niente persistenza |
| Integrità e riservatezza | Elaborazione 100% locale |

### Art. 25 — Privacy by Design e by Default

L'app è progettata fin dall'inizio per non trattare dati personali fuori dal computer dell'utente. Non esiste un'opzione "invia al cloud" — è strutturalmente impossibile.

### Art. 28 — Responsabili del trattamento

**Anonimizzatore PDF non è un responsabile del trattamento.** Il software gira sul computer dell'utente, che è l'unico titolare del trattamento dei suoi documenti.

### Art. 32 — Sicurezza del trattamento

Misure tecniche:
- ✅ Elaborazione locale
- ✅ Niente trasmissione in rete
- ✅ Redazione fisica (non recuperabile)
- ✅ Codice verificabile pubblicamente

Misure organizzative (a cura dell'utente):
- 🔐 Proteggere l'accesso al computer
- 🔐 Cifrare il disco rigido
- 🔐 Backup sicuri

---

## 📝 Responsabilità dell'utente

L'utente (studio legale, professionista) rimane **unico responsabile**:

1. ✅ **Verificare il risultato** — l'AI può sbagliare
2. ✅ **Configurare il computer** in modo sicuro (cifratura, password, antivirus)
3. ✅ **Gestire i backup** (se attivati, contengono i documenti elaborati)
4. ✅ **Eliminare i file** in modo sicuro quando non servono più
5. ✅ **Adempiere agli obblighi GDPR** verso i propri clienti

---

## 🌐 Hosting e servizi cloud — opzionali e separati

Se in futuro vorrai usare la **versione Enterprise** con hosting centralizzato:

- Il server è dello **studio**, non di terzi
- I dati restano nella **rete interna**
- Il software è lo **stesso**, semplicemente in modalità multi-utente

**La versione Community e Professional NON usa server esterni.**

---

## 🔍 Vuoi verificare?

Il codice è pubblico su GitHub. Puoi:

1. Cercare la stringa `requests.get` o `urllib` nel codice — vedrai che esistono solo per il download iniziale di Tesseract/spaCy in fase di installazione
2. Monitorare il traffico di rete dell'app con Wireshark o Little Snitch — vedrai solo connessioni locali (localhost:8501)
3. Lanciare l'app in una macchina senza internet — funziona identico (dopo l'installazione iniziale)

---

## 📞 Domande?

- **GitHub Issues** per domande pubbliche
- **Email**: REPLACE-BEFORE-MERGE@example.invalid per audit/compliance privato

---

> **In sintesi**: Anonimizzatore PDF è progettato per essere **GDPR-compliant by design**. Niente cloud, niente API, niente telemetria. Codice aperto e verificabile.
