# 🔒 Politica di sicurezza

## Versioni supportate

| Versione | Supportata |
|----------|------------|
| 1.x      | ✅         |
| < 1.0    | ❌         |

## Segnalare una vulnerabilità

La sicurezza è critica per uno strumento di anonimizzazione di documenti legali. Se trovi una vulnerabilità, **non aprire una issue pubblica**.

### Come segnalare

Manda una email a: **REPLACE-BEFORE-MERGE@example.invalid**

Includi:
- **Descrizione** della vulnerabilità
- **Passi per riprodurla**
- **Impatto** potenziale
- **Suggerimenti** per il fix (se ne hai)

### Cosa aspettarsi

- **Conferma**: entro 48 ore lavorative
- **Valutazione**: entro 7 giorni con un piano di risposta
- **Fix**: dipende dalla gravità (critical: 1 settimana; high: 1 mese; medium/low: prossima release)
- **Disclosure**: coordinato con te dopo il fix

### Ringraziamenti

I ricercatori che segnalano responsabilmente le vulnerabilità saranno ringraziati nel changelog (a meno che non preferiscano l'anonimato).

---

## 🛡️ Considerazioni di sicurezza specifiche

### Documenti sensibili

L'app processa **documenti legali sensibili**. Cose da sapere:

1. **Tutto è locale** — i PDF non vengono mai inviati a server esterni
2. **Niente persistenza** — i documenti non vengono salvati su disco se non come output volontario
3. **Niente telemetria** — Streamlit usage stats è disabilitato esplicitamente
4. **Verifica sempre** — l'AI non è infallibile, controlla il PDF finale prima dell'invio

### Dipendenze

Le dipendenze vengono aggiornate periodicamente. Usa sempre l'ultima versione del software.

### Modelli di minaccia considerati

✅ **Considerati e mitigati:**
- Estrazione di testo dietro rettangoli di redazione (mitigato: redazione vera con rimozione fisica)
- Recupero da metadati (mitigato: i metadati sensibili vengono rimossi)
- Recupero da copy-paste OCR (mitigato: pagina ricostruita come immagine pura)

⚠️ **Considerati ma a rischio dell'utente:**
- File temporanei di sistema (Windows page file, swap macOS) — verificare le impostazioni di sicurezza del proprio OS
- Backup di OneDrive/iCloud — disattivare la sincronizzazione della cartella di lavoro se necessario
- Compromissione del PC dell'utente — fuori scope di questo software

---

**Grazie per aiutarci a mantenere Anonimizzatore PDF sicuro per tutti! 🙏**
