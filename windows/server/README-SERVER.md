# 🖥️ Modalità server condiviso (desktop remoto / RDS)

Guida per installare **Anonimizzatore PDF** su un server Windows multiutente
(es. cloud dello studio a cui gli avvocati accedono in desktop remoto via VPN).

**Il risultato:** un'unica istanza dell'app, sempre attiva, condivisa da tutte
le sessioni utente. Ogni avvocato la usa aprendo il collegamento
**"Anonimizzatore PDF"** sul desktop (o il browser su `http://localhost:8501`).

---

## Perché un'istanza unica (e non una per utente)

| | Istanza unica condivisa | Una copia per utente |
|---|---|---|
| RAM | ~1 GB totale (modello caricato una volta) | ~1 GB **per utente** |
| Porta 8501 | Nessun conflitto | Conflitto se in due la lanciano insieme |
| Manutenzione | Un solo punto da aggiornare | N installazioni |

## Requisiti

- Windows Server 2016+ (o Windows 10/11 multiutente)
- **4 GB di RAM liberi** consigliati (l'app ne usa ~1 in idle, di più durante l'OCR)
- Accesso amministratore (solo per l'installazione)
- Anonimizzatore PDF **v1.2.0 o successiva**

## Installazione (10 minuti + download dipendenze)

1. **Installa l'app** con l'installer standard:
   scarica `AnonimizzatorePDF-Setup-vX.Y.Z.exe` dall'ultima
   [release GitHub](https://github.com/jacktotem/anonimizzatore-pdf/releases)
   ed eseguilo come amministratore. Attendi il completamento del setup
   delle dipendenze (Python, Tesseract, librerie: 10-15 minuti).

2. **Configura la modalità server**: apri PowerShell **come amministratore**
   nella cartella `windows/server/` di questo repository ed esegui:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\configura-server.ps1
   ```

   Lo script:
   - registra l'attività pianificata **"AnonimizzatorePDF Server"** che avvia
     l'app all'accensione del server (account SYSTEM, riavvio automatico in
     caso di crash) — vedi "Account dell'attività" più sotto;
   - la avvia subito e verifica che risponda;
   - crea il collegamento **"Anonimizzatore PDF"** sul desktop di tutti gli utenti.

3. **Verifica**: da una sessione desktop remoto qualsiasi, doppio click sul
   collegamento → l'app si apre nel browser. Fine.

Parametri opzionali:

```powershell
.\configura-server.ps1 -InstallPath "D:\Apps\AnonimizzatorePDF"  # percorso non standard
.\configura-server.ps1 -Port 8600                                # porta diversa
```

## Sicurezza e privacy

- L'app è vincolata a **127.0.0.1**: è raggiungibile **solo dalle sessioni
  aperte sul server stesso**. Nessuna porta esposta sulla rete, nessuna
  regola firewall da aggiungere, niente da pubblicare su internet.
- I documenti **non lasciano il server dello studio**: l'elaborazione è
  interamente locale (nessun cloud, nessuna API esterna), come nella
  versione desktop.
- I PDF caricati vivono nella memoria del programma. Solo l'OCR usa file
  temporanei: ogni pagina letta da Tesseract passa per qualche istante
  da un file nella cartella temporanea dell'account che esegue l'app, e
  viene cancellata a fine pagina. I file rimasti da un'esecuzione
  interrotta vengono cancellati al riavvio dell'app.
- Tutti gli utenti del server usano la stessa istanza, **senza
  autenticazione**: chiunque abbia una sessione sul server può aprire
  l'app. Ogni sessione vede solo i propri documenti.

### Account dell'attività

Lo script registra l'attività con l'account **SYSTEM**, il più semplice
da configurare. L'app apre PDF ricevuti da terzi con librerie in codice
nativo (MuPDF, Tesseract): un PDF costruito per sfruttare un difetto di
una di queste librerie agirebbe con i privilegi dell'account che esegue
l'app, cioè — con SYSTEM — con il controllo completo del server.

Dove il server ospita altri servizi o dati, conviene eseguire l'attività
con un **account locale dedicato senza privilegi amministrativi**, con
sola lettura sulla cartella dell'app: in Utilità di pianificazione, nelle
proprietà dell'attività, "Cambia utente o gruppo". Tenere l'app
aggiornata riduce comunque l'esposizione.

Se l'app è installata fuori da `Program Files` (per esempio in
`D:\Apps`), verificare che gli utenti normali **non possano scrivere**
in quella cartella: chi può sostituire `app.py` o una libreria la fa
eseguire con l'account dell'attività.

Dopo la configurazione, sul desktop comune restano due icone con lo
stesso nome: quella creata dall'installer (un file `.lnk`) avvia
un'istanza privata per il singolo utente e va **rimossa**; quella creata
da questo script (un file `.url`) apre l'istanza condivisa.

## Aggiornamento a una nuova versione

1. **Prima ferma l'istanza.** Quando cambiano le librerie il setup
   ricostruisce l'ambiente dell'app: con l'istanza in esecuzione i file
   sono in uso e l'aggiornamento resta a metà.

   ```powershell
   Stop-ScheduledTask -TaskName "AnonimizzatorePDF Server"
   ```

2. Scarica ed esegui il nuovo `AnonimizzatorePDF-Setup-vX.Y.Z.exe`
   (sovrascrive l'installazione esistente).
3. Riavvia l'istanza:

   ```powershell
   Start-ScheduledTask -TaskName "AnonimizzatorePDF Server"
   ```

   (oppure semplicemente riavvia il server).

Dalla 2.2.0 il setup ferma da solo l'attività se la trova in esecuzione
e la riavvia alla fine; fermarla a mano resta la via più sicura.

## Rimozione della modalità server

```powershell
.\rimuovi-server.ps1
```

Rimuove attività pianificata e collegamento (l'app resta installata; per
disinstallarla del tutto usare "Installazione applicazioni" di Windows).

## Risoluzione problemi

| Sintomo | Causa probabile | Rimedio |
|---|---|---|
| Il collegamento apre una pagina bianca / errore di connessione | L'istanza non è partita o sta ancora caricando il modello (1-2 min al primo avvio) | Attendere, poi `Start-ScheduledTask -TaskName "AnonimizzatorePDF Server"` |
| "Attività non trovata" | Configurazione mai eseguita | Rieseguire `configura-server.ps1` |
| App lenta con molti utenti simultanei | CPU satura (l'OCR è pesante) | Aumentare i core del server; invitare a usare "Forza OCR" solo quando serve |
| Dopo un aggiornamento l'app non riparte | Percorso installazione cambiato | Rieseguire `configura-server.ps1` con il `-InstallPath` corretto |

Log dell'attività: **Utilità di pianificazione** → `AnonimizzatorePDF Server` →
scheda *Cronologia*.
