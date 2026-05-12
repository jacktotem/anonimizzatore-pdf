"""Regression guards per le issue #2 e #3.

#2: `doc.get_js()` non esisteva in PyMuPDF e l'AttributeError veniva
    ingoiato silenziosamente, quindi il loop xref non veniva mai eseguito.
#3: Anche con il loop attivo, i riferimenti `/Names/JavaScript` e
    `/OpenAction` nel catalog sopravvivevano alla sanitizzazione.
"""
import fitz

from app import sanitize_pdf_objects


def _catalog_text(doc):
    return doc.xref_object(doc.pdf_catalog())


def test_javascript_payload_removed_from_xrefs(fixtures_dir):
    """#2: nessun xref deve contenere il payload JavaScript dopo sanitize."""
    doc = fitz.open(fixtures_dir / "with_js_and_openaction.pdf")
    stats = sanitize_pdf_objects(doc)

    # La funzione DEVE riportare almeno un JS rimosso (prima del fix riportava 0).
    assert stats["javascript"] >= 1, (
        "sanitize_pdf_objects deve riportare js_removed >= 1; "
        f"valore effettivo: {stats['javascript']}. "
        "Se vale 0, il fix di #2 è regredito."
    )

    # Verifica fisica: il payload non deve essere più presente in nessun xref.
    leak_found = False
    for xref in range(1, doc.xref_length()):
        try:
            obj = doc.xref_object(xref)
        except Exception:
            continue
        if "app.alert" in obj:
            leak_found = True
            break
    assert not leak_found, "Payload JS ancora presente in qualche xref"
    doc.close()


def test_catalog_no_javascript_or_openaction(fixtures_dir):
    """#3: catalog non deve riferire /OpenAction né /Names/JavaScript."""
    doc = fitz.open(fixtures_dir / "with_js_and_openaction.pdf")
    sanitize_pdf_objects(doc)

    catalog = _catalog_text(doc)
    assert "/OpenAction" not in catalog, (
        "catalog continua a riferire /OpenAction dopo sanitize"
    )
    assert "/JavaScript" not in catalog, (
        "catalog continua a riferire /JavaScript (via /Names) dopo sanitize"
    )
    doc.close()


def test_plain_pdf_unaffected(fixtures_dir):
    """Sanity check: PDF senza JS deve sopravvivere intatto."""
    doc = fitz.open(fixtures_dir / "plain.pdf")
    stats = sanitize_pdf_objects(doc)
    assert stats["javascript"] == 0
    assert doc.page_count == 1
    doc.close()
