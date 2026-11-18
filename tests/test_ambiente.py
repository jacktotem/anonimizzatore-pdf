"""
L'app non fa chiamate di rete durante l'analisi e non lascia in giro i
file temporanei dell'OCR (audit del 17 novembre 2026, D5).
"""
import os
import socket
import tempfile
import time

import pytest

import app


def test_elenco_dei_suffissi_senza_rete_e_senza_cache():
    import tldextract
    assert isinstance(tldextract.extract, tldextract.TLDExtract)
    assert tuple(tldextract.extract.suffix_list_urls) == ()
    assert tldextract.extract.cache_dir is None if hasattr(tldextract.extract, "cache_dir") else True


def test_riconoscitore_email_funziona_con_la_rete_bloccata(monkeypatch):
    from presidio_analyzer.predefined_recognizers import EmailRecognizer

    def niente_rete(*a, **k):
        raise OSError("rete bloccata dal test")

    monkeypatch.setattr(socket.socket, "connect", niente_rete)
    monkeypatch.setattr(socket, "create_connection", niente_rete)
    testo = "scrivere a ermenegildo.zanfretta@esempio.it per informazioni"
    trovati = EmailRecognizer(supported_language="it").analyze(testo, ["EMAIL_ADDRESS"])
    assert [testo[r.start:r.end] for r in trovati] == ["ermenegildo.zanfretta@esempio.it"]


def test_cartella_temporanea_dedicata_e_ripulita(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    cartella = app._use_private_temp_dir()
    try:
        assert cartella and os.path.isdir(cartella)
        assert os.path.dirname(cartella) == str(tmp_path)
        assert tempfile.gettempdir() == cartella
        vecchio = os.path.join(cartella, "tess_vecchio.PNG")
        recente = os.path.join(cartella, "tess_recente.PNG")
        for f in (vecchio, recente):
            open(f, "wb").close()
        ieri = time.time() - 86400
        os.utime(vecchio, (ieri, ieri))
        # un secondo avvio: toglie i residui vecchi, non i file in uso
        assert app._use_private_temp_dir() == cartella
        assert not os.path.exists(vecchio)
        assert os.path.exists(recente)
    finally:
        tempfile.tempdir = None


def test_avviso_se_l_ocr_non_ha_l_italiano():
    livelli = [livello for livello, _ in app.messaggi_avvisi({"ocr_senza_italiano": True})]
    assert livelli == ["error"]
    assert app.messaggi_avvisi({"ocr_senza_italiano": False, "pagine_ocr": [1]}) == []
