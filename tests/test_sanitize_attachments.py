"""Regression guard per issue #4.

#4: `embfile_del(filename)` cancellava solo la prima occorrenza con quel
    nome — allegati con nomi duplicati (frequenti in PDF prodotti da Acrobat
    o Word export) sopravvivevano silenziosamente.
"""
import fitz

from app import sanitize_pdf_objects


def test_duplicate_attachments_all_removed(fixtures_dir):
    """#4: due allegati con lo stesso filename devono essere entrambi rimossi."""
    doc = fitz.open(fixtures_dir / "with_duplicate_attachments.pdf")
    assert doc.embfile_count() == 2, (
        "fixture corrotta: ci si aspettano 2 allegati di partenza"
    )

    stats = sanitize_pdf_objects(doc)

    assert doc.embfile_count() == 0, (
        f"Allegati ancora presenti dopo sanitize: {doc.embfile_count()}. "
        "Se > 0, il fix di #4 è regredito (probabile uso di embfile_del per nome)."
    )
    assert stats["attachments"] == 2, (
        f"sanitize_pdf_objects deve riportare 2 allegati rimossi; "
        f"valore effettivo: {stats['attachments']}"
    )
    doc.close()


def test_plain_pdf_no_attachments(fixtures_dir):
    """Sanity check: PDF senza allegati non deve riportare false positive."""
    doc = fitz.open(fixtures_dir / "plain.pdf")
    assert doc.embfile_count() == 0
    stats = sanitize_pdf_objects(doc)
    assert stats["attachments"] == 0
    doc.close()
