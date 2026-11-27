"""
Test dell'interfaccia con il banco di prova di Streamlit (AppTest).

Coprono ciò che i test di redact_pdf non possono vedere: che cosa resta
a schermo dopo l'elaborazione. Prima dell'audit del 17 novembre 2026
gli avvisi comparivano un istante e sparivano al primo clic, un PDF
protetto mostrava una traccia dello stack e, cambiando le impostazioni,
restavano visibili i risultati del giro precedente.

Servono il modello italiano di spaCy e una versione di Streamlit il cui
banco di prova sappia caricare file: dove mancano, i test si saltano.
Tutti i dati sono di fantasia.
"""
from pathlib import Path

import fitz
import pytest

pytest.importorskip("it_core_news_lg", reason="modello italiano spaCy non installato")
testing = pytest.importorskip("streamlit.testing.v1")
element_tree = pytest.importorskip("streamlit.testing.v1.element_tree")
if not hasattr(element_tree, "FileUploader"):
    pytest.skip("questa versione di Streamlit non carica file nei test",
                allow_module_level=True)

APP = str(Path(__file__).resolve().parent.parent / "src" / "app.py")
FRASE = "Il sig. Ermenegildo Zanfretta abita a Rovereto da molti anni e lavora in zona."


def _pdf(con_immagine=False, password=None, frase=FRASE):
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_text((72, 90), frase, fontsize=12)
    if con_immagine:
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 300, 40), False)
        pix.clear_with(230)
        pagina.insert_image(fitz.Rect(72, 560, 372, 600), pixmap=pix)   # 2,4% della pagina
    if password:
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw="x")
    return doc.tobytes()


def _avvia(nome, contenuto):
    at = testing.AppTest.from_file(APP, default_timeout=180).run()
    at.file_uploader[0].upload(nome, contenuto, "application/pdf").run()
    bottone = next(b for b in at.button if "Anonimizza" in b.label)
    bottone.click().run()
    return at


def _testi(elementi):
    return " ".join(e.value for e in elementi)


def test_elaborazione_riuscita_mostra_esito_e_download():
    at = _avvia("atto.pdf", _pdf())
    assert not at.exception
    assert "completata" in _testi(at.success)
    assert at.get("download_button"), "manca il pulsante di download"


def test_pdf_protetto_da_password_errore_chiaro_senza_traccia():
    at = _avvia("protetto.pdf", _pdf(password="segreta"))
    assert not at.exception, "nessuna traccia dello stack a schermo"
    assert "password" in _testi(at.error)
    assert not at.get("download_button")


def test_avviso_immagini_resta_dopo_un_altro_giro():
    at = _avvia("atto.pdf", _pdf(con_immagine=True))
    assert "Immagini non lette" in _testi(at.warning)
    at.run()   # come dopo un clic su "Scarica": lo script riparte da capo
    assert "Immagini non lette" in _testi(at.warning)
    assert at.get("download_button")


def test_cambio_impostazioni_invalida_i_risultati():
    at = _avvia("atto.pdf", _pdf())
    assert at.get("download_button")
    casella = next(c for c in at.checkbox if c.label == "Email")
    casella.set_value(False).run()
    assert not at.get("download_button"), "restano i download del giro precedente"
    assert "premi di nuovo" in _testi(at.info)


def test_nome_file_con_dato_oscurato_viene_segnalato():
    at = _avvia("Ricorso Zanfretta.pdf", _pdf())
    assert not at.exception
    assert "documento_1.pdf" in _testi(at.caption)


def test_caricamento_con_stesso_nome_e_dimensione_invalida_i_risultati():
    primo = _pdf()
    secondo = _pdf(frase=FRASE.replace("zona", "sede"))
    dimensione = max(len(primo), len(secondo))
    primo, secondo = primo.ljust(dimensione, b"\n"), secondo.ljust(dimensione, b"\n")
    assert primo != secondo and len(primo) == len(secondo)
    at = _avvia("atto.pdf", primo)
    assert at.get("download_button")

    at.file_uploader[0].set_value(("atto.pdf", secondo, "application/pdf")).run()

    assert not at.exception
    assert not at.get("download_button")
    assert "premi di nuovo" in _testi(at.info)


def test_zip_esclude_i_pdf_con_avvisi_di_analisi():
    at = testing.AppTest.from_file(APP, default_timeout=180).run()
    at.file_uploader[0].set_value([
        ("testuale.pdf", _pdf(), "application/pdf"),
        ("immagini.pdf", _pdf(con_immagine=True), "application/pdf"),
    ]).run()
    next(b for b in at.button if "Anonimizza" in b.label).click().run()

    assert not at.exception
    assert "1 PDF da verificare" in _testi(at.warning)
    assert any("senza avvisi (1, ZIP)" in b.proto.label for b in at.get("download_button"))
