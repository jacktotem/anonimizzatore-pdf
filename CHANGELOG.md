# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.6.0] - 2026-07-20

### Added
- **R-10 — Opzione "Non anonimizzare i magistrati"** (checkbox in
  sidebar, disattivata di default): nella prassi di anonimizzazione
  dei provvedimenti (art. 52 d.lgs. 196/2003) si oscurano le parti,
  non i giudici. Con l'opzione attiva, i nomi riconosciuti nei
  contesti tipici del collegio — epigrafe "dott. X -
  Presidente/Consigliere", "Consigliere relatore dott. X", firme
  digitali "Firmato Da: X", sottoscrizioni "Il Presidente" — restano
  visibili in tutto il documento. Regola prudenziale: un nome è
  considerato magistrato solo se TUTTI i suoi token provengono da quei
  contesti; in dubbio si redige. Il riepilogo mostra quanti nomi sono
  stati esclusi. Vale anche per le pagine OCR.

## [1.5.1] - 2026-07-20

### Fixed
- **R-09 — Stessa persona, stesso codice:** nei provvedimenti la stessa
  persona compare sia come "Cognome Nome" (epigrafe) sia come "Nome
  Cognome" (corpo). La chiave di pseudonimizzazione è ora insensibile
  all'ordine dei token: "Criniti Francesco" e "Francesco Criniti"
  ricevono lo stesso codice, con le occorrenze sommate. Vale solo per
  le persone; sull'ordinanza di riferimento la tabella passa da 35 a
  29 codici. Il solo cognome condiviso da più persone ("Criniti")
  mantiene correttamente un codice proprio: l'attribuzione sarebbe
  ambigua.

## [1.5.0] - 2026-07-20

Seconda release di qualità del rilevamento, guidata dalla tabella di
accoppiamento di un'ordinanza di Cassazione reale: da 65 codici con
~25 falsi positivi a 37 codici senza errori noti.

### Fixed
- **R-07 — Abbreviazioni e formule di rito:** "Cass", "Sez", "civ",
  "P.q.m", "Stato", "Vero", "Illustrissimi Signori", "Corte di
  Lussemburgo" ecc. non vengono più scambiati per nomi o luoghi
  (stoplist ampliata). I **numeri romani** ("III", "XVI") sono
  riconosciuti con una regex stretta e mai redatti. Un
  **PHONE_NUMBER con la forma di una data** ("3.9.2009") viene
  scartato: è una data, non un telefono.
- **R-07 — Trim dei bordi delle entità NER:** il boilerplate catturato
  per errore ai margini viene rimosso prima della redazione: "FRASCA
  Emesso Da" → "FRASCA", "Marco Rossetti - Consigliere rel" → "Marco
  Rossetti". Migliora anche la pseudonimizzazione: la stessa persona
  con e senza ruolo riceve ora lo stesso codice.

### Added
- **R-08 — Citazioni giurisprudenziali preservate:** i nomi dei
  precedenti pubblicati (Köbler, Lucchini, Asturcom, "FY c. Profi
  Credit Polska"...) non sono dati personali da proteggere e
  anonimizzarli distruggerebbe le citazioni. Vengono riconosciuti dal
  contesto — numero di causa CGUE anche spezzato dall'a-capo
  ("C- 869/19", "C-40/"), marcatori "CGUE"/"CEDU"/"in causa"/"cause
  riunite", formato "X c. Y" — e lasciati intatti. Rete di sicurezza:
  se il nome di una parte compare per caso vicino a una citazione,
  quell'occorrenza resta coperta dalla propagazione dei nomi (R-04).

## [1.4.4] - 2026-07-20

### Fixed
- **PRM-01 — Messaggio chiaro sui permessi:** se il setup viene
  eseguito senza privilegi di amministratore (visto sul campo: pip
  lanciato a mano da un prompt non elevato → "[WinError 5] Accesso
  negato" in Program Files), lo script ora lo rileva subito e spiega
  in italiano come rimediare, invece di fallire a metà con un errore
  criptico.
- **PRM-02 — Pulizia dei residui del modello:** le installazioni
  fallite a metà possono lasciare in `site-packages` directory parziali
  di `it_core_news_lg` (anche read-only) che fanno fallire pure i
  tentativi successivi. Prima di ogni tentativo di installazione del
  modello i residui vengono rimossi; `pip install` ora usa
  `--force-reinstall --no-deps` sul wheel verificato.

## [1.4.3] - 2026-07-20

### Fixed
- **NAT-01 — Setup abortito da stderr su Windows PowerShell 5.1:** con
  `$ErrorActionPreference = "Stop"`, ogni riga scritta su stderr da un
  comando nativo rediretto con `2>&1` diventa un errore terminante.
  Due conseguenze osservate sul campo: il controllo "modello già
  installato?" (un `import` che deve poter fallire) abortiva il setup
  mostrando solo "Traceback (most recent call last):"; e gli errori pip
  scavalcavano i retry mostrando il testo grezzo. Ora tutti i comandi
  nativi passano da `Invoke-Native` (EAP locale "Continue", output nel
  log, esito giudicato solo dall'exit code): i controlli possono
  fallire senza far esplodere l'installazione e i retry del modello
  funzionano davvero.

## [1.4.2] - 2026-07-20

### Fixed
- **MDL-01 — "Wheel 'it-core-news-lg' ... is invalid" a fine setup
  Windows:** il modello linguistico (~580 MB) era l'unico download
  dell'installer senza verifica d'integrità (passava dalla scatola nera
  `spacy download`): se il file arrivava corrotto — rete instabile,
  proxy, antivirus che tocca il temp — l'errore emergeva solo alla fine
  dei 15 minuti di setup. Ora il wheel ufficiale viene scaricato
  direttamente con **SHA256 pinnato** (come Python e Tesseract), fino a
  3 tentativi automatici in caso di corruzione, e installato con pip
  dal file locale verificato.
- **Accenti rotti nei messaggi dell'installer** ("NON Ã¨ andata a buon
  fine"): gli script PowerShell erano salvati UTF-8 senza BOM e Windows
  PowerShell li leggeva come ANSI. Aggiunto il BOM a
  `setup-dependencies.ps1` e agli script server.

## [1.4.1] - 2026-07-18

Mitigazioni per i falsi positivi di SmartScreen/Defender sull'installer
non firmato (`DEF-01`/`DEF-02`).

### Changed
- **Installer trasparente:** rimosso il flag `runhidden` — la finestra
  PowerShell del setup resta visibile. L'utente vede cosa viene
  scaricato e installato, e l'installer perde uno dei tratti
  comportamentali "da dropper" che contribuivano ai falsi positivi.
- **CI:** ogni release pubblica ora anche il file `.sha256` accanto
  all'exe e aggiunge l'hash alle note della release, per la verifica
  d'integrità (`certutil -hashfile ... SHA256`). Hash aggiunto
  retroattivamente anche alla v1.4.0.

### Added
- `docs/FALSI-POSITIVI-ANTIVIRUS.md`: perché succede, come verificare
  l'hash e ripristinare dalla quarantena, come segnalare il falso
  positivo a Microsoft (con testo pronto), e la roadmap code signing.
- README: sezione "Avviso SmartScreen / Microsoft Defender" nella
  guida d'installazione Windows.

## [1.4.0] - 2026-07-17

### Added
- **🔄 Verifica aggiornamenti in-app** (`R-06`): pulsante nella barra
  laterale che confronta la versione installata con l'ultima release su
  GitHub e mostra le novità + il link diretto al download. Contatta
  `api.github.com` **solo su click esplicito** e non invia alcun dato —
  nessun codice viene scaricato o eseguito (nessun self-update: scelta
  deliberata per non aprire una superficie supply-chain su un'app per
  studi legali). Usa solo la stdlib (`urllib`), con timeout e gestione
  offline.
- **Script `mac/aggiorna.sh`**: aggiorna la copia macOS con `git pull`
  e reinstalla le librerie **solo se `requirements.txt` è cambiato**.
  Gestisce il caso di copia non-git rimandando alla pagina release.

### Changed
- **Installer Windows idempotente** (`UPD-01`): `setup-dependencies.ps1`
  ora salta i componenti già presenti — Python 3.12, Tesseract, il venv
  con le librerie (fingerprint della lista pacchetti in
  `.deps-fingerprint`) e il modello linguistico italiano (~580 MB). Un
  aggiornamento di versione dell'app passa da ~15 minuti a **circa un
  minuto**. Il venv viene ricreato solo se le dipendenze sono cambiate o
  i moduli non sono importabili; il fingerprint è scritto solo a
  installazione riuscita.

## [1.3.2] - 2026-07-17

### Fixed
- **Download CSV di accoppiamento non più raggiungibile dopo "Scarica
  PDF":** in Streamlit ogni click su un download button riesegue lo
  script e `st.button` torna `False`, quindi i risultati (e con loro il
  bottone del CSV) sparivano dopo il primo download. I risultati ora
  vengono salvati in `st.session_state` e restano visibili tra i
  download; vengono invalidati automaticamente quando si carica un file
  diverso.

## [1.3.1] - 2026-07-15

### Fixed
- **M-03-R2 — Rimozione effettiva di `/OpenAction`, `/AA` e `/Names`
  JavaScript dal catalog:** `xref_set_key(..., "null")` di PyMuPDF
  (implementazione rebased, ≥ 1.24) non cancella la chiave ma lascia la
  coppia `/Chiave null` nel dizionario, che sopravvive anche al
  salvataggio. Un valore `null` è funzionalmente equivalente a chiave
  assente (ISO 32000-1 §7.3.7), quindi il JavaScript non veniva comunque
  eseguito, ma il catalog del documento "anonimizzato" continuava ad
  annunciare la presenza pregressa di OpenAction/JS. Ora, dopo la
  normalizzazione a `null`, le coppie annullate vengono rimosse
  fisicamente riscrivendo il catalog. Ripristina il verde di
  `test_catalog_no_javascript_or_openaction` (verificato su PyMuPDF
  1.24.14, 1.26.4 e 1.28.0).

## [1.3.0] - 2026-07-15

### Added
- **R-05 — Pseudonimizzazione con codici univoci** (selezionabile in
  sidebar, in alternativa all'oscuramento): ogni stringa rilevata viene
  sostituita da un codice stabile (`[PER-01]`, `[CF-01]`, `[TERM-01]`...)
  — stessa stringa → stesso codice in tutto il documento, così il testo
  resta leggibile e coerente. Il testo originale viene comunque rimosso
  fisicamente dal PDF. A parte viene generata la **tabella di
  accoppiamento** codice↔testo (CSV per Excel), con avvertenza: è la
  chiave di re-identificazione e va custodita separatamente; il
  documento pseudonimizzato resta un dato personale ai sensi del GDPR
  finché la tabella esiste. Funziona anche sulle pagine OCR (riquadro
  bianco con codice). Un token propagato ("Alonge") riusa il codice
  della persona ("Alonge Antonio") quando l'attribuzione è univoca.
- **Priorità di redazione senza sovrapposizioni**: ogni parola riceve
  una sola redazione — termini personalizzati (codice TERM coerente),
  poi entità deterministiche (CF, IBAN...), poi NER, poi propagazione.
  Vale in entrambe le modalità e in OCR.
- **Modalità server condiviso** (`windows/server/`): script PowerShell
  per registrare l'app come istanza unica su server Windows
  multiutente (desktop remoto / RDS). L'app parte all'avvio del
  server (attività pianificata, account SYSTEM, riavvio automatico),
  è vincolata a 127.0.0.1 (nessuna esposizione di rete) e viene
  condivisa da tutte le sessioni utente tramite collegamento sul
  desktop pubblico. Include `configura-server.ps1`,
  `rimuovi-server.ps1` e guida `README-SERVER.md` per l'IT.
- CI: workflow `build-installer.yml` — a ogni release pubblicata
  l'installer Windows viene compilato con Inno Setup su un runner
  GitHub e allegato automaticamente alla release. La versione in
  `installer.iss` è derivata dal tag (guard `#ifndef` per la
  compilazione manuale).

## [1.2.0] - 2026-07-15

Release di qualità del rilevamento, in risposta a regressioni osservate
su provvedimenti reali (sentenze d'appello e ordinanze di Cassazione).

### Fixed
- **R-02 — Redazione posizionale:** la redazione delle entità non usa
  più `page.search_for(testo)`, che è case-insensitive e cerca
  sottostringhe: un falso positivo "SE'" oscurava "se" dentro
  "**se**ntenza", "spe**se**", "prete**se**" in tutta la pagina. Ora il
  testo viene analizzato tramite una mappa parola→coordinate e viene
  oscurata **solo l'occorrenza effettivamente rilevata**, ai suoi
  rettangoli. Lo stesso vale per i termini personalizzati, che ora
  corrispondono a parole intere (case-insensitive, ignorando la
  punteggiatura ai bordi) e mai a frammenti.
- **R-01 — Filtro falsi positivi NER:** le parole di boilerplate legale
  scambiate dal modello per nomi ("Firmato Da", "Emesso Da", "Numero",
  "Data", "CAUSA", "Ordinanza Interlocutoria", ...) vengono scartate
  prima della redazione. Il filtro si applica solo alle entità NER
  (PERSON, LOCATION, DATE_TIME, ...) — mai a quelle deterministiche
  (codice fiscale, IBAN, P.IVA, ...). Scartate anche le entità troppo
  corte (< 3 caratteri sostanziali).

### Added
- **R-03 — Recognizer nomi in contesto legale:** nuove regole
  deterministiche per i nomi che il NER statistico manca (es. cognomi
  rari come "Cabalisti"): un nome seguito da "(C.F. ...)" o preceduto
  da un titolo (avv., dott., sig., prof., ing., ...) è una persona.
- **R-04 — Propagazione dei nomi:** i token dei nomi di persona
  rilevati in qualunque pagina vengono oscurati in **tutto** il
  documento (solo parole intere con iniziale maiuscola), coprendo le
  occorrenze che il modello manca. Funziona anche sulle pagine OCR.
- Riepilogo arricchito: conteggio dei falsi positivi scartati e dei
  nomi propagati.

### Known limitations
- Le filigrane diagonali (es. "copia comunicata ai soli fini dell'art
  133 cpc") possono perdere i glifi che attraversano fisicamente un
  rettangolo di redazione: `apply_redactions` rimuove ogni carattere il
  cui bounding box interseca l'area. Mitigato restringendo leggermente
  i rettangoli (`shrink_redact_rect`); il danno residuo è
  over-redaction cosmetica, mai perdita di dati da anonimizzare.

## [1.1.2] - 2026-05-12

Security release in risposta all'audit esterno post-v1.1.1. Chiude tutte
le 10 issue aperte (`#1` – `#10`).

### Security
- **Sanitize JS:** rimosso il guard inesistente `doc.get_js()` che
  intrappolava silenziosamente un `AttributeError`. Il loop di pulizia
  degli xref JavaScript non era **mai** eseguito da v1.0.0: PDF con
  `/OpenAction` JavaScript sopravvivevano alla "sanitizzazione". (`#2`)
- **Sanitize catalog:** dopo lo svuotamento degli xref JS, vengono ora
  strippati anche i riferimenti `/OpenAction`, `/AA` e
  `/Names/JavaScript` dal catalog. Il PDF anonimizzato non annuncia più
  di aver mai contenuto JavaScript. (`#3`)
- **Sanitize attachments:** `embfile_del()` ora viene chiamato per indice
  intero invece che per filename. La vecchia logica cancellava solo la
  prima occorrenza di nomi duplicati — comune nei PDF prodotti da Acrobat
  o Word export, dove un allegato `.docx` con PII poteva sopravvivere
  silenziosamente. (`#4`)
- **Installer Windows:** corretto il SHA256 di Python 3.12.8. Il valore
  pinnato precedente non corrispondeva al file reale di python.org,
  quindi l'installer falliva sempre la verifica di integrità su macchine
  senza Python pre-installato. (`#1`)
- **Installer Windows:** hash placeholder o vuoto ora fa fallire il
  setup in produzione, tranne se viene passato esplicitamente
  `-DevMode`. La vecchia logica accettava silenziosamente download non
  verificati, vanificando la claim di hash pinning. (`#1`)

### Added
- `tests/` con suite pytest minima e PDF fixtures riproducibili.
  Regression guard per `#2`, `#3`, `#4`, più verifica della claim di
  azzeramento metadata. (`#8`)
- `.streamlit/config.toml` con `maxUploadSize = 100` MB e
  `gatherUsageStats = false`. Più un guard difensivo in app per messaggio
  d'errore esplicito al posto del precedente OOM silenzioso. (`#7`)
- `scripts/release-checks.sh` + `.github/workflows/release-checks.yml`:
  CI che fallisce il build su placeholder email residui, hash SHA256
  placeholder, o entry CHANGELOG mancante per il tag corrente. (`#5`,
  `#1`, `#10`)
- `requirements-dev.txt` con pytest, separato dal `requirements.txt` di
  runtime. (`#8`)
- Nota in `docs/SECURITY-ADVISORY-v1.1.0.md` che documenta esplicitamente
  l'asimmetria di trust macOS↔Windows nell'installer (TLS chain Homebrew
  vs hash pinning). (`#6`)

### Changed
- `windows/setup-dependencies.ps1` legge la versione mostrata all'utente
  da una sola variabile `$AppVersion`. Banner di log e dialog di
  successo non sono più disallineati con `installer.iss` e `src/app.py`. (`#9`)
- Placeholder `[inserire email]` / `[inserire email security]` sostituiti
  con `info@jacoporomani.it` in 8 file (SECURITY.md,
  README.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, mac/README-MAC.md,
  docs/FAQ.md, docs/PRIVACY-GDPR.md, docs/ARCHITECTURE.md). Il CI guard
  rifiuta il merge finché non sono sostituiti con un'email reale. (`#5`)
- `docs/ARCHITECTURE.md` sezione "Test e qualità" ora descrive la suite
  reale (`tests/`) invece di una directory che non esisteva, con i test
  storicamente proposti elencati come roadmap. (`#8`)
- `docs/RELEASE-GUIDE.md` aggiornato per il nuovo pattern placeholder e
  il guard CI. (`#5`)

### Deprecated
- Vecchio `CHANGELOG.md` (che era una procedura di rilascio v1.0.0→v1.1.0)
  spostato a `docs/RELEASE-PROCEDURE-v1.1.0.md`. Conservato per
  riferimento storico, non viene più aggiornato. (`#10`)

### Known issues
- Il guard CI fallisce il build finché:
  - L'email reale del maintainer non sostituisce
    `info@jacoporomani.it` (`#5`)
  - Gli SHA256 reali di Tesseract e Tessdata non sostituiscono
    `AGGIORNARE_AL_PRIMO_RILASCIO` in `windows/setup-dependencies.ps1`
    (`#1`)
- Versione unica letta da un file `VERSION` in repo root (così
  `installer.iss`, `setup-dependencies.ps1` e `src/app.py` condividono una
  sola fonte) è ancora todo — per v1.2.0.

## [1.1.1] - 2026-05-11

### Fixed
- Il metadata `producer` del PDF output è ora una stringa vuota invece di
  "Anonimizzatore PDF", che identificava il software anche dopo
  l'anonimizzazione.
- La detection di immagini inline usa `abs(page.mediabox.*)` invece di
  `page.rect.*` per gestire correttamente pagine ruotate.

### Changed
- `st.set_page_config(menu_items={})` per rimuovere i link Streamlit di
  default "Report a bug" e "About".

## [1.1.0] - 2026-04 (data esatta da `git log`)

Security hardening release. **Nota retroattiva (v1.1.2):** l'audit esterno
ha rivelato che diverse claim di questa release non erano realmente
applicate dal codice — vedi i fix `#1`, `#2`, `#3`, `#4` in v1.1.2.

### Added
- Installer Windows con (intento di) verifica SHA256 per ogni binario
  scaricato — vedi `docs/SECURITY-ADVISORY-v1.1.0.md`.
- `sanitize_pdf_objects()`: rimozione di annotazioni, AcroForm, allegati
  embedded e oggetti JavaScript a livello di documento.
- `sanitize_pdf_metadata()`: azzeramento metadata standard + rimozione
  XMP stream.
- Logger strutturato, `$ErrorActionPreference = "Stop"` nell'installer
  per fail-fast.

### Security
- TLS 1.2+ forzato in tutti i download dell'installer.
- URL ufficiali per tutti i binari di terze parti (no mirror non
  verificati).

## [1.0.0] - 2026

Initial public release.

### Added
- Streamlit UI con detection automatica di:
  - PII generiche via Microsoft Presidio + spaCy `it_core_news_lg`
  - Entità italiane custom: `IT_FISCAL_CODE`, `IT_VAT_CODE`,
    `IT_IDENTITY_CARD`, `IT_DRIVER_LICENSE`, `IT_PASSPORT`
  - Termini personalizzati definiti dall'utente
- OCR Tesseract per PDF scansionati (rilevamento automatico delle pagine
  che ne hanno bisogno).
- Redazione fisica via PyMuPDF (testo rimosso, non solo coperto).
- Supporto Windows 10/11 e macOS 12+ (Intel + Apple Silicon).
- Licenza AGPL v3 con offerta licenza commerciale alternativa.

[Unreleased]: https://github.com/jacktotem/anonimizzatore-pdf/compare/v1.1.2...HEAD
[1.1.2]: https://github.com/jacktotem/anonimizzatore-pdf/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/jacktotem/anonimizzatore-pdf/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/jacktotem/anonimizzatore-pdf/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/jacktotem/anonimizzatore-pdf/releases/tag/v1.0.0
