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


# ------------------------------------------------------------
# R-07/R-08: abbreviazioni, romani, date-telefono, trim, citazioni
# ------------------------------------------------------------

from app import is_case_citation, trim_ner_span  # noqa: E402


@pytest.mark.parametrize("entity_type,text", [
    ("PERSON", "Cass"),
    ("PERSON", "Sez"),
    ("PERSON", "III"),                 # numero romano
    ("PERSON", "XVI"),
    ("LOCATION", "civ"),
    ("LOCATION", "P.q.m"),
    ("LOCATION", "Stato"),
    ("LOCATION", "Vero"),
    ("LOCATION", "Corte di Lussemburgo"),
    ("PERSON", "Illustrissimi Signori Magistrati"),
    ("PHONE_NUMBER", "3.9.2009"),      # data, non telefono
    ("PHONE_NUMBER", "03/09/2009"),
])
def test_falsi_positivi_r07(entity_type, text):
    assert is_false_positive(entity_type, text) is True


def test_telefono_vero_non_filtrato():
    assert is_false_positive("PHONE_NUMBER", "+39 3201234567") is False


def test_trim_bordi_entita():
    text = "Firmato Da: FRASCA Emesso Da: TRUSTPRO"
    start, end = text.index("FRASCA"), text.index("FRASCA") + len("FRASCA Emesso Da:")
    assert text[slice(*trim_ner_span(text, start, end))] == "FRASCA"

    text2 = "dott. Raffaele Frasca - Presidente dott."
    s2 = text2.index("Raffaele")
    assert text2[slice(*trim_ner_span(text2, s2, len(text2)))] == "Raffaele Frasca"

    # entità fatta SOLO di boilerplate → None
    text3 = "Emesso Da Numero"
    assert trim_ner_span(text3, 0, len(text3)) is None


def test_citazioni_giurisprudenziali_riconosciute():
    t = "come affermato in sent. 30 settembre 2003, Köbler, C-224/01, punto 3"
    s = t.index("Köbler")
    assert is_case_citation(t, s, s + len("Köbler")) is True

    t2 = "nel caso Farrell c. Whitty la Corte ha stabilito"
    s2 = t2.index("Farrell")
    assert is_case_citation(t2, s2, s2 + len("Farrell c. Whitty")) is True

    # un nome comune senza contesto di citazione NON è una citazione
    t3 = "il ricorrente Mario Rossi ha depositato memoria"
    s3 = t3.index("Mario")
    assert is_case_citation(t3, s3, s3 + len("Mario Rossi")) is False


# ------------------------------------------------------------
# R-09: stessa persona, ordine nome/cognome diverso → stesso codice
# ------------------------------------------------------------

def test_codici_ordine_nome_cognome_unificato():
    a = CodeAssigner()
    c1 = a.assign("PERSON", "Criniti Francesco")   # epigrafe
    c2 = a.assign("PERSON", "Francesco Criniti")   # corpo del provvedimento
    assert c1 == c2 == "PER-01"
    assert a.mapping[0]["Occorrenze"] == 2

    # anche con tre token
    c3 = a.assign("PERSON", "Iorno Maria Saletta")
    c4 = a.assign("PERSON", "Maria Saletta Iorno")
    assert c3 == c4 == "PER-02"


def test_codici_persone_diverse_restano_distinte():
    a = CodeAssigner()
    assert a.assign("PERSON", "Criniti Francesco") == "PER-01"
    assert a.assign("PERSON", "Criniti Luisa") == "PER-02"
    assert a.assign("PERSON", "Spezzano Francesco") == "PER-03"
    # il solo "Criniti" è ambiguo tra più persone → codice proprio
    assert a.assign("PERSON (propagato)", "Criniti") == "PER-04"


def test_codici_ordine_non_applicato_alle_location():
    a = CodeAssigner()
    c1 = a.assign("LOCATION", "Reggio Calabria")
    c2 = a.assign("LOCATION", "Calabria Reggio")
    assert c1 != c2  # solo le persone sono order-insensitive


# ------------------------------------------------------------
# R-10: esclusione magistrati (opzionale)
# ------------------------------------------------------------

from app import collect_magistrate_tokens, is_magistrate  # noqa: E402

_EPIGRAFE = (
    "composta dai magistrati: dott. Raffaele Frasca - Presidente "
    "dott. Marco Rossetti - Consigliere rel. "
    "dott. ssa Anna Moscarini - Consigliere "
    "udita la relazione svolta dal Consigliere relatore dott. Marco Rossetti "
    "Firmato Da: RAFFAELE GAETANO ANTONIO FRASCA Emesso Da: TRUSTPRO QUALIFIED"
)


def test_collect_magistrate_tokens_dai_contesti():
    toks = collect_magistrate_tokens(_EPIGRAFE)
    assert {"frasca", "raffaele", "rossetti", "marco", "moscarini", "anna"} <= toks
    # i ruoli e l'ente certificatore non entrano nel set
    assert not {"presidente", "consigliere", "trustpro"} & toks


def test_is_magistrate_solo_se_tutti_i_token_sono_noti():
    toks = collect_magistrate_tokens(_EPIGRAFE)
    assert is_magistrate("Marco Rossetti", toks) is True
    assert is_magistrate("RAFFAELE GAETANO ANTONIO FRASCA", toks) is True
    # una parte non è mai magistrato
    assert is_magistrate("Criniti Francesco", toks) is False
    # nome misto (un token ignoto) → si redige: prevale la protezione
    assert is_magistrate("Marco Bianchi", toks) is False
    # set vuoto → nessuno è magistrato
    assert is_magistrate("Marco Rossetti", set()) is False


def test_nome_senza_contesto_non_e_magistrato():
    toks = collect_magistrate_tokens("il sig. Mario Rossi ha depositato ricorso")
    assert toks == set()


# ------------------------------------------------------------
# R-11: targhe di veicoli italiane
# ------------------------------------------------------------

from app import build_license_plate_recognizer  # noqa: E402


def _plates(text):
    rec = build_license_plate_recognizer()
    return {text[r.start:r.end] for r in rec.analyze(text, ["IT_LICENSE_PLATE"])}


@pytest.mark.parametrize("text,expected", [
    ("l'autovettura targata DR 456 EN di proprietà del convenuto", "DR 456 EN"),
    ("il veicolo DR456EN tamponava", "DR456EN"),
    ("la vettura DR-456-EN", "DR-456-EN"),
])
def test_targa_rilevata(text, expected):
    assert expected in _plates(text)


@pytest.mark.parametrize("text", [
    "procedimento R.G. 17354/21 pendente",   # numero di registro
    "iscritta al n. 465 del ruolo generale",  # numeri di ruolo
    "AI 123 BO",   # lettere fuori alfabeto targhe (I, O)
    "QU 456 OI",   # idem (Q, U, O, I)
    "art. 183 c.p.c. comma sesto",
])
def test_targa_non_confusa(text):
    assert _plates(text) == set()


def test_targa_codice_pseudonimizzazione():
    a = CodeAssigner()
    assert a.assign("IT_LICENSE_PLATE", "DR 456 EN") == "TARGA-01"
    # normalizzazione: con/senza spazi è la stessa targa? No: token diversi
    # ("DR 456 EN" vs "DR456EN") — comportamento documentato, occorrenze
    # separate solo se scritte diversamente nel documento
    assert a.assign("IT_LICENSE_PLATE", "DR 456 EN") == "TARGA-01"


# ------------------------------------------------------------
# R-12: targhe moto, estere e di qualsiasi formato, via contesto
# ------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    # moto e ciclomotori italiani (formati diversi dall'auto)
    ("il motociclo targato AB 12345 procedeva", "AB 12345"),
    ("targa AB12345", "AB12345"),
    ("il ciclomotore targato X9A9B", "X9A9B"),
    ("il rimorchio targato XA 123 AB", "XA 123 AB"),
    # targhe estere
    ("l'autovettura targata M-AB 1234 immatricolata in Germania", "M-AB 1234"),
    ("il veicolo targato AB-123-CD", "AB-123-CD"),
    ("auto targata WA 12345", "WA 12345"),
    # varianti della parola-spia
    ("targa n. AB 12345 di proprietà", "AB 12345"),
    ("veicoli targati GG 999 HH nel sinistro", "GG 999 HH"),
])
def test_targa_da_contesto(text, expected):
    assert expected in _plates(text)


def test_targa_plurale_due_veicoli():
    assert _plates("le auto targate DR 456 EN e FK 833 XT") == {"DR 456 EN", "FK 833 XT"}


@pytest.mark.parametrize("text", [
    # la parola-spia c'è ma NON segue una targa
    "l'autovettura targata Fiat Panda di colore rosso",
    "il veicolo iscritto al PRA in data odierna",
    "il veicolo di proprietà del convenuto",
    # formati ambigui SENZA parola-spia: non si redigono
    "nel procedimento RG 17354 pendente",
    "protocollo AB 12345 del registro",
])
def test_targa_contesto_niente_falsi_positivi(text):
    assert _plates(text) == set()


def test_targa_non_duplicata_se_doppio_match():
    """Formato auto + parola-spia non devono produrre due entità sovrapposte."""
    rec = build_license_plate_recognizer()
    text = "l'autovettura targata DR 456 EN di proprietà"
    results = rec.analyze(text, ["IT_LICENSE_PLATE"])
    assert len(results) == 1
    assert text[results[0].start:results[0].end] == "DR 456 EN"


# ------------------------------------------------------------
# R-13: fix dal CSV del ricorso (contatti, ruolo/anno, città, trim)
# ------------------------------------------------------------

from app import retype_city_as_location  # noqa: E402


@pytest.mark.parametrize("entity_type,text", [
    ("LOCATION", "Tel"),
    ("LOCATION", "P.IVA"),
    ("LOCATION", "Trib"),
    ("LOCATION", "Autorità Giudiziaria"),
    ("LOCATION", "Foro"),
    ("PHONE_NUMBER", "3 26972/2008"),   # numero di ruolo, non telefono
    ("PHONE_NUMBER", "12908/2004"),
])
def test_falsi_positivi_r13(entity_type, text):
    assert is_false_positive(entity_type, text) is True


def test_telefono_vecchio_stile_con_slash_resta_valido():
    # "02/3288652" è un telefono: lo slash non è seguito da un anno
    assert is_false_positive("PHONE_NUMBER", "02/3288652") is False
    assert is_false_positive("PHONE_NUMBER", "02.3288652") is False


def test_trim_rimuove_punteggiatura_ai_bordi():
    text = "residente in Milano, dal 2010"
    s = text.index("Milano,")
    span = trim_ner_span(text, s, s + len("Milano,"))
    assert text[slice(*span)] == "Milano"


def test_trim_ruolo_patrocinante():
    text = "C.F.: FRRSFN65B10F205X Patrocinante in Cassazione"
    s = text.index("FRRSFN65B10F205X")
    span = trim_ner_span(text, s, s + len("FRRSFN65B10F205X Patrocinante"))
    assert text[slice(*span)] == "FRRSFN65B10F205X"


def test_trim_nome_con_via_appiccicata():
    text = "Studio Legale Avv. Stefano Carlo Ferrari Via Stelvio 19"
    s = text.index("Stefano")
    span = trim_ner_span(text, s, s + len("Stefano Carlo Ferrari Via"))
    assert text[slice(*span)] == "Stefano Carlo Ferrari"


@pytest.mark.parametrize("text,expected", [
    ("Milano", "LOCATION"),
    ("San Martino", "LOCATION"),
    ("Reggio Calabria", "LOCATION"),
    ("Sant'Angelo", "LOCATION"),
    ("Mario Rossi", "PERSON"),          # una persona resta persona
    ("Milano Rossi", "PERSON"),         # cognome+nome ambiguo: prudenza
])
def test_retype_citta(text, expected):
    assert retype_city_as_location("PERSON", text) == expected


def test_citazioni_nazionali_riconosciute():
    t = "Cass., n. 12908/2004; Trib. Bari, 25.05.2005; Trib. Pordenone, n. 806"
    for nome in ("Bari", "Pordenone"):
        s = t.index(nome)
        assert is_case_citation(t, s, s + len(nome)) is True
    # una residenza non è una citazione
    t2 = "il convenuto, residente in Bari alla via Roma 1, ha eccepito"
    s2 = t2.index("Bari")
    assert is_case_citation(t2, s2, s2 + len("Bari")) is False


# ------------------------------------------------------------
# R-14: fix dal CSV della comparsa (società, veicoli, onorifici)
# ------------------------------------------------------------

from app import (  # noqa: E402
    is_vehicle_description,
    retype_company_as_org,
)


@pytest.mark.parametrize("entity_type,text", [
    ("PERSON", "l'Ill.mo"),
    ("PERSON", "Premessa"),
    ("PERSON", "Assicurato"),
    ("LOCATION", "targata"),
    ("PHONE_NUMBER", "16990"),          # massima di Cassazione, non telefono
])
def test_falsi_positivi_r14(entity_type, text):
    assert is_false_positive(entity_type, text) is True


def test_telefono_lungo_senza_separatori_resta_valido():
    assert is_false_positive("PHONE_NUMBER", "3201234567") is False


def test_trim_contro_in_testa():
    text = "Contro RONCHETTI ELENA rappresentata"
    span = trim_ner_span(text, 0, len("Contro RONCHETTI ELENA"))
    assert text[slice(*span)] == "RONCHETTI ELENA"


def test_trim_conserva_piazza_in_testa():
    text = "con sede in Trento, Piazza delle Donne Lavoratrici n. 2"
    s = text.index("Piazza")
    span = trim_ner_span(text, s, s + len("Piazza delle Donne Lavoratrici"))
    assert text[slice(*span)] == "Piazza delle Donne Lavoratrici"
    # ...ma "Via" in coda a un nome viene ancora rimossa
    t2 = "Avv. Stefano Carlo Ferrari Via Stelvio"
    s2 = t2.index("Stefano")
    span2 = trim_ner_span(t2, s2, s2 + len("Stefano Carlo Ferrari Via"))
    assert t2[slice(*span2)] == "Stefano Carlo Ferrari"


@pytest.mark.parametrize("text,following,expected", [
    ("ITAS", "Mutua per ivi sentir", "ORGANIZATION"),
    ("CARROZZERIA MODERNA", "S.N.C. (P.IVA", "ORGANIZATION"),
    ("MODERNA", "S.N.C.", "ORGANIZATION"),
    ("Genertel s.p.a.", "", "ORGANIZATION"),
    ("Ronchetti Elena", "ed ITAS Mutua", "PERSON"),   # una persona resta tale
])
def test_retype_societa(text, following, expected):
    assert retype_company_as_org("PERSON", text, following) == expected


def test_veicolo_descrizione_non_redatta():
    t = "danni causati all'automezzo Jeep Compass in sosta"
    s = t.index("Jeep")
    assert is_vehicle_description(t, s) is True
    # ma il proprietario NON è una descrizione di veicolo
    t2 = "la vettura del sig. Ciullo Fabio parcheggiata"
    s2 = t2.index("Ciullo")
    assert is_vehicle_description(t2, s2) is False


def test_targa_congiunzione_vagante():
    # "targate X e FP185GN": la "e" non entra nella targa
    assert "FP185GN" in _plates("le vetture targate e FP185GN in colonna")
    assert "EFP185GN" not in _plates("le vetture targate e FP185GN in colonna")


def test_collect_org_tokens_da_coppie_di_parole():
    """La coppia "ITAS Mutua" nel testo semplice basta a identificare
    la società, anche senza entità NER."""
    from app import collect_org_tokens
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "conveniva in giudizio ITAS Mutua e la", fontsize=11)
    page.insert_text((72, 120), "CARROZZERIA MODERNA S.N.C. nonche' detta societa'", fontsize=11)
    full_text, entries = build_word_map(page)
    doc.close()
    toks = collect_org_tokens({"full_text": full_text, "entries": entries, "results": []})
    assert "itas" in toks
    assert "moderna" in toks
    # "detta" (davanti a "società") non è un nome di società
    assert "detta" not in toks


def test_propagazione_org_distinta_dalle_persone(pagina_sintetica):
    """Un token di società propagato riceve tipo e codice ORG."""
    page = pagina_sintetica[0]
    full_text, entries = build_word_map(page)
    analysis = {"full_text": full_text, "entries": entries, "results": []}
    assigner = CodeAssigner()
    log = []

    _apply(page, analysis, [], {"mario"}, log, 1,
           redaction_mode="codes", assigner=assigner,
           known_org_tokens={"rossi"})   # fingiamo che "Rossi" sia una srl

    tipi = {r["Testo"]: r["Tipo"] for r in log}
    assert tipi["Rossi"] == "ORGANIZATION (propagato)"
    assert tipi["Mario"] == "PERSON (propagato)"
    codici = {r["Testo"]: r["Codice"] for r in log}
    assert codici["Rossi"].startswith("ORG-")
    assert codici["Mario"].startswith("PER-")


# ------------------------------------------------------------
# R-15: lessico medico/assicurativo, ruoli tecnici, intestazioni atto
# ------------------------------------------------------------

@pytest.mark.parametrize("entity_type,text", [
    ("LOCATION", "FRATTURA"),
    ("LOCATION", "SCOPPIO"),
    ("PERSON", "CTU"),
    ("PERSON", "Lucro"),
    ("PERSON", "Polizze"),
    ("PERSON", "Avv.ti"),
])
def test_falsi_positivi_r15(entity_type, text):
    assert is_false_positive(entity_type, text) is True


def test_trim_intestazione_comparsa():
    text = "Giudice Dott. Giulio Scaramuzzino COMPARSA DI COSTITUZIONE"
    s = text.index("Giulio")
    span = trim_ner_span(text, s, s + len("Giulio Scaramuzzino COMPARSA"))
    assert text[slice(*span)] == "Giulio Scaramuzzino"


def test_trim_avvti_in_testa():
    text = "dagli Avv.ti Andrea Girardi (C.F. ..."
    s = text.index("Avv.ti")
    span = trim_ner_span(text, s, s + len("Avv.ti Andrea Girardi"))
    assert text[slice(*span)] == "Andrea Girardi"


def test_propagazione_senza_punteggiatura(pagina_sintetica):
    """'Rossi' propagato da un'occorrenza 'Rossi,' appare pulito nel log."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "il dott. Pieri, accertava i postumi", fontsize=11)
    full_text, entries = build_word_map(page)
    analysis = {"full_text": full_text, "entries": entries, "results": []}
    assigner = CodeAssigner()
    log = []
    _apply(page, analysis, [], {"pieri"}, log, 1,
           redaction_mode="codes", assigner=assigner)
    doc.close()
    assert log[0]["Testo"] == "Pieri"
    assert assigner.mapping[0]["Testo originale"] == "Pieri"


# ------------------------------------------------------------
# R-16: batch multi-documento (codici condivisi, ZIP)
# ------------------------------------------------------------

import zipfile  # noqa: E402
from io import BytesIO  # noqa: E402

from app import build_results_zip, mapping_to_csv_bytes  # noqa: E402


def test_assigner_condiviso_stesso_codice_tra_documenti():
    """La stessa persona in due atti del fascicolo → stesso codice."""
    a = CodeAssigner()
    a.current_document = "ricorso.pdf"
    c1 = a.assign("PERSON", "Mario Rossi")
    a.current_document = "comparsa.pdf"
    c2 = a.assign("PERSON", "Rossi Mario")     # ordine invertito, stesso codice
    c3 = a.assign("PERSON", "Luigi Verdi")
    assert c1 == c2 == "PER-01"
    assert c3 == "PER-02"
    riga = next(r for r in a.mapping if r["Codice"] == "PER-01")
    assert riga["Occorrenze"] == 2
    assert riga["Documenti"] == "ricorso.pdf · comparsa.pdf"


def test_mapping_senza_documenti_se_singolo():
    """Senza current_document la colonna Documenti non compare."""
    a = CodeAssigner()
    a.assign("PERSON", "Mario Rossi")
    assert "Documenti" not in a.mapping[0]


def test_csv_con_colonna_documenti():
    a = CodeAssigner()
    a.current_document = "atto1.pdf"
    a.assign("PERSON", "Mario Rossi")
    csv_bytes = mapping_to_csv_bytes(a.mapping, with_document=True)
    testo = csv_bytes.decode("utf-8-sig")
    assert testo.splitlines()[0] == "Codice;Tipo;Testo originale;Occorrenze;Documenti"
    assert "atto1.pdf" in testo


def test_zip_contiene_pdf_e_tabelle_per_documento():
    risultati = [
        {"output_bytes": b"%PDF-1", "log": [{}], "mapping": [
            {"Codice": "PER-01", "Tipo": "PERSON", "Testo originale": "X", "Occorrenze": 1}],
         "redaction_mode": "codes", "source_name": "uno.pdf"},
        {"output_bytes": b"%PDF-2", "log": [{}], "mapping": [
            {"Codice": "PER-01", "Tipo": "PERSON", "Testo originale": "Y", "Occorrenze": 1}],
         "redaction_mode": "codes", "source_name": "due.pdf"},
    ]
    zf = zipfile.ZipFile(BytesIO(build_results_zip(risultati)))
    nomi = set(zf.namelist())
    assert {"pseudonimizzato_uno.pdf", "pseudonimizzato_due.pdf",
            "accoppiamento_uno.csv", "accoppiamento_due.csv"} == nomi
    assert zf.read("pseudonimizzato_due.pdf") == b"%PDF-2"


def test_zip_con_tabella_condivisa_unica():
    risultati = [
        {"output_bytes": b"%PDF-1", "log": [{}], "mapping": [], "redaction_mode": "codes",
         "source_name": "uno.pdf"},
        {"output_bytes": b"%PDF-2", "log": [{}], "mapping": [], "redaction_mode": "codes",
         "source_name": "due.pdf"},
    ]
    shared = [{"Codice": "PER-01", "Tipo": "PERSON", "Testo originale": "X",
               "Occorrenze": 3, "Documenti": "uno.pdf · due.pdf"}]
    zf = zipfile.ZipFile(BytesIO(build_results_zip(risultati, shared)))
    nomi = set(zf.namelist())
    assert "accoppiamento_fascicolo.csv" in nomi
    # con la tabella condivisa NON ci sono le tabelle per documento
    assert not any(n.startswith("accoppiamento_uno") for n in nomi)


def test_zip_blackout_senza_csv():
    risultati = [{"output_bytes": b"%PDF", "log": [{}], "mapping": [],
                  "redaction_mode": "blackout", "source_name": "atto.pdf"}]
    zf = zipfile.ZipFile(BytesIO(build_results_zip(risultati)))
    assert zf.namelist() == ["anonimizzato_atto.pdf"]


# ------------------------------------------------------------
# R-17: entità ORGANIZATION richiesta a Presidio + trim dedicato
# ------------------------------------------------------------

from app import trim_org_span  # noqa: E402


@pytest.mark.parametrize("text,atteso", [
    # la forma giuridica esce, il nome distintivo resta INTERO
    ("Società MONDI ITALIA SRL", "MONDI ITALIA"),
    ("MONDI ITALIA S.r.l.", "MONDI ITALIA"),
    ("Assicurazioni Esempio S.p.A.", "Esempio"),
    ("CARROZZERIA MODERNA S.N.C.", "MODERNA"),
    ("Banca Findomestic S.p.A.", "Findomestic"),
])
def test_trim_org_conserva_il_nome(text, atteso):
    span = trim_org_span(text, 0, len(text))
    assert text[slice(*span)] == atteso


def test_trim_org_scarta_le_sole_forme_giuridiche():
    """Una forma giuridica senza nome non è un dato da proteggere."""
    for solo_forma in ["Società", "S.r.l.", "S.p.A."]:
        assert trim_org_span(solo_forma, 0, len(solo_forma)) is None
    # "la società": il trim lascia l'articolo, che viene però scartato
    # subito dopo dal filtro falsi positivi (nessun token sostanziale)
    span = trim_org_span("la società", 0, len("la società"))
    residuo = "la società"[slice(*span)] if span else ""
    assert is_false_positive("ORGANIZATION", residuo) is True


def test_trim_org_non_usa_la_stoplist_delle_persone():
    """'Italia' è in stoplist per le persone ma è parte del nome sociale:
    il trim generico lo toglierebbe, quello per le organizzazioni no."""
    t = "Società MONDI ITALIA SRL"
    generico = t[slice(*trim_ner_span(t, 0, len(t)))]
    org = t[slice(*trim_org_span(t, 0, len(t)))]
    assert generico == "MONDI"          # comportamento del trim persone
    assert org == "MONDI ITALIA"        # trim organizzazioni: nome intero


def _org_tokens_da_testo(testo):
    """Esegue collect_org_tokens su una pagina con questo testo."""
    from app import collect_org_tokens
    doc = fitz.open()
    page = doc.new_page()
    for i, riga in enumerate(testo.split("\n")):
        page.insert_text((50, 80 + i * 20), riga, fontsize=10)
    full_text, entries = build_word_map(page)
    doc.close()
    return collect_org_tokens(
        {"full_text": full_text, "entries": entries, "results": []})


def test_ragione_sociale_intera_dalla_forma_giuridica():
    """Il bug segnalato: 'MONDI ITALIA SRL' perdeva 'MONDI' perché il
    vicino di 'SRL' era 'ITALIA', che è in stoplist."""
    toks = _org_tokens_da_testo("nella qualita' di legale rappresentante\n"
                                "della Societa' MONDI ITALIA SRL, con sede")
    assert "mondi" in toks
    assert "italia" in toks


@pytest.mark.parametrize("testo,attesi", [
    ("il contratto con Findomestic Banca S.p.A. del 2018", {"findomestic"}),
    # "Carrozzeria" è genere merceologico (come "Banca"): resta leggibile,
    # viene protetto il nome distintivo
    ("la CARROZZERIA MODERNA S.N.C. ha riparato", {"moderna"}),
    ("conveniva in giudizio ITAS Mutua per sentir", {"itas"}),
])
def test_ragioni_sociali_varie(testo, attesi):
    assert attesi <= _org_tokens_da_testo(testo)


@pytest.mark.parametrize("testo", [
    # senza forma giuridica non si attiva: corti e norme restano intatte
    "la Corte di giustizia dell'Unione Europea ha affermato",
    "come previsto dalla Direttiva 2009/103/CE del Parlamento europeo",
    "il Tribunale di Milano, Sezione Impresa, ha disposto",
    "visto il Codice delle Assicurazioni Private",
])
def test_nessuna_societa_senza_forma_giuridica(testo):
    assert _org_tokens_da_testo(testo) == set()


def test_articoli_e_ruoli_non_entrano_nel_nome():
    toks = _org_tokens_da_testo("citava in giudizio la Spett.le ESEMPIO S.r.l.")
    assert "esempio" in toks
    assert not {"spett", "spettle", "citava"} & toks
