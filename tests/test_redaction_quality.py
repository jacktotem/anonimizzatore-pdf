"""
Regression guard per la release 1.2.0 (qualità del rilevamento).

Copre i tre bug osservati su provvedimenti reali:
- R-01: falsi positivi NER ("Firmato Da", "Numero", "SE'") redatti;
- R-02: search_for oscurava sottostringhe dentro altre parole
  ("se" → "sentenza", "spese", "pretese");
- R-03: nomi con cognomi rari ("Cabalisti Marco") mancati dal NER
  ma riconoscibili dal contesto legale ("(C.F. ...)", titoli).

Nessun test qui richiede spaCy/modello italiano: si testano gli helper
deterministici e la redazione posizionale con risultati sintetici.
"""
import fitz
import pytest
from presidio_analyzer import RecognizerResult

from app import (
    ItLegalNameRecognizer,
    apply_text_redactions,
    build_word_map,
    collect_person_tokens,
    find_custom_term_matches,
    is_false_positive,
    shrink_redact_rect,
)


# ------------------------------------------------------------
# R-01: filtro falsi positivi
# ------------------------------------------------------------

@pytest.mark.parametrize("entity_type,text", [
    ("PERSON", "Firmato Da"),
    ("PERSON", "Emesso Da"),
    ("PERSON", "Numero"),
    ("DATE_TIME", "Data"),
    ("LOCATION", "SE’"),
    ("LOCATION", "CAUSA"),
    ("LOCATION", "S"),
    ("LOCATION", "N T E N Z A"),   # intestazione "S E N T E N Z A" spaziata
    ("PERSON", "Ordinanza Interlocutoria"),
    ("PERSON", "R.G."),
    ("LOCATION", "C.F."),
])
def test_falsi_positivi_scartati(entity_type, text):
    assert is_false_positive(entity_type, text) is True


@pytest.mark.parametrize("entity_type,text", [
    ("PERSON", "Cabalisti Marco"),
    ("PERSON", "Maria Celeste Arbia"),
    ("PERSON", "Elena Rossi Consigliere"),  # nome + ruolo: va tenuto
    ("LOCATION", "Venezia"),
])
def test_entita_vere_non_scartate(entity_type, text):
    assert is_false_positive(entity_type, text) is False


def test_entita_pattern_mai_filtrate():
    # Le entità deterministiche non passano MAI dal filtro,
    # nemmeno con testi corti o strani.
    assert is_false_positive("IT_FISCAL_CODE", "SE") is False
    assert is_false_positive("IBAN_CODE", "IT") is False


# ------------------------------------------------------------
# R-03: recognizer nomi in contesto legale
# ------------------------------------------------------------

def _person_spans(text):
    rec = ItLegalNameRecognizer()
    return {text[r.start:r.end] for r in rec.analyze(text, ["PERSON"])}


def test_nome_prima_del_codice_fiscale():
    text = "e contro Cabalisti Marco (C.F. CBLMRC90L07A459F) appellato"
    assert "Cabalisti Marco" in _person_spans(text)


def test_nome_dopo_titolo_avvocato():
    text = "rappresentato e difeso dall’avv. Calogera Cusumano contro"
    assert "Calogera Cusumano" in _person_spans(text)


def test_titolo_con_suffisso_e_ruolo_trimmato():
    # "dott. ssa" e ruolo finale "Presidente" non devono entrare nel nome
    text = "composta da dott. ssa Clotilde Parise Presidente e altri"
    spans = _person_spans(text)
    assert "Clotilde Parise" in spans
    assert all("Presidente" not in s for s in spans)


def test_niente_nome_senza_contesto():
    # Parole qualsiasi non devono produrre match
    assert _person_spans("la sentenza del Tribunale di Verona è confermata") == set()


# ------------------------------------------------------------
# R-02: mappa parole e redazione posizionale
# ------------------------------------------------------------

@pytest.fixture
def pagina_sintetica(tmp_path):
    """Pagina con la frase incriminata: entità 'SE’' + parole con 'se'."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 100),
        "la sentenza sulle spese da CAUSA A SE' imputabile resta base",
        fontsize=11,
    )
    page.insert_text((72, 130), "il sig. Mario Rossi ha vinto", fontsize=11)
    yield doc
    doc.close()


def test_word_map_offsets_coerenti(pagina_sintetica):
    full_text, entries = build_word_map(pagina_sintetica[0])
    for e in entries:
        assert full_text[e["start"]:e["end"]] == e["text"]


def test_redazione_non_tocca_altre_parole(pagina_sintetica):
    """La redazione posizionale oscura solo la parola bersaglio."""
    page = pagina_sintetica[0]
    full_text, entries = build_word_map(page)
    start = full_text.index("imputabile")
    result = RecognizerResult("LOCATION", start, start + len("imputabile"), 0.85)
    analysis = {"full_text": full_text, "entries": entries, "results": [result]}

    apply_text_redactions(page, analysis, [], set(), [], 1)

    text_dopo = page.get_text()
    assert "imputabile" not in text_dopo
    for parola in ("sentenza", "spese", "base", "resta"):
        assert parola in text_dopo, f"parola mutilata: {parola}"


def test_falso_positivo_scartato_anche_in_applicazione(pagina_sintetica):
    """Difesa in profondità: un'entità FP ("SE'") che arrivasse fino
    alla fase di applicazione viene comunque saltata, non redatta."""
    page = pagina_sintetica[0]
    full_text, entries = build_word_map(page)
    start = full_text.index("SE'")
    result = RecognizerResult("LOCATION", start, start + len("SE'"), 0.85)
    analysis = {"full_text": full_text, "entries": entries, "results": [result]}
    log = []

    apply_text_redactions(page, analysis, [], set(), log, 1)

    assert "SE'" in page.get_text()   # non redatto: è un falso positivo
    assert log == []


def test_propagazione_nomi(pagina_sintetica):
    """Un token nome noto ("Rossi") viene oscurato come parola intera."""
    page = pagina_sintetica[0]
    full_text, entries = build_word_map(page)
    analysis = {"full_text": full_text, "entries": entries, "results": []}

    apply_text_redactions(page, analysis, [], {"mario", "rossi"}, [], 1)

    text_dopo = page.get_text()
    assert "Mario" not in text_dopo
    assert "Rossi" not in text_dopo
    # "resta" contiene "res" ma non è un match di parola intera
    assert "resta" in text_dopo


def test_collect_person_tokens_esclude_stopword():
    full_text = "Alonge Antonio contro Istituto Nazionale Lavoro"
    results = [
        RecognizerResult("PERSON", 0, 14, 0.85),               # Alonge Antonio
        RecognizerResult("PERSON", 22, len(full_text), 0.85),  # Istituto ... Lavoro
    ]
    tokens = collect_person_tokens({"full_text": full_text, "results": results})
    assert {"alonge", "antonio"} <= tokens
    assert not {"istituto", "nazionale", "lavoro"} & tokens


def test_termini_personalizzati_parole_intere(pagina_sintetica):
    _, entries = build_word_map(pagina_sintetica[0])
    # "se" matcha SOLO la parola a sé stante "SE'",
    # mai i frammenti dentro "sentenza"/"spese"
    matches = find_custom_term_matches("se", entries)
    matched_words = {entries[i]["text"] for m in matches for i in m}
    assert matched_words == {"SE'"}
    # il nome multi-parola matcha ignorando le maiuscole
    assert len(find_custom_term_matches("mario rossi", entries)) == 1
    # nessun match per termini assenti
    assert find_custom_term_matches("Genertel", entries) == []


def test_shrink_redact_rect_resta_dentro():
    rect = fitz.Rect(10, 10, 60, 22)
    shrunk = shrink_redact_rect(rect)
    assert rect.contains(shrunk)
    assert not shrunk.is_empty


# ------------------------------------------------------------
# R-05: pseudonimizzazione con codici
# ------------------------------------------------------------

from app import CodeAssigner, apply_text_redactions as _apply  # noqa: E402


def test_codici_stessa_stringa_stesso_codice():
    a = CodeAssigner()
    c1 = a.assign("PERSON", "Alonge Antonio")
    c2 = a.assign("PERSON", "ALONGE ANTONIO")   # case-insensitive
    c3 = a.assign("PERSON", "Alonge Antonio,")  # punteggiatura ai bordi
    assert c1 == c2 == c3 == "PER-01"
    assert a.mapping[0]["Occorrenze"] == 3


def test_codici_stringhe_diverse_codici_diversi():
    a = CodeAssigner()
    assert a.assign("PERSON", "Alonge Antonio") == "PER-01"
    assert a.assign("PERSON", "Scardoni Aldo") == "PER-02"
    assert a.assign("IT_FISCAL_CODE", "LNGNTN72T09D514W") == "CF-01"
    assert a.assign("TERMINE PERSONALIZZATO", "ACME S.p.A.") == "TERM-01"


def test_codici_token_propagato_riusa_codice_persona():
    a = CodeAssigner()
    a.assign("PERSON", "Alonge Antonio")
    # il solo cognome appartiene a una sola persona -> stesso codice
    assert a.assign("PERSON (propagato)", "Alonge") == "PER-01"


def test_codici_token_ambiguo_codice_nuovo():
    a = CodeAssigner()
    a.assign("PERSON", "Criniti Francesco")
    a.assign("PERSON", "Criniti Luisa")
    # "Criniti" appartiene a due persone: attribuzione ambigua -> codice nuovo
    assert a.assign("PERSON (propagato)", "Criniti") == "PER-03"


def test_pseudonimizzazione_sostituisce_con_codice(pagina_sintetica):
    page = pagina_sintetica[0]
    full_text, entries = build_word_map(page)
    start = full_text.index("Mario Rossi")
    result = RecognizerResult("PERSON", start, start + len("Mario Rossi"), 0.85)
    analysis = {"full_text": full_text, "entries": entries, "results": [result]}
    assigner = CodeAssigner()
    log = []

    _apply(page, analysis, [], set(), log, 1,
           redaction_mode="codes", assigner=assigner)

    text_dopo = page.get_text()
    assert "Mario" not in text_dopo and "Rossi" not in text_dopo
    assert "[PER-01]" in text_dopo
    # il resto della pagina è intatto
    for parola in ("sentenza", "spese", "base"):
        assert parola in text_dopo
    # log e tabella coerenti
    assert log[0]["Codice"] == "PER-01"
    assert assigner.mapping == [{
        "Codice": "PER-01", "Tipo": "PERSON",
        "Testo originale": "Mario Rossi", "Occorrenze": 1,
    }]


def test_blackout_resta_default(pagina_sintetica):
    """In modalità blackout nessun codice appare nel PDF né nel log."""
    page = pagina_sintetica[0]
    full_text, entries = build_word_map(page)
    start = full_text.index("Mario Rossi")
    result = RecognizerResult("PERSON", start, start + len("Mario Rossi"), 0.85)
    analysis = {"full_text": full_text, "entries": entries, "results": [result]}
    log = []

    _apply(page, analysis, [], set(), log, 1)

    text_dopo = page.get_text()
    assert "Mario" not in text_dopo
    assert "[PER-" not in text_dopo
    assert "Codice" not in log[0]


# ------------------------------------------------------------
# R-06: verifica aggiornamenti (parsing versioni)
# ------------------------------------------------------------

from app import parse_version as _parse_version  # noqa: E402


@pytest.mark.parametrize("tag,expected", [
    ("v1.4.0", (1, 4, 0)),
    ("1.4.0", (1, 4, 0)),
    ("v1.3.2", (1, 3, 2)),
    ("v2.0", (2, 0)),
    ("1.10.3", (1, 10, 3)),
    ("", ()),
    ("beta", ()),
])
def test_parse_version(tag, expected):
    assert _parse_version(tag) == expected


def test_parse_version_confronto_numerico():
    # 1.10.0 > 1.9.0 (confronto numerico, non lessicografico)
    assert _parse_version("v1.10.0") > _parse_version("v1.9.0")
    assert _parse_version("v1.4.0") > _parse_version("v1.3.2")
    assert _parse_version("v1.4.0") == _parse_version("1.4.0")
