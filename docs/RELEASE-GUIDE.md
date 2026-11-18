# Guida al rilascio (per chi mantiene il progetto)

Come si pubblica oggi una nuova versione. Ogni passaggio che può essere
controllato da una macchina lo è: se un controllo fallisce, non si rilascia.

## In breve

1. Le modifiche arrivano su `main` solo con una pull request.
2. La pull request aggiorna versione e changelog.
3. I test automatici devono essere verdi.
4. Si pubblica una release su GitHub con il tag della versione.
5. GitHub compila l'installer Windows, lo allega alla release e manda la
   notifica via email.

## 1. Preparare la pull request

- **Codice:** si modifica solo `src/app.py`. Poi
  `bash scripts/sync-app.sh` aggiorna le copie in `mac/` e `windows/app/`.
- **Versione**, in tre punti che devono coincidere:
  - `__version__` in `src/app.py`;
  - `#define MyAppVersion` (e il commento sopra) in `windows/installer.iss`;
  - una nuova sezione `## [X.Y.Z] - AAAA-MM-GG` in `CHANGELOG.md`, sotto
    `## [Unreleased]`.
- **Librerie:** l'unico elenco è `requirements.txt` (lo leggono
  `mac/installa.sh` e `mac/aggiorna.sh`); `windows/setup-dependencies.ps1`
  ne tiene una copia in `$PythonPackages`, che va tenuta identica.
  Cambiare quell'elenco fa ricostruire l'ambiente agli utenti Windows al
  prossimo aggiornamento: va detto nelle note di rilascio.
- **Dati di esempio:** solo di fantasia, anche nei commenti e nella
  descrizione della pull request.

Controllo locale, dalla radice del progetto:

```bash
bash scripts/release-checks.sh
python -m pytest -q
```

## 2. Cosa controlla GitHub sulla pull request

| Workflow | Cosa prova | Quando parte |
|---|---|---|
| `test.yml` | copie di `app.py` identiche, versione coerente, suite completa con PyMuPDF minimo e ultimo | ogni PR e ogni push su `main` |
| `test-installazione-windows.yml` | installer vero su Windows in quattro scenari, poi la suite nell'ambiente installato | PR che toccano `windows/`, l'app, le librerie o i test; ogni lunedì |
| `test-installazione-mac.yml` | `installa.sh` su un Mac pulito, librerie nei limiti, avvio dell'app, suite nell'ambiente installato | PR che toccano `mac/`, l'app, le librerie o i test; ogni lunedì |

Le prove del lunedì servono a scoprire quando una libreria pubblicata da
altri rompe un'installazione da zero, anche se il progetto non è cambiato.

## 3. Unire e pubblicare

1. Unire la pull request (squash).
2. Creare la release dal commit appena unito:

   ```bash
   gh release create vX.Y.Z --target <commit completo> \
     --title "vX.Y.Z — titolo breve" --notes-file note.md --latest
   ```

   Le note sono per chi usa il programma: che cosa cambia per lui e come
   aggiornare (Windows; Mac con git; Mac con zip; server, se serve
   fermare l'attività).
3. La pubblicazione fa partire due workflow:
   - `build-installer.yml` compila l'installer **dal tag**, lo allega con
     il file `.sha256` e aggiunge l'impronta alle note;
   - `notifica-release.yml` aspetta che l'installer sia allegato e manda
     la mail.
4. Verificare: l'exe è tra gli allegati, l'impronta nelle note coincide
   con quella del file scaricato.

Su Mac non c'è nulla da compilare: `aggiorna.sh` porta le copie
scaricate con git all'ultima versione rilasciata.

## Cose da non fare

- **Non compilare l'installer a mano** per allegarlo a una release: quello
  pubblicato deve venire dal workflow, con la sua impronta.
- **Non sostituire l'installer di una release già pubblicata.** Se c'è un
  errore si pubblica una versione nuova.
- **Non usare `git add .` o `git add -A`** senza guardare cosa entra: i
  file locali (log di installazione, documenti di prova) non devono finire
  nel repository pubblico.

## Configurazione del repository

- Secret: `RESEND_API_KEY`, `NOTIFY_EMAIL`, `NOTIFY_FROM` (gli indirizzi
  sono secret perché il repository è pubblico e i log sono leggibili).
- L'installer non è firmato digitalmente: vedi
  [`FALSI-POSITIVI-ANTIVIRUS.md`](FALSI-POSITIVI-ANTIVIRUS.md).

La procedura della versione 1.1.0 è conservata, come riferimento
storico, in [`RELEASE-PROCEDURE-v1.1.0.md`](RELEASE-PROCEDURE-v1.1.0.md):
non va seguita per le versioni attuali.
