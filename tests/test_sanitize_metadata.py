"""Verifica la claim di azzeramento metadata nell'advisory di sicurezza."""
import fitz

from app import sanitize_pdf_metadata


def test_metadata_fields_blank_after_sanitize(fixtures_dir):
    doc = fitz.open(fixtures_dir / "plain.pdf")
    doc.set_metadata({
        "author": "Mario Rossi",
        "title": "Bilancio riservato",
        "subject": "Confidenziale",
        "keywords": "rossi, bilancio",
        "creator": "WordPerfect",
        "producer": "Anonimizzatore PDF",
    })
    sanitize_pdf_metadata(doc)
    md = doc.metadata or {}
    for field in ("author", "title", "subject", "keywords", "creator", "producer"):
        assert not md.get(field), (
            f"metadata.{field} dovrebbe essere vuoto, valore: {md.get(field)!r}"
        )
    doc.close()
