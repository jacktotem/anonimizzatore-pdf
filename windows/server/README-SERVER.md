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
     caso di crash);
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
- I PDF caricati vivono solo nella memoria della sessione browser e non
  vengono salvati su disco dall'app.

## Aggiornamento a una nuova versione

1. Scarica ed esegui il nuovo `AnonimizzatorePDF-Setup-vX.Y.Z.exe`
   (sovrascrive l'installazione esistente).
2. Riavvia l'istanza:

   ```powershell
   Stop-ScheduledTask  -TaskName "AnonimizzatorePDF Server"
   Start-ScheduledTask -TaskName "AnonimizzatorePDF Server"
   ```

   (oppure semplicemente riavvia il server).

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
