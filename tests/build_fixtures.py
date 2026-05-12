#!/usr/bin/env python3
"""Genera le fixture PDF per la test suite.

Run dalla root del repo:  python tests/build_fixtures.py

Fixtures prodotte in tests/fixtures/:
- plain.pdf:                       PDF minimale solo-testo, senza metadata, senza JS.
- with_js_and_openaction.pdf:      catalog con /OpenAction JavaScript +
                                   /Names/JavaScript entry. Regression guard per #2/#3.
- with_duplicate_attachments.pdf:  due allegati con nome identico.
                                   Regression guard per #4.
"""
from pathlib import Path

import fitz  # PyMuPDF

OUT = Path(__file__).parent / "fixtures"
OUT.mkdir(exist_ok=True)


def build_plain():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello, plain fixture.")
    # Garantisce metadata vuoti
    doc.set_metadata({})
    doc.save(OUT / "plain.pdf")
    doc.close()


def build_with_js():
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "This file carries OpenAction JS.")

    # Crea un xref con JavaScript action
    js_xref = doc.get_new_xref()
    doc.update_object(
        js_xref,
        "<< /S /JavaScript /JS (app.alert('pwned');) >>",
    )

    catalog_xref = doc.pdf_catalog()
    # /OpenAction -> esegue JS all'apertura del documento
    doc.xref_set_key(catalog_xref, "OpenAction", f"{js_xref} 0 R")

    # /Names/JavaScript -> "documenti named JS" raggiungibili via Names tree
    names_xref = doc.get_new_xref()
    doc.update_object(
        names_xref,
        f"<< /JavaScript << /Names [ (boot) {js_xref} 0 R ] >> >>",
    )
    doc.xref_set_key(catalog_xref, "Names", f"{names_xref} 0 R")

    doc.save(OUT / "with_js_and_openaction.pdf")
    doc.close()


def build_with_duplicate_attachments():
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Two attachments named the same.")
    # Nota: il nome usato per l'identità interna PyMuPDF differisce dal
    # filename — passiamo lo stesso filename ad entrambi.
    doc.embfile_add("same1", b"first payload", filename="same.txt")
    doc.embfile_add("same2", b"second payload", filename="same.txt")
    doc.save(OUT / "with_duplicate_attachments.pdf")
    doc.close()


if __name__ == "__main__":
    build_plain()
    build_with_js()
    build_with_duplicate_attachments()
    print(f"Fixtures written to {OUT}")
