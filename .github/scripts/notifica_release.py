#!/usr/bin/env python3
"""
Compone e invia via Resend la mail di notifica di una nuova release.

Legge release.json (prodotto da `gh release view --json`) e le variabili
d'ambiente RESEND_API_KEY, NOTIFY_EMAIL, NOTIFY_FROM, TAG.

Nessuna dipendenza esterna: usa solo la libreria standard, così il job
non deve installare nulla.
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

RESEND_ENDPOINT = "https://api.resend.com/emails"
MAX_NOVITA = 2500  # caratteri di changelog inclusi nel corpo


def markdown_essenziale_in_html(testo):
    """
    Conversione minima del corpo della release (Markdown) in HTML.
    Volutamente limitata: titoli, grassetto, corsivo, codice, link ed
    elenchi puntati — è tutto ciò che usiamo nelle note di rilascio.
    """
    testo = html.escape(testo)
    testo = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
                   r'<a href="\2">\1</a>', testo)
    # URL nudi (es. "Full Changelog: https://…") resi cliccabili, senza
    # toccare quelli già dentro un tag <a> appena creato
    testo = re.sub(r'(?<!href=")(?<!>)(https?://[^\s<]+)(?![^<]*</a>)',
                   r'<a href="\1">\1</a>', testo)
    testo = re.sub(r"`([^`]+)`",
                   r'<code style="background:#EDF0F2;padding:1px 5px;'
                   r'border-radius:3px">\1</code>', testo)
    testo = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", testo)
    testo = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", testo)

    righe, dentro_lista = [], False
    for riga in testo.split("\n"):
        spoglia = riga.strip()
        if spoglia.startswith("#"):
            if dentro_lista:
                righe.append("</ul>")
                dentro_lista = False
            titolo = spoglia.lstrip("#").strip()
            righe.append(f'<h3 style="color:#EC671A;margin:18px 0 6px">'
                         f'{titolo}</h3>')
        elif spoglia.startswith("- "):
            if not dentro_lista:
                righe.append('<ul style="margin:0 0 10px 18px;padding:0">')
                dentro_lista = True
            righe.append(f'<li style="margin-bottom:5px">{spoglia[2:]}</li>')
        elif not spoglia:
            if dentro_lista:
                righe.append("</ul>")
                dentro_lista = False
        else:
            if dentro_lista:
                righe.append("</ul>")
                dentro_lista = False
            righe.append(f'<p style="margin:0 0 10px">{spoglia}</p>')
    if dentro_lista:
        righe.append("</ul>")
    return "\n".join(righe)


def costruisci_html(tag, dati, novita_html):
    nome = html.escape(dati.get("name") or tag)
    url = dati.get("url", "")
    assets = dati.get("assets") or []
    elenco_file = "".join(
        f'<li style="margin-bottom:4px"><a href="{html.escape(a.get("url",""))}">'
        f'{html.escape(a.get("name",""))}</a>'
        f' <span style="color:#8A93A0">({a.get("size",0)//1024} KB)</span></li>'
        for a in assets
    )
    blocco_file = (
        f'<h3 style="color:#EC671A;margin:18px 0 6px">File pubblicati</h3>'
        f'<ul style="margin:0 0 10px 18px;padding:0">{elenco_file}</ul>'
        if elenco_file else ""
    )
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#F6EFD7">
<div style="max-width:640px;margin:0 auto;padding:28px 24px;
            font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;
            color:#334C58;font-size:15px;line-height:1.6">
  <p style="margin:0 0 4px;font-size:11px;letter-spacing:.14em;
            text-transform:uppercase;color:#EC671A;font-weight:700">
    Anonimizzatore PDF</p>
  <h1 style="margin:0 0 6px;font-size:26px;line-height:1.2">
    Nuova versione: {html.escape(tag)}</h1>
  <p style="margin:0 0 18px;color:#8A93A0">{nome}</p>
  <div style="background:#fff;border-radius:8px;padding:18px 20px">
    {novita_html}
    {blocco_file}
  </div>
  <p style="margin:20px 0 0">
    <a href="{html.escape(url)}"
       style="display:inline-block;background:#EC671A;color:#fff;
              text-decoration:none;font-weight:600;padding:11px 20px;
              border-radius:6px">Apri la pagina della release</a>
  </p>
  <p style="margin:22px 0 0;font-size:12px;color:#8A93A0">
    Messaggio automatico inviato alla pubblicazione di una release del
    repository jacktotem/anonimizzatore-pdf.</p>
</div></body></html>"""


def main():
    api_key = os.environ["RESEND_API_KEY"]
    destinatario = os.environ["NOTIFY_EMAIL"]
    # Se non è configurato un mittente, si usa quello di prova di Resend:
    # funziona senza dominio verificato ma consegna SOLO all'indirizzo
    # dell'account Resend.
    mittente = os.environ.get("NOTIFY_FROM") or "onboarding@resend.dev"
    tag = os.environ["TAG"]

    with open("release.json", encoding="utf-8") as f:
        dati = json.load(f)

    corpo = (dati.get("body") or "").strip()
    if len(corpo) > MAX_NOVITA:
        corpo = corpo[:MAX_NOVITA].rsplit("\n", 1)[0] + "\n\n*(…continua sulla pagina della release)*"
    novita_html = (markdown_essenziale_in_html(corpo) if corpo
                   else "<p>Nessuna nota di rilascio.</p>")

    payload = {
        "from": mittente,
        "to": [destinatario],
        "subject": f"Anonimizzatore PDF {tag} — nuova versione disponibile",
        "html": costruisci_html(tag, dati, novita_html),
    }

    richiesta = urllib.request.Request(
        RESEND_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Senza uno User-Agent esplicito, Cloudflare (davanti all'API
            # di Resend) blocca la richiesta con "error code: 1010":
            # il default di urllib ("Python-urllib/3.x") è in blacklist.
            "User-Agent": "anonimizzatore-pdf-notifier/1.0 (+https://github.com/jacktotem/anonimizzatore-pdf)",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=30) as risposta:
            esito = json.load(risposta)
        print(f"Mail inviata a {destinatario} (id: {esito.get('id', 'n/d')})")
    except urllib.error.HTTPError as e:
        dettaglio = e.read().decode("utf-8", "replace")[:500]
        # La chiave non finisce mai nei log: si stampa solo la risposta API
        print(f"ERRORE Resend {e.code}: {dettaglio}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERRORE invio: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
