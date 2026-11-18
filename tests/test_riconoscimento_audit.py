"""
Casi di riconoscimento emersi dall'audit del 17 novembre 2026 (gruppo B):
dati veri che i filtri contro i falsi positivi lasciavano in chiaro.

Come negli altri test del riconoscimento non serve spaCy: si provano i
filtri e i riconoscitori a regola. Tutti i dati sono di fantasia.
"""
import fitz
import pytest
from presidio_analyzer import RecognizerResult

import app
from app import (
    ItBirthDateRecognizer,
    ItLegalNameRecognizer,
    build_word_map,
    collect_person_tokens,
    find_custom_term_matches,
    is_case_citation,
    is_false_positive,
    is_vehicle_description,
    trim_ner_span,
)


def _trim(testo, entita):
    s = testo.index(entita)
    span = trim_ner_span(testo, s, s + len(entita))
    return None if span is None else testo[slice(*span)]


def _nomi(testo):
    rec = ItLegalNameRecognizer()
    return {testo[r.start:r.end] for r in rec.analyze(testo, ["PERSON"])}


# ------------------------------------------------------------
# B1: cognomi uguali a parole comuni, cognomi di due lettere
# ------------------------------------------------------------

@pytest.mark.parametrize("testo,entita", [
    ("Sentito il sig. Mario Piazza in udienza.", "Mario Piazza"),
    ("Per l'avv. Giuseppe Giudice si costituisce.", "Giuseppe Giudice"),
    ("La sig.ra Anna Corso non compare.", "Anna Corso"),
    ("La teste Rosa Italiano conferma.", "Rosa Italiano"),
    ("Il sig. Luca Strada, convenuto.", "Luca Strada"),
    ("Il sig. Giovanni Re ha firmato.", "Giovanni Re"),
    ("Il sig. Hu Wei ha tradotto.", "Hu Wei"),
    ("ricorrente MARIO PIAZZA contro", "MARIO PIAZZA"),
])
def test_cognome_parola_comune_resta_nel_nome(testo, entita):
    assert _trim(testo, entita) == entita


@pytest.mark.parametrize("testo,entita,atteso", [
    # prefisso di via incollato al nome: l'indirizzo prosegue
    ("Avv. Sandro Carlo Ferretti Via Garibaldi 19", "Sandro Carlo Ferretti Via", "Sandro Carlo Ferretti"),
    ("il sig. Mario Piazza Dante 3, Trento", "Mario Piazza", "Mario"),
    ("residente Luca Corso Italia 12", "Luca Corso", "Luca"),
    # ruolo dopo nome e cognome: si toglie come prima
    ("Giudice Dott. Giulio Castellani Giudice del Tribunale", "Giulio Castellani Giudice", "Giulio Castellani"),
    ("Firmato Da: BELTRAMI Emesso Da: TRUSTPRO", "BELTRAMI Emesso Da", "BELTRAMI"),
    ("dott. ssa Clotilde Farnesi Presidente e altri", "Clotilde Farnesi Presidente", "Clotilde Farnesi"),
    # parola comune in minuscolo: non e' un cognome
    ("il sig. Mario corso di laurea", "Mario corso", "Mario"),
])
def test_boilerplate_ai_bordi_si_toglie_ancora(testo, entita, atteso):
    assert _trim(testo, entita) == atteso


@pytest.mark.parametrize("testo,atteso", [
    ("Sentito il sig. Mario Piazza in udienza.", "Mario Piazza"),
    ("Per l'avv. Giuseppe Giudice si costituisce.", "Giuseppe Giudice"),
    ("La sig.ra Anna Corso non compare.", "Anna Corso"),
    ("Il sig. Giovanni Re ha firmato.", "Giovanni Re"),
    ("Il teste Rosa Italiano conferma.", "Rosa Italiano"),
])
def test_riconoscitore_a_regola_tiene_il_cognome_parola_comune(testo, atteso):
    assert atteso in _nomi(testo)


def test_riconoscitore_a_regola_toglie_ancora_il_ruolo():
    spans = _nomi("composta da dott. ssa Clotilde Farnesi Presidente e altri")
    assert "Clotilde Farnesi" in spans
    assert all("Presidente" not in s for s in spans)


def test_due_token_corti_sono_un_nome():
    assert is_false_positive("PERSON", "Hu Bo") is False
    # ma i frammenti di sempre restano falsi positivi
    assert is_false_positive("PERSON", "Da Se") is True
    assert is_false_positive("PERSON", "SE'") is True


def test_cognomi_ambigui_segnalati_e_non_propagati():
    testo = "Sentito il sig. Mario Piazza in udienza e il sig. Giovanni Re"
    analisi = {"full_text": testo, "entries": [], "results": [
        RecognizerResult("PERSON", testo.index("Mario"), testo.index("Piazza") + 6, 0.85),
        RecognizerResult("PERSON", testo.index("Giovanni"), len(testo), 0.85),
    ]}
    tokens = collect_person_tokens(analisi)
    assert {"mario", "giovanni"} <= tokens
    # "Piazza" e "Re" da soli coprirebbero ogni piazza e ogni re dell'atto
    assert "piazza" not in tokens and "re" not in tokens
    assert app.collect_ambiguous_surnames(analisi) == {"Piazza", "Re"}


def test_cognome_parola_comune_oscurato_anche_se_il_nome_e_gia_coperto():
    """Due entità sovrapposte ("Giuseppe" e "Giuseppe Giudice"): quando
    alla seconda resta solo "Giudice", quello è il cognome e va oscurato."""
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_text((72, 100), "Per l'avv. Giuseppe Giudice si costituisce in giudizio", fontsize=11)
    testo, voci = build_word_map(pagina)
    i = testo.index("Giuseppe")
    analisi = {"full_text": testo, "entries": voci, "results": [
        RecognizerResult("PERSON", i, i + len("Giuseppe"), 0.85),
        RecognizerResult("PERSON", i, i + len("Giuseppe Giudice"), 0.85),
    ]}
    app.apply_text_redactions(pagina, analisi, [], set(), [], 1)
    dopo = pagina.get_text()
    assert "Giuseppe" not in dopo and "Giudice" not in dopo
    assert "giudizio" in dopo


# ------------------------------------------------------------
# B2: citazioni e veicoli
# ------------------------------------------------------------

@pytest.mark.parametrize("testo,nome", [
    ("Il Giudice autorizza la chiamata in causa di Giovanni Verdolin, residente a Bolzano.", "Giovanni Verdolin"),
    ("Trib. Trento, R.G. 123/2024 - ricorrente Carla Nerozzi", "Carla Nerozzi"),
    ("come da Cass. n. 100/2020, il sig. Mario Rossi ha chiesto", "Mario Rossi"),
])
def test_persona_vicino_a_una_citazione_nazionale_non_e_una_citazione(testo, nome):
    s = testo.index(nome)
    assert is_case_citation(testo, s, s + len(nome), "PERSON") is False


def test_citazioni_vere_restano_riconosciute():
    t = "come affermato in sent. 30 settembre 2003, Köbler, C-224/01, punto 3"
    s = t.index("Köbler")
    assert is_case_citation(t, s, s + 6, "PERSON") is True
    t2 = "nel caso Farrell c. Whitty la Corte ha stabilito"
    s2 = t2.index("Farrell")
    assert is_case_citation(t2, s2, s2 + len("Farrell c. Whitty"), "PERSON") is True
    t3 = "Cass., n. 12908/2004; Trib. Bari, 25.05.2005; Trib. Pordenone, n. 806"
    for citta in ("Bari", "Pordenone"):
        s3 = t3.index(citta)
        assert is_case_citation(t3, s3, s3 + len(citta), "LOCATION") is True


def test_luogo_lontano_dal_marcatore_non_e_una_citazione():
    t = "Trib. Trento, R.G. 123/2024 - il ricorrente, residente a Rovereto in via"
    s = t.index("Rovereto")
    assert is_case_citation(t, s, s + len("Rovereto"), "LOCATION") is False


def test_nome_di_persona_dopo_una_parola_veicolo_non_e_una_marca():
    t = "il conducente dell'autovettura Luigi Bianchetti dichiarava il falso"
    s = t.index("Luigi")
    assert is_vehicle_description(t, s, s + len("Luigi Bianchetti")) is False


@pytest.mark.parametrize("testo,entita", [
    ("danni causati all'automezzo Jeep Compass in sosta", "Jeep Compass"),
    ("alla guida dell'autovettura Fiat Panda di colore rosso", "Fiat Panda"),
    ("il veicolo Punto era fermo", "Punto"),
])
def test_marca_e_modello_restano_esclusi(testo, entita):
    s = testo.index(entita)
    assert is_vehicle_description(testo, s, s + len(entita)) is True


# ------------------------------------------------------------
# B3: date di nascita
# ------------------------------------------------------------

@pytest.mark.parametrize("testo,data", [
    ("Tizio, nato a Roma l'11/08/1975, operaio.", "11/08/1975"),
    ("Caia, nata a Bassano del Grappa il 12/03/1975, impiegata.", "12/03/1975"),
    ("Sempronio, nato a S. Giovanni in Persiceto il 10/01/1980.", "10/01/1980"),
    ("Il sottoscritto nato/a il 05/06/1970 dichiara.", "05/06/1970"),
    ("Data di nascita: 02/02/1982", "02/02/1982"),
    ("Mevio, n. a Trento il 07/07/1977.", "07/07/1977"),
    ("Filano, nato a Bolzano/Bozen il 09/09/1969.", "09/09/1969"),
    ("nata a Borgo Valsugana (TN) il 3 marzo 1975", "3 marzo 1975"),
    ("nato a Trento il 10/01/1980", "10/01/1980"),
])
def test_data_di_nascita_riconosciuta(testo, data):
    rec = ItBirthDateRecognizer()
    trovate = [testo[r.start:r.end] for r in rec.analyze(testo, ["IT_BIRTH_DATE"])]
    assert trovate == [data]


@pytest.mark.parametrize("testo", [
    "sinistro occorso in data 10/01/2019",
    "nato il giorno dopo",
    "n. 5 del 10/01/2019 del registro",
    "udienza del 12/03/2024 alle ore 9",
])
def test_altre_date_non_sono_date_di_nascita(testo):
    assert ItBirthDateRecognizer().analyze(testo, ["IT_BIRTH_DATE"]) == []


# ------------------------------------------------------------
# B4: termini specifici
# ------------------------------------------------------------

def _voci(*righe):
    doc = fitz.open()
    pagina = doc.new_page()
    for i, riga in enumerate(righe):
        pagina.insert_text((72, 100 + i * 24), riga, fontsize=11)
    return build_word_map(pagina)[1]


def _trovate(termine, voci):
    return [" ".join(voci[i]["text"] for i in gruppo)
            for gruppo in find_custom_term_matches(termine, voci)]


def test_termine_con_apostrofo_dritto_trova_quello_tipografico():
    voci = [{"text": t} for t in "Compare la parte D’AMICO personalmente".split()]
    assert _trovate("D'Amico", voci) == ["D’AMICO"]


def test_termine_trova_la_forma_elisa():
    voci = _voci("La casa dell'Amico era vuota.")
    assert _trovate("Amico", voci) == ["dell'Amico"]


def test_termine_trova_la_parte_di_un_cognome_doppio():
    voci = _voci("Il fondo Rossignoli-Bianchetti confina.")
    assert _trovate("Rossignoli", voci) == ["Rossignoli-Bianchetti"]


def test_termine_con_trattino_isolato():
    voci = _voci("Sede in Via Roma, 12 - Milano.")
    assert len(find_custom_term_matches("Via Roma, 12 - Milano", voci)) == 1


def test_termine_resta_a_parole_intere():
    voci = _voci("La sentenza regola le spese.")
    assert find_custom_term_matches("se", voci) == []
    assert find_custom_term_matches("sent", voci) == []


def test_termini_senza_riscontro_riportati_negli_avvisi():
    class AnalizzatoreFinto:
        def analyze(self, text, entities, language):
            i = text.index("Zanfretta")
            return [RecognizerResult("PERSON", i, i + 9, 0.85)]

    doc = fitz.open()
    doc.new_page().insert_text((72, 90), "Il sig. Ermenegildo Zanfretta abita a Rovereto.", fontsize=12)
    esito = app.redact_pdf(doc.tobytes(), ["PERSON"], ["Rovereto", "Bragadin", "  "],
                           AnalizzatoreFinto())
    assert esito.avvisi["termini_non_trovati"] == ["Bragadin"]


# ------------------------------------------------------------
# B5: numero civico e CAP
# ------------------------------------------------------------

@pytest.mark.parametrize("testo,attesi", [
    ("residente in via Giuseppe Verdi n. 27/B, 38051 Borgo Valsugana (TN)", ["27/B", "38051"]),
    ("con studio in Piazza Dante 3, Trento", ["3"]),
    ("alla via delle Betulle 14, Rovereto", ["14"]),
    ("Corso Italia, 56 80100 Napoli", ["56", "80100"]),
])
def test_civico_e_cap_riconosciuti(testo, attesi):
    rec = app.ItStreetAddressRecognizer()
    trovati = [testo[r.start:r.end] for r in rec.analyze(testo, ["IT_ADDRESS"])]
    assert trovati == attesi


@pytest.mark.parametrize("testo", [
    "il corso di formazione 2021 si e' concluso",
    "e cosi' via 3 volte",
    "art. 2054 c.c. e sentenza n. 332/2024",
    "per euro 38051 oltre interessi",
])
def test_numeri_qualsiasi_non_sono_indirizzi(testo):
    assert app.ItStreetAddressRecognizer().analyze(testo, ["IT_ADDRESS"]) == []


# ------------------------------------------------------------
# B8: propagazione di cognomi con apostrofo o trattino
# ------------------------------------------------------------

def test_propagazione_cognome_con_apostrofo_e_forma_elisa():
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_text((72, 100), "la casa dell'Alonzi e il fondo di D'Alonzi", fontsize=11)
    testo, voci = build_word_map(pagina)
    analisi = {"full_text": testo, "entries": voci, "results": []}
    log = []
    app.apply_text_redactions(pagina, analisi, [], {"alonzi", "d'alonzi"}, log, 1)
    dopo = pagina.get_text()
    assert "Alonzi" not in dopo
    assert "casa" in dopo and "fondo" in dopo


def test_token_dei_nomi_con_apostrofo_e_trattino():
    testo = "il sig. Luca D’Alonzi e la sig.ra Anna Rossignoli-Bianchetti"
    analisi = {"full_text": testo, "entries": [], "results": [
        RecognizerResult("PERSON", testo.index("Luca"), testo.index("Alonzi") + 6, 0.85),
        RecognizerResult("PERSON", testo.index("Anna"), len(testo), 0.85),
    ]}
    tokens = collect_person_tokens(analisi)
    assert {"luca", "d'alonzi", "anna", "rossignoli-bianchetti",
            "rossignoli", "bianchetti"} <= tokens
