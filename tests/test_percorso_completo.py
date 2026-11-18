"""
Test dell'intero percorso: PDF in ingresso -> redact_pdf -> PDF prodotto.

Gli altri test verificano i singoli pezzi (filtri, riconoscitori,
sanitizzazione). Qui si controlla la promessa fatta all'utente: nel file
prodotto i dati riconosciuti non ci sono piu', in nessuna forma.

Regola: il PDF prodotto contiene solo cio' che l'analisi ha visto.
Campi modulo, livelli nascosti, link e testo fuori dal ritaglio sono
canali che l'estrazione del testo non vedeva e che finivano comunque
nel file (audit del 17 novembre 2026).

Nessun test richiede spaCy: l'analizzatore e' finto e riconosce un
elenco fisso di parole. I casi con OCR vengono saltati se Tesseract
non e' installato. Tutti i dati sono di fantasia.
"""
import io
import re

import fitz
import pytest
from presidio_analyzer import RecognizerResult

import app
from app import redact_pdf

COGNOME = "Zanfretta"
NOME = "Ermenegildo"
ENTITA = ["PERSON"]

serve_ocr = pytest.mark.skipif(
    not app.TESSERACT_AVAILABLE, reason="Tesseract non installato"
)


class AnalizzatoreFinto:
    """Riconosce un elenco fisso di parole; puo' fallire a comando."""

    def __init__(self, parole=(NOME, COGNOME, "Bragadin"), fallisci_alla=None):
        self.parole = parole
        self.fallisci_alla = fallisci_alla
        self.chiamate = 0

    def analyze(self, text, entities, language):
        self.chiamate += 1
        if self.chiamate == self.fallisci_alla:
            raise RuntimeError("guasto simulato")
        trovati = []
        for parola in self.parole:
            for m in re.finditer(rf"(?<!\w){re.escape(parola)}(?!\w)", text):
                trovati.append(RecognizerResult("PERSON", m.start(), m.end(), 0.85))
        return trovati


def _varianti(ago):
    yield ago.encode()
    yield ago.encode("utf-16-be")
    yield ago.encode().hex().encode()
    yield ago.encode("utf-16-be").hex().encode()


def _nei_byte(doc, ago):
    """True se `ago` compare in un qualunque oggetto o flusso del PDF."""
    for xref in range(1, doc.xref_length()):
        try:
            pezzi = [doc.xref_object(xref, compressed=True).encode("latin-1", "replace")]
            if doc.xref_is_stream(xref):
                pezzi.append(doc.xref_stream(xref) or b"")
        except Exception:
            continue
        for pezzo in pezzi:
            basso = pezzo.lower()
            if any(v.lower() in basso for v in _varianti(ago)):
                return True
    return False


def _esegui(doc, analizzatore=None, termini=(), **opzioni):
    esito = redact_pdf(
        doc.tobytes(), ENTITA, list(termini),
        analizzatore or AnalizzatoreFinto(), **opzioni,
    )
    return esito, fitz.open(stream=esito.pdf, filetype="pdf")


def _testo(doc):
    return "\n".join(p.get_text() for p in doc)


def _pagina(testo="Il sig. Ermenegildo Zanfretta abita a Rovereto da molti anni e lavora in citta'."):
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_text((72, 90), testo, fontsize=12)
    return doc, pagina


def _ocr(pagina):
    import pytesseract
    from PIL import Image
    img = Image.open(io.BytesIO(pagina.get_pixmap(dpi=200).tobytes("png")))
    return pytesseract.image_to_string(img, lang="ita" if app.ITALIAN_AVAILABLE else "eng")


# ------------------------------------------------------------
# Base: il testo riconosciuto sparisce dal file, non solo dalla vista
# ------------------------------------------------------------

@pytest.mark.parametrize("modo", ["blackout", "codes"])
def test_testo_riconosciuto_assente_da_testo_e_byte(modo):
    doc, _ = _pagina()
    esito, out = _esegui(doc, redaction_mode=modo)
    assert COGNOME not in _testo(out)
    assert not _nei_byte(out, COGNOME)
    assert "Rovereto" in _testo(out)          # il resto resta
    assert esito.log, "la redazione deve comparire nel report"
    assert esito.avvisi["pagine_fallite"] == []


def test_il_risultato_si_spacchetta_come_prima():
    """Chi usa pdf, log, mapping per posizione continua a funzionare."""
    doc, _ = _pagina()
    pdf, log, mapping, avvisi = redact_pdf(doc.tobytes(), ENTITA, [], AnalizzatoreFinto())
    assert pdf[:4] == b"%PDF" and isinstance(log, list) and isinstance(avvisi, dict)


# ------------------------------------------------------------
# A1 / A10: campi modulo
# ------------------------------------------------------------

def _con_campo(valore, rect=(72, 200, 400, 222), nome="campo_cognome"):
    doc, pagina = _pagina("Modulo di denuncia di sinistro compilato dal contraente in ogni sua parte.")
    w = fitz.Widget()
    w.field_name = nome
    w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    w.rect = fitz.Rect(*rect)
    w.field_value = valore
    w.field_label = f"Suggerimento {valore}"
    pagina.add_widget(w)
    return doc


@pytest.mark.parametrize("modo", ["blackout", "codes"])
def test_valore_di_un_campo_modulo_non_resta_nel_file(modo):
    doc = _con_campo(f"{NOME} {COGNOME}")
    esito, out = _esegui(doc, redaction_mode=modo)
    assert COGNOME not in _testo(out)
    assert not _nei_byte(out, COGNOME), "valore, nome o suggerimento del campo ancora nel file"
    assert all(not list(p.widgets() or []) for p in out)


def test_campo_modulo_non_riconosciuto_resta_visibile_come_testo():
    """Un modulo compilato non deve uscire in bianco: il valore diventa
    testo della pagina e passa dall'analisi come tutto il resto."""
    doc = _con_campo("Polizza numero 4455")
    _, out = _esegui(doc)
    assert "4455" in _testo(out)
    assert all(not list(p.widgets() or []) for p in out)


def test_nome_del_campo_modulo_non_resta_nel_file():
    doc = _con_campo("valore qualsiasi", nome=f"cognome_{COGNOME}")
    _, out = _esegui(doc)
    assert not _nei_byte(out, COGNOME)


def test_nessun_modulo_nel_catalogo_del_risultato():
    doc = _con_campo("valore qualsiasi")
    _, out = _esegui(doc)
    assert out.xref_get_key(out.pdf_catalog(), "AcroForm")[0] == "null"


# ------------------------------------------------------------
# A6: link
# ------------------------------------------------------------

def test_link_rimossi_anche_dalle_pagine_senza_redazioni():
    doc, pagina = _pagina("Per informazioni generali sul procedimento scrivere allo studio legale.")
    pagina.insert_link({
        "kind": fitz.LINK_URI, "from": fitz.Rect(72, 80, 300, 95),
        "uri": "mailto:ermenegildo.zanfretta@esempio.it",
    })
    esito, out = _esegui(doc)
    assert esito.log == []                      # nessuna redazione sulla pagina
    assert all(not p.get_links() for p in out)
    assert not _nei_byte(out, COGNOME)


# ------------------------------------------------------------
# A4: livelli nascosti
# ------------------------------------------------------------

def test_testo_in_un_livello_nascosto_viene_analizzato():
    doc, pagina = _pagina()
    livello = doc.add_ocg("Bozza nascosta", on=False)
    pagina.insert_text((72, 300), "Versione precedente: Bragadin contro Zanfretta", fontsize=11, oc=livello)
    _, out = _esegui(doc)
    assert "Bragadin" not in _testo(out)
    assert not _nei_byte(out, "Bragadin")
    assert not _nei_byte(out, COGNOME)


def test_livello_nascosto_e_campo_modulo_nella_stessa_pagina():
    """I due canali insieme: l'ordine delle operazioni di preparazione
    non deve lasciare fuori dall'analisi il livello nascosto."""
    doc = _con_campo("valore del campo")
    livello = doc.add_ocg("Bozza nascosta", on=False)
    doc[0].insert_text((72, 300), "Versione precedente: Bragadin contro Zanfretta", fontsize=11, oc=livello)
    esito, out = _esegui(doc)
    assert esito.avvisi["campi_modulo"] == 1
    assert not _nei_byte(out, "Bragadin")
    assert not _nei_byte(out, COGNOME)


# ------------------------------------------------------------
# A5: testo fuori dall'area visibile
# ------------------------------------------------------------

def test_testo_fuori_dal_ritaglio_viene_analizzato():
    doc, pagina = _pagina("Atto di citazione. Le parti hanno concluso come da verbale di udienza del giorno.")
    pagina.insert_text((72, 800), "Il sig. Ermenegildo Zanfretta", fontsize=11)
    ritaglio = fitz.Rect(0, 0, pagina.rect.width, 700)
    pagina.set_cropbox(ritaglio)
    _, out = _esegui(doc)
    assert not _nei_byte(out, COGNOME)
    # la pagina resta ritagliata come l'originale
    assert abs(out[0].rect.height - 700) < 1
    assert "Atto di citazione" in _testo(out)


# ------------------------------------------------------------
# A3: errore su una pagina
# ------------------------------------------------------------

def test_pagina_con_errore_di_analisi_non_esce_in_chiaro():
    doc = fitz.open()
    for i in range(3):
        doc.new_page().insert_text(
            (72, 90), f"Pagina {i + 1}. Il sig. Ermenegildo Zanfretta abita a Rovereto da anni.", fontsize=12)
    esito, out = _esegui(doc, AnalizzatoreFinto(fallisci_alla=2))
    assert esito.avvisi["pagine_fallite"] == [2]
    assert len(out) == 3
    assert COGNOME not in _testo(out)
    assert not _nei_byte(out, COGNOME)
    assert out[1].get_text().strip() == ""      # pagina oscurata per intero
    assert "Rovereto" in out[0].get_text() and "Rovereto" in out[2].get_text()
    assert any(r["Pagina"] == 2 and "NON ANALIZZATA" in r["Tipo"] for r in esito.log)


@serve_ocr
def test_pagina_con_ocr_fallito_non_esce_in_chiaro(monkeypatch):
    import pytesseract

    def rotto(*a, **k):
        raise RuntimeError("tesseract non risponde")

    doc = _scansione("Il sig. Ermenegildo Zanfretta abita a Rovereto.")
    monkeypatch.setattr(pytesseract, "image_to_data", rotto)
    esito, out = _esegui(doc)
    monkeypatch.undo()
    assert esito.avvisi["pagine_fallite"] == [1]
    assert COGNOME.lower() not in _ocr(out[0]).lower()


# ------------------------------------------------------------
# A2: scansioni con un po' di testo digitale
# ------------------------------------------------------------

def _scansione(testo, margine=None):
    """Pagina-immagine; `margine` aggiunge una riga di testo vero."""
    bozza = fitz.open()
    pb = bozza.new_page()
    pb.insert_text((72, 150), testo, fontsize=14)
    pix = pb.get_pixmap(dpi=200)
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_image(pagina.rect, pixmap=pix)
    if margine:
        pagina.insert_text((72, 820), margine, fontsize=8)
    return doc


@serve_ocr
def test_scansione_con_testo_a_margine_passa_dall_ocr():
    doc = _scansione(
        "Il sig. Ermenegildo Zanfretta abita a Rovereto.",
        margine="Copia conforme all'originale informatico depositato nel fascicolo telematico - pag. 1 di 1",
    )
    esito, out = _esegui(doc)
    assert esito.avvisi["pagine_ocr"] == [1]
    letto = _ocr(out[0]).lower()
    assert "zanfretta" not in letto and "ermenegildo" not in letto
    assert not _nei_byte(out, COGNOME)


def test_pagina_digitale_con_immagine_di_sfondo_resta_testuale():
    """Costo della regola: una pagina con molto testo sopra un'immagine
    grande (carta intestata, filigrana) non deve finire all'OCR."""
    from PIL import Image
    sfondo = io.BytesIO()
    Image.new("RGB", (400, 560), (245, 245, 235)).save(sfondo, "PNG")
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_image(pagina.rect, stream=sfondo.getvalue())
    riga = "Il convenuto Ermenegildo Zanfretta ha depositato memoria difensiva nei termini di legge."
    for i in range(30):
        pagina.insert_text((60, 80 + i * 22), riga, fontsize=11)
    esito, out = _esegui(doc)
    assert esito.avvisi["pagine_ocr"] == []
    assert COGNOME not in _testo(out)
    assert "memoria difensiva" in _testo(out)   # testo ancora selezionabile


def test_immagine_piccola_non_letta_viene_segnalata():
    from PIL import Image, ImageDraw
    timbro = Image.new("RGB", (600, 80), "white")
    ImageDraw.Draw(timbro).text((10, 30), "timbro", fill="black")
    b = io.BytesIO()
    timbro.save(b, "PNG")
    doc, pagina = _pagina()
    pagina.insert_image(fitz.Rect(72, 560, 372, 600), stream=b.getvalue())   # 2,4% della pagina
    esito, _ = _esegui(doc)
    assert esito.avvisi["pagine_immagini_non_lette"] == [1]


# ------------------------------------------------------------
# C1: le righe vicine restano intatte
# ------------------------------------------------------------

def test_interlinea_stretta_non_cancella_le_righe_vicine():
    doc = fitz.open()
    pagina = doc.new_page()
    righe = [
        "Con ricorso depositato in cancelleria il ricorrente chiedeva",
        "la condanna di Ermenegildo Zanfretta al risarcimento dei danni",
        "patiti in conseguenza del sinistro stradale occorso in citta'.",
    ]
    for i, riga in enumerate(righe):
        pagina.insert_text((72, 100 + i * 9.5), riga, fontsize=12)   # interlinea < altezza
    parole_prima = [w[4] for w in pagina.get_text("words")]
    _, out = _esegui(doc)
    parole_dopo = [w[4] for w in out[0].get_text("words")]
    attese = [p for p in parole_prima if p not in (NOME, COGNOME)]
    assert parole_dopo == attese, "parole non sensibili perse o mutilate"


def test_riquadro_nero_a_piena_altezza():
    """La rimozione usa una fascia stretta, ma il riquadro disegnato deve
    coprire tutta l'altezza della parola."""
    doc, pagina = _pagina()
    rett = next(fitz.Rect(w[:4]) for w in pagina.get_text("words") if w[4] == COGNOME)
    _, out = _esegui(doc)
    pix = out[0].get_pixmap(dpi=144, clip=rett)
    scuri = sum(1 for i in range(0, len(pix.samples), pix.n) if pix.samples[i] < 60)
    assert scuri / (pix.width * pix.height) > 0.75


@serve_ocr
def test_pixel_dell_immagine_sotto_il_riquadro_cancellati():
    """Scansione con strato di testo: sotto il riquadro non devono
    restare pezzi di lettere nell'immagine incorporata."""
    import pytesseract
    from PIL import Image
    righe = ["Verbale di udienza del tribunale ordinario, sezione civile, ruolo generale."] * 24
    righe[5] = "Il sig. Ermenegildo Zanfretta abita a Rovereto da molti anni e lavora in zona."
    bozza = fitz.open()
    pb = bozza.new_page()
    for i, riga in enumerate(righe):
        pb.insert_text((60, 80 + i * 28), riga, fontsize=13)
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_image(pagina.rect, pixmap=pb.get_pixmap(dpi=200))
    for i, riga in enumerate(righe):                      # strato OCR invisibile
        pagina.insert_text((60, 80 + i * 28), riga, fontsize=13, render_mode=3)
    esito, out = _esegui(doc)
    assert esito.avvisi["pagine_ocr"] == []          # resta una pagina testuale
    info = out[0].get_images(full=True)
    assert info, "l'immagine della scansione deve restare"
    img = Image.open(io.BytesIO(fitz.Pixmap(out, info[0][0]).tobytes("png")))
    letto = pytesseract.image_to_string(img).lower()
    assert "zanfretta" not in letto and "ermenegildo" not in letto
    assert "rovereto" in letto


@serve_ocr
def test_scansione_con_poco_testo_nello_strato_va_all_ocr():
    """Uno strato di testo che copre pochissimo della scansione non basta
    a fidarsi: la pagina viene riletta con l'OCR."""
    testo = "Il sig. Ermenegildo Zanfretta abita a Rovereto."
    doc = _scansione(testo)
    doc[0].insert_text((72, 150), testo, fontsize=14, render_mode=3)
    esito, out = _esegui(doc)
    assert esito.avvisi["pagine_ocr"] == [1]
    assert "zanfretta" not in _ocr(out[0]).lower()


# ------------------------------------------------------------
# C3: la pulizia di JavaScript non tocca oggetti innocenti
# ------------------------------------------------------------

def test_carattere_con_JS_nel_nome_non_viene_azzerato():
    doc, pagina = _pagina("Testo di prova con parole normali da leggere.")
    font = pagina.get_fonts()[0][0]
    doc.xref_set_key(font, "BaseFont", "/JSABCD+Helvetica")
    copia = fitz.open(stream=doc.tobytes(), filetype="pdf")
    stat = app.sanitize_pdf_objects(copia)
    assert stat["javascript"] == 0
    assert "BaseFont" in copia.xref_object(font)


# ------------------------------------------------------------
# A8 / A9: cosa finisce nei file scaricati
# ------------------------------------------------------------

def _risultato(nome, modo="codes"):
    return {
        "redaction_mode": modo, "source_name": nome, "output_bytes": b"%PDF-1.7",
        "mapping": [{"Codice": "PER-01", "Tipo": "PERSON",
                     "Testo originale": "Zanfretta", "Occorrenze": 1}],
        "log": [{"Pagina": 1, "Tipo": "PERSON", "Testo": "Ermenegildo Zanfretta"}],
    }


def test_lo_zip_non_contiene_la_tabella_di_accoppiamento():
    import zipfile
    zip_bytes = app.build_results_zip([_risultato("atto.pdf")], shared_mapping=None)
    nomi = zipfile.ZipFile(io.BytesIO(zip_bytes)).namelist()
    assert nomi == ["pseudonimizzato_atto.pdf"]


def test_nome_del_file_neutro_se_contiene_un_dato_oscurato():
    r = _risultato("Ricorso Zanfretta c Bragadin.pdf", modo="blackout")
    assert app.nome_file_uscita(r, 1) == "anonimizzato_documento_1.pdf"


def test_nome_del_file_conservato_se_non_contiene_dati_oscurati():
    r = _risultato("ricorso_2024_bozza.pdf", modo="blackout")
    assert app.nome_file_uscita(r, 1) == "anonimizzato_ricorso_2024_bozza.pdf"


# ------------------------------------------------------------
# PDF che non si possono aprire
# ------------------------------------------------------------

def test_pdf_con_password_da_un_errore_chiaro():
    doc, _ = _pagina()
    cifrato = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="segreta", owner_pw="x")
    with pytest.raises(app.DocumentoNonElaborabile):
        redact_pdf(cifrato, ENTITA, [], AnalizzatoreFinto())
