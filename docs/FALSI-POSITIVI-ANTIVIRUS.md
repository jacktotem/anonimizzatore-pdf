# 🛡️ Falsi positivi antivirus — perché succedono e cosa fare

## Perché Defender a volte segnala o rimuove l'installer

L'installer `AnonimizzatorePDF-Setup-vX.Y.Z.exe`:

- **non è firmato digitalmente** (la firma richiede un certificato commerciale a pagamento);
- è **compilato nuovo a ogni release** da GitHub Actions, quindi ogni exe è un file mai visto prima, con reputazione zero per SmartScreen;
- per funzionare fa cose che, viste da un antivirus, somigliano al comportamento di un malware "dropper": lancia PowerShell, scarica gli installer ufficiali di Python e Tesseract e li esegue.

Su file a reputazione zero il verdetto lo dà un classificatore automatico, che è probabilistico: **una release può passare pulita e la successiva essere segnalata**, senza che nulla di sostanziale sia cambiato. Le etichette tipiche di questi falsi positivi sono `Trojan:Win32/Wacatac` o `Program:Win32/Wacapew`.

Ogni download resta comunque **verificabile**: il codice sorgente è tutto in questo repository, la build è pubblica (tab *Actions*) e ogni release include lo SHA256 dell'exe.

## Per l'utente: verificare e ripristinare

1. **Verifica lo SHA256** del file scaricato:
   ```
   certutil -hashfile AnonimizzatorePDF-Setup-vX.Y.Z.exe SHA256
   ```
   Il valore deve coincidere con quello pubblicato nella pagina della release (file `.sha256` e sezione "Verifica integrità"). Se non coincide, **non eseguire il file** e riscaricalo.
2. **Avviso SmartScreen** ("PC protetto da Windows"): *Ulteriori informazioni* → *Esegui comunque*.
3. **File rimosso/quarantenato**: *Sicurezza di Windows* → *Protezione da virus e minacce* → *Cronologia protezione* → seleziona la rilevazione → *Azioni* → *Ripristina* (o *Consenti nel dispositivo*).
4. In ambienti gestiti (studio con IT): chiedete all'IT di aggiungere un'esclusione o di distribuire l'app dal server condiviso (`windows/server/`), così nessuno deve scaricare l'exe.

## Per il maintainer: segnalare il falso positivo a Microsoft

La segnalazione "ripulisce" il singolo file per tutti gli utenti, di solito entro 24-72 ore. Va **ripetuta a ogni release segnalata** (l'hash cambia).

1. Vai su **https://www.microsoft.com/wdsi/filesubmission**
2. Accedi con un account Microsoft e scegli il profilo **Software developer**
   (in alternativa **Home customer**, senza priorità).
3. Compila:
   - *Select the file*: carica l'exe della release segnalata
   - *What do you believe this file is?* → **Incorrectly detected as malware/malicious**
   - *Detection name*: il nome mostrato da Defender (es. `Trojan:Win32/Wacatac.B!ml`)
   - *Additional information*: testo pronto qui sotto
4. Conserva il numero di submission per il follow-up.

Testo pronto da incollare (adattare versione e link):

> This is a false positive. The file is the official installer of "Anonimizzatore PDF", an open-source (AGPL v3) GDPR document-redaction tool for Italian law firms. Source code: https://github.com/jacktotem/anonimizzatore-pdf — the installer is built automatically from source by GitHub Actions (public build logs in the Actions tab) and its SHA256 is published on the release page: https://github.com/jacktotem/anonimizzatore-pdf/releases — The installer legitimately downloads and runs the official Python and Tesseract installers (hash-pinned, official URLs only), which may resemble dropper behavior. The binary is unsigned because the project has no code-signing certificate yet.

## La soluzione definitiva

Solo la **firma digitale** (code signing) elimina il problema alla radice, perché la reputazione si trasferisce da una release all'altra. Opzioni valutate nel progetto: Azure Trusted Signing (~10 $/mese, integrabile in GitHub Actions) o certificato OV/EV tradizionale (~200-600 €/anno). Finché non c'è, valgono le mitigazioni sopra.
