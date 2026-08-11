#!/usr/bin/env python3
"""
Invia via Resend la notifica operativa di una nuova release.

Destinatario tipo: il responsabile IT, che deve installare
l'aggiornamento sul server Windows dello studio. La mail è quindi una
CONSEGNA DI ISTRUZIONI, non un annuncio di novità: dice cosa scaricare,
cosa eseguire e come verificare che sia andata a buon fine.

Legge release.json (prodotto da `gh release view --json`) e le variabili
d'ambiente RESEND_API_KEY, NOTIFY_EMAIL, NOTIFY_FROM, TAG.
Nessuna dipendenza esterna: solo libreria standard.
"""
import html
import json
import os
import sys
import urllib.error
import urllib.request

RESEND_ENDPOINT = "https://api.resend.com/emails"
TIMEOUT = 30
UA = ("anonimizzatore-pdf-notifier/1.0 "
      "(+https://github.com/jacktotem/anonimizzatore-pdf)")


def trova_asset(assets, suffisso):
    for a in assets or []:
        if (a.get("name") or "").endswith(suffisso):
            return a
    return None


def leggi_hash(asset):
    """Scarica il file .sha256 e ne estrae l'impronta. None se non riesce."""
    if not asset or not asset.get("url"):
        return None
    try:
        req = urllib.request.Request(asset["url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8", "replace").split()[0]
    except Exception:
        return None


def costruisci_html(tag, versione, url_release, exe, impronta):
    nome_exe = html.escape(exe.get("name", "AnonimizzatorePDF-Setup.exe")) if exe else ""
    url_exe = html.escape(exe.get("url", url_release)) if exe else url_release
    peso = f" ({exe.get('size', 0) // 1024 // 102 / 10:.1f} MB)" if exe else ""

    blocco_hash = ""
    if impronta:
        blocco_hash = f"""
    <p style="margin:14px 0 4px;font-size:13px;color:#8A93A0">
      Verifica del file (facoltativa) — da prompt dei comandi:<br>
      <code style="display:inline-block;margin-top:4px;background:#EDF0F2;
                   padding:5px 8px;border-radius:4px;font-size:12px">
      certutil -hashfile {nome_exe} SHA256</code><br>
      <span style="font-size:11px">deve risultare:
      <code style="font-size:11px;word-break:break-all">{html.escape(impronta)}</code></span>
    </p>"""

    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#F6EFD7">
<div style="max-width:640px;margin:0 auto;padding:28px 24px;
            font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;
            color:#334C58;font-size:15px;line-height:1.6">

  <p style="margin:0 0 4px;font-size:11px;letter-spacing:.14em;
            text-transform:uppercase;color:#EC671A;font-weight:700">
    Anonimizzatore PDF · Aggiornamento</p>
  <h1 style="margin:0 0 10px;font-size:25px;line-height:1.25">
    Da installare sul server: versione {html.escape(versione)}</h1>
  <p style="margin:0 0 20px">
    È disponibile una nuova versione dell'Anonimizzatore PDF.
    Occorre aggiornare l'installazione sul server Windows dello studio.</p>

  <div style="background:#fff;border-radius:8px;padding:20px 22px">
    <h2 style="margin:0 0 14px;font-size:15px;color:#EC671A;
               text-transform:uppercase;letter-spacing:.08em">Come procedere</h2>

    <p style="margin:0 0 6px"><strong>1. Scarica l'installer</strong></p>
    <p style="margin:0 0 16px">
      <a href="{url_exe}"
         style="display:inline-block;background:#EC671A;color:#fff;
                text-decoration:none;font-weight:600;padding:10px 18px;
                border-radius:6px">Scarica {nome_exe}</a>
      <span style="color:#8A93A0;font-size:13px">{peso}</span></p>

    <p style="margin:0 0 6px"><strong>2. Eseguilo sul server</strong></p>
    <p style="margin:0 0 16px;color:#334C58">
      Doppio click e conferma la richiesta di autorizzazione di Windows.
      <strong>Non serve disinstallare</strong> la versione precedente:
      l'installer va eseguito sopra quella esistente e riconosce i
      componenti già presenti (richiede circa un minuto).</p>

    <p style="margin:0 0 6px"><strong>3. Riavvia il servizio</strong></p>
    <p style="margin:0 0 8px;color:#334C58">
      Da PowerShell come amministratore, oppure riavviando il server:</p>
    <div style="background:#EDF0F2;border-radius:5px;padding:10px 12px;
                font-family:Consolas,Menlo,monospace;font-size:12.5px;
                margin:0 0 16px;line-height:1.7">
      Stop-ScheduledTask&nbsp;&nbsp;-TaskName "AnonimizzatorePDF Server"<br>
      Start-ScheduledTask -TaskName "AnonimizzatorePDF Server"
    </div>

    <p style="margin:0 0 6px"><strong>4. Verifica</strong></p>
    <p style="margin:0;color:#334C58">
      Da una sessione desktop remoto apri il collegamento
      <em>Anonimizzatore PDF</em>: sotto il titolo deve comparire
      <strong>v{html.escape(versione)}</strong>.</p>
    {blocco_hash}
  </div>

  <p style="margin:18px 0 0;padding:12px 16px;background:#F6EFD7;
            border-left:4px solid #78C7C9;font-size:13.5px">
    Se Windows segnala il file come non riconosciuto, si tratta
    dell'avviso SmartScreen sugli installer non firmati:
    <em>Ulteriori informazioni → Esegui comunque</em>.</p>

  <p style="margin:22px 0 0;font-size:12px;color:#8A93A0">
    Note tecniche complete della versione:
    <a href="{html.escape(url_release)}" style="color:#8A93A0">pagina della release</a>.<br>
    Messaggio automatico generato alla pubblicazione della versione {html.escape(tag)}.</p>
</div></body></html>"""


def main():
    api_key = os.environ["RESEND_API_KEY"]
    destinatario = os.environ["NOTIFY_EMAIL"]
    mittente = os.environ.get("NOTIFY_FROM") or "onboarding@resend.dev"
    tag = os.environ["TAG"]
    versione = tag.lstrip("vV")

    with open("release.json", encoding="utf-8") as f:
        dati = json.load(f)

    assets = dati.get("assets") or []
    exe = trova_asset(assets, ".exe")
    impronta = leggi_hash(trova_asset(assets, ".sha256"))

    payload = {
        "from": mittente,
        "to": [destinatario],
        "subject": (f"Notifica automatica da Jacopo: Anonimizzatore PDF "
                    f"{versione} — aggiornamento da installare sul server"),
        "html": costruisci_html(tag, versione, dati.get("url", ""), exe, impronta),
    }

    richiesta = urllib.request.Request(
        RESEND_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Senza User-Agent esplicito Cloudflare (davanti all'API di
            # Resend) risponde 403 "error code: 1010".
            "User-Agent": UA,
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=TIMEOUT) as risposta:
            esito = json.load(risposta)
        print(f"Mail inviata a {destinatario} (id: {esito.get('id', 'n/d')})")
    except urllib.error.HTTPError as e:
        dettaglio = e.read().decode("utf-8", "replace")[:500]
        # La chiave non compare mai: si stampa solo la risposta dell'API
        print(f"ERRORE Resend {e.code}: {dettaglio}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERRORE invio: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
