"""
Anonimizzatore PDF
Basato su Microsoft Presidio + PyMuPDF + Tesseract OCR
Anonimizzazione locale di documenti legali italiani (testo + scansioni).

Versione: 1.1.1
Licenza: GNU AGPL v3.0
"""

import streamlit as st
import fitz  # PyMuPDF
import csv
import os
import re
import sys
import logging
from io import BytesIO, StringIO
from collections import Counter
from presidio_analyzer import (
    AnalyzerEngine,
    RecognizerRegistry,
    EntityRecognizer,
    RecognizerResult,
)
from presidio_analyzer.nlp_engine import NlpEngineProvider

__version__ = "1.3.2"

# Logging diagnostico (sostituisce i try/except: pass)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("anonimizzatore-pdf")


# ============================================================
# DETECTION TESSERACT OCR
# ============================================================
# L-02: cerchiamo PRIMA nei path di sistema (Program Files),
# DOPO in %LOCALAPPDATA% per evitare path hijacking
# L-01: niente try/except: pass cieco — logghiamo gli errori

TESSERACT_AVAILABLE = False
TESSERACT_PATH = None
TESSERACT_VERSION = None
ITALIAN_AVAILABLE = False
TESSERACT_INIT_ERROR = None

try:
    import pytesseract
    from PIL import Image, ImageDraw, ImageFont

    if sys.platform == "win32":
        # ORDINE IMPORTANTE: prima i path di sistema (richiedono admin per
        # essere modificati), poi quelli utente. Mai il contrario.
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                TESSERACT_PATH = path
                break

    TESSERACT_VERSION = str(pytesseract.get_tesseract_version())
    TESSERACT_AVAILABLE = True

    available_langs = pytesseract.get_languages(config="")
    ITALIAN_AVAILABLE = "ita" in available_langs

except ImportError as e:
    TESSERACT_INIT_ERROR = f"Modulo non disponibile: {type(e).__name__}"
    logger.warning("Tesseract/PIL non importabili: %s", e)
except Exception as e:
    # Niente più 'pass' silenzioso: registriamo l'errore
    TESSERACT_INIT_ERROR = f"{type(e).__name__}"
    logger.warning("Inizializzazione Tesseract fallita: %s", e)


# ============================================================
# CONFIGURAZIONE PAGINA
# ============================================================

st.set_page_config(
    page_title="Anonimizzatore PDF",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={},
)


# ============================================================
# FILTRO FALSI POSITIVI (R-01)
# ============================================================
# Il NER statistico (spaCy) scambia regolarmente parole di
# intestazione dei provvedimenti per nomi di persona o luoghi:
# "Firmato Da", "Emesso Da", "Numero", "Data", "SE'", "CAUSA"...
# Queste vanno scartate PRIMA della redazione, ma SOLO per le
# entità NER: le entità a pattern (codice fiscale, IBAN, ecc.)
# non producono questo tipo di falso positivo e non vanno filtrate.

# Tipi di entità prodotti dal NER statistico (filtrabili)
NER_ENTITY_TYPES = {"PERSON", "LOCATION", "DATE_TIME", "NRP", "ORGANIZATION"}

# Lunghezza minima di un token perché sia "sostanziale"
MIN_TOKEN_LEN = 3

# Parole di boilerplate legale/documentale che NON sono mai
# di per sé un dato personale (tutte minuscole, senza punteggiatura)
FALSE_POSITIVE_STOPWORDS = {
    # intestazioni e campi documento
    "numero", "data", "firmato", "emesso", "serial", "registro",
    "generale", "sezionale", "raccolta", "pubblicazione", "copia",
    "originale", "pagina", "oggetto", "conclusioni", "premesso",
    "rilevato", "ritenuto", "osserva", "letto", "visto",
    # istituzioni e ruoli
    "repubblica", "italiana", "italiano", "italia", "popolo",
    "corte", "appello", "cassazione", "tribunale", "giudice",
    "presidente", "consigliere", "consiglieri", "estensore",
    "relatore", "magistrato", "magistrati", "sezione", "sezioni",
    "civile", "penale", "unite", "collegio", "camera", "consiglio",
    "cancelliere", "cancelleria", "procura", "procuratore",
    "ministero", "pubblico",
    # termini processuali
    "sentenza", "ordinanza", "decreto", "ricorso", "controricorso",
    "interlocutoria", "interlocutorio", "appellante", "appellata",
    "appellato", "appellati", "appellate", "ricorrente", "ricorrenti",
    "resistente", "resistenti", "controricorrente", "controricorrenti",
    "convenuto", "convenuta", "attore", "attrice", "contumace",
    "contumaci", "interveniente", "intervenuta", "intervenuto",
    "difensore", "difensori", "udienza", "giudizio", "causa",
    "merito", "istruttoria", "dispositivo", "motivi", "motivazione",
    "fatto", "fatti", "diritto", "svolgimento", "processo",
    "procedimento", "legge", "articolo", "artt", "art", "comma",
    "codice", "fiscale", "spese", "compensi", "interessi",
    "rivalutazione",
    # titoli professionali
    "avv", "avvocato", "avvocati", "dott", "ssa", "sig", "sigra",
    "prof", "ing", "geom", "rag", "notaio",
    # enti ricorrenti nei documenti legali
    "istituto", "nazionale", "assicurazione", "assicurazioni",
    "infortuni", "lavoro", "inail", "inps", "agenzia", "entrate",
    "comune", "provincia", "regione", "societa", "società", "soc",
    "coop", "srl", "spa", "sas", "snc",
    # preposizioni/congiunzioni che finiscono dentro le entità
    "da", "di", "del", "della", "dei", "delle", "il", "lo", "la",
    "le", "ed", "in", "per", "con", "su", "al", "ai", "gia", "già",
    "nome", "se",
}

# Punteggiatura da rimuovere ai bordi dei token
_TOKEN_PUNCT = ".,;:()[]{}'\"«»–—-’‘“”/\\"


def _clean_token(token):
    """Normalizza un token: rimuove punteggiatura ai bordi e minuscolizza."""
    return token.strip(_TOKEN_PUNCT).lower()


def is_false_positive(entity_type, text):
    """
    R-01: True se l'entità rilevata è quasi certamente un falso positivo.

    Si applica SOLO alle entità NER (PERSON, LOCATION, ...):
    - testo troppo corto ("SE'", "S", "Da") → falso positivo
    - nessun token sostanziale (solo frammenti/numeri) → falso positivo
    - tutti i token sostanziali sono boilerplate legale
      ("Firmato Da", "Numero", "Ordinanza Interlocutoria") → falso positivo
    """
    if entity_type not in NER_ENTITY_TYPES:
        return False
    stripped = text.strip()
    if len(stripped) < MIN_TOKEN_LEN:
        return True
    substantive = []
    for token in stripped.split():
        clean = _clean_token(token)
        # contano solo le LETTERE: "R.G.", "C.F.", "S", "12" non
        # sono token sostanziali
        letters = "".join(c for c in clean if c.isalpha())
        if len(letters) < MIN_TOKEN_LEN:
            continue
        substantive.append((clean, letters))
    if not substantive:
        return True
    return all(
        clean in FALSE_POSITIVE_STOPWORDS or letters in FALSE_POSITIVE_STOPWORDS
        for clean, letters in substantive
    )


# ============================================================
# MAPPA PAROLA → COORDINATE (R-02)
# ============================================================
# Sostituisce page.search_for(testo_trovato): search_for è
# case-insensitive e cerca SOTTOSTRINGHE, quindi un'entità "SE'"
# oscurava "se" dentro "sentenza", "spese", "pretese"...
# Con la mappa parola→rettangolo oscuriamo SOLO l'occorrenza
# effettivamente rilevata dall'analisi, alle sue coordinate.

def build_word_map(page):
    """
    Estrae le parole della pagina con le loro coordinate.

    Ritorna (full_text, entries) dove full_text è il testo
    ricostruito (parole separate da spazio) e entries è una lista
    di dict {start, end, rect, text} con gli offset di ogni parola
    dentro full_text.
    """
    words = page.get_text("words")
    # Ordine di lettura: blocco, riga, parola
    words.sort(key=lambda w: (w[5], w[6], w[7]))
    full_text = ""
    entries = []
    for w in words:
        token = w[4].strip()
        if not token:
            continue
        if full_text:
            full_text += " "
        start = len(full_text)
        full_text += token
        entries.append({
            "start": start,
            "end": len(full_text),
            "rect": fitz.Rect(w[0], w[1], w[2], w[3]),
            "text": token,
            "line": (w[5], w[6]),  # (blocco, riga) — per raggruppare i codici
        })
    return full_text, entries


def rects_for_span(entries, start, end):
    """Rettangoli delle parole che si sovrappongono allo span [start, end)."""
    return [
        (i, e["rect"]) for i, e in enumerate(entries)
        if e["start"] < end and e["end"] > start
    ]


def shrink_redact_rect(rect):
    """
    Restringe leggermente il rettangolo di redazione.

    apply_redactions() rimuove OGNI carattere il cui bounding box
    interseca il rettangolo: con interlinee strette o testo ruotato
    (es. filigrane diagonali "copia comunicata ai soli fini...")
    un rettangolo a piena altezza mutila anche i caratteri delle
    righe adiacenti. I caratteri della parola bersaglio attraversano
    comunque la fascia centrale, quindi vengono sempre rimossi.
    """
    v = min(1.0, rect.height * 0.15)
    h = min(0.3, rect.width * 0.05)
    return fitz.Rect(rect.x0 + h, rect.y0 + v, rect.x1 - h, rect.y1 - v)


# ============================================================
# PSEUDONIMIZZAZIONE CON CODICI (R-05)
# ============================================================
# In alternativa al rettangolo nero, ogni stringa redatta può essere
# sostituita da un codice univoco ("[PER-01]"): il testo originale
# viene comunque RIMOSSO FISICAMENTE dal PDF (stessa garanzia
# dell'oscuramento), ma il documento resta leggibile e coerente.
# A parte viene prodotta la tabella di accoppiamento codice↔testo,
# che è la chiave di re-identificazione e va custodita separatamente.

ENTITY_CODE_PREFIXES = {
    "PERSON": "PER",
    "PERSON (propagato)": "PER",
    "LOCATION": "LOC",
    "DATE_TIME": "DATA",
    "NRP": "NRP",
    "ORGANIZATION": "ORG",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "TEL",
    "IT_FISCAL_CODE": "CF",
    "IT_VAT_CODE": "PIVA",
    "IT_IDENTITY_CARD": "CI",
    "IT_DRIVER_LICENSE": "PAT",
    "IT_PASSPORT": "PASS",
    "IBAN_CODE": "IBAN",
    "CREDIT_CARD": "CARTA",
    "URL": "URL",
    "IP_ADDRESS": "IP",
    "CRYPTO": "CRYPTO",
    "TERMINE PERSONALIZZATO": "TERM",
}


class CodeAssigner:
    """
    Assegna codici univoci e stabili alle stringhe redatte.

    - Stessa stringa (normalizzata: minuscole, punteggiatura ai bordi
      ignorata) → stesso codice in tutto il documento.
    - Prefisso per tipo di dato: PER-01, CF-01, IBAN-01, TERM-01...
    - Un token di nome propagato ("Alonge") riusa il codice della
      persona già codificata ("Alonge Antonio") se l'attribuzione è
      univoca; altrimenti riceve un codice proprio.
    """

    def __init__(self):
        self._key_to_code = {}
        self._counters = {}
        self._entries_by_code = {}
        self._person_token_codes = {}  # token -> set di codici che lo contengono

    @staticmethod
    def _normalize(text):
        tokens = (_clean_token(t) for t in text.split())
        return " ".join(t for t in tokens if t)

    def assign(self, entity_type, text):
        """Ritorna il codice per questa occorrenza (creandolo se nuovo)."""
        prefix = ENTITY_CODE_PREFIXES.get(entity_type, "DATO")
        norm = self._normalize(text) or text.strip().lower()
        key = (prefix, norm)
        code = self._key_to_code.get(key)

        if code is None and prefix == "PER" and " " not in norm:
            # Token singolo (propagazione): riusa il codice della persona
            # SOLO se il token appartiene a una sola persona codificata.
            candidates = self._person_token_codes.get(norm)
            if candidates and len(candidates) == 1:
                code = next(iter(candidates))
                self._key_to_code[key] = code

        if code is None:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            code = f"{prefix}-{self._counters[prefix]:02d}"
            self._key_to_code[key] = code
            self._entries_by_code[code] = {
                "Codice": code,
                "Tipo": entity_type.replace(" (propagato)", ""),
                "Testo originale": text.strip(),
                "Occorrenze": 0,
            }

        if prefix == "PER":
            for token in norm.split():
                self._person_token_codes.setdefault(token, set()).add(code)

        self._entries_by_code[code]["Occorrenze"] += 1
        return code

    @property
    def mapping(self):
        """Tabella di accoppiamento: lista di dict ordinata per codice."""
        return sorted(
            self._entries_by_code.values(),
            key=lambda e: (e["Codice"].split("-")[0], e["Codice"]),
        )


def group_hits_by_line(entries, word_hits):
    """Raggruppa i (indice, rect) di un'entità per riga di testo."""
    groups = []
    current = []
    last_line = None
    for idx, rect in word_hits:
        line = entries[idx].get("line")
        if current and line != last_line:
            groups.append(current)
            current = []
        current.append((idx, rect))
        last_line = line
    if current:
        groups.append(current)
    return groups


def _fit_fontsize(text, rect):
    """Dimensione font massima che fa stare `text` dentro `rect`."""
    try:
        unit = fitz.get_text_length(text, fontname="helv", fontsize=1)
    except Exception:
        unit = 0.5 * max(1, len(text))
    if unit <= 0:
        return 6
    size = min(rect.height * 0.8, (rect.width * 0.95) / unit)
    return max(4, size)


def add_redaction_for_hits(page, entries, word_hits, mode, code=None):
    """
    Aggiunge le redact-annotation per le parole di un'occorrenza.

    - mode "blackout": rettangolo nero per parola (comportamento storico).
    - mode "codes": il testo viene rimosso e sostituito dal codice
      "[XXX-nn]" sul primo segmento di riga; gli eventuali segmenti
      successivi (entità che va a capo) restano vuoti.
    """
    if mode != "codes":
        for _idx, rect in word_hits:
            page.add_redact_annot(shrink_redact_rect(rect), fill=(0, 0, 0))
        return

    label = f"[{code}]"
    for gi, group in enumerate(group_hits_by_line(entries, word_hits)):
        union = fitz.Rect()
        for _idx, rect in group:
            union |= rect
        union = shrink_redact_rect(union)
        text = label if gi == 0 else ""
        page.add_redact_annot(
            union,
            text=text,
            fontname="helv",
            fontsize=_fit_fontsize(label, union),
            align=fitz.TEXT_ALIGN_CENTER,
            fill=(1, 1, 1),
            text_color=(0, 0, 0),
            cross_out=False,
        )


def find_custom_term_matches(term, entries):
    """
    Cerca un termine personalizzato come sequenza di PAROLE INTERE
    (case-insensitive, ignorando la punteggiatura ai bordi).
    Ritorna una lista di gruppi di indici parola corrispondenti.
    Niente più match di sottostringhe dentro altre parole.
    """
    term_tokens = [_clean_token(t) for t in term.split()]
    term_tokens = [t for t in term_tokens if t]
    if not term_tokens:
        return []
    doc_tokens = [_clean_token(e["text"]) for e in entries]
    n = len(term_tokens)
    matches = []
    for i in range(len(doc_tokens) - n + 1):
        if doc_tokens[i:i + n] == term_tokens:
            matches.append(list(range(i, i + n)))
    return matches


# ============================================================
# RECOGNIZER NOMI IN CONTESTO LEGALE (R-03)
# ============================================================
# spaCy manca nomi con cognomi rari (es. "Cabalisti Marco").
# Nei documenti legali italiani però ci sono contesti deterministici:
#   1. "Cognome Nome (C.F. XXXXXXXXXXXXXXXX)" — un nome seguito dal
#      codice fiscale tra parentesi è quasi certamente una persona
#   2. "avv./dott./sig. Nome Cognome" — titolo professionale
# Questo recognizer li cattura con regex + trimming degli eventuali
# ruoli finali ("Presidente", "Consigliere", ...).

# Token "nome proprio": iniziale maiuscola + almeno un altro carattere
_NAME_TOKEN = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-Þà-öø-ÿ'’\-]+"
_NAME_SEQ = rf"{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{0,3}}"


class ItLegalNameRecognizer(EntityRecognizer):
    """Nomi di persona in contesti tipici dei documenti legali italiani."""

    # "Cabalisti Marco (C.F. CBLMRC90L07A459F)"
    REGEX_NAME_CF = re.compile(
        rf"({_NAME_SEQ})\s*\(\s*(?i:c\.?\s?f\.?|cod\.?\s*fisc\.?|codice\s+fiscale)"
    )
    # "avv. Calogera Cusumano", "dott. ssa Clotilde Parise"
    REGEX_TITLE_NAME = re.compile(
        rf"\b(?i:avv|dott|prof|sig|ing|geom|rag|not)\."
        rf"\s*(?i:(?:ssa|ra|ri|re|ti)\.?\s+)?({_NAME_SEQ})"
    )

    SCORE_NAME_CF = 0.9
    SCORE_TITLE_NAME = 0.85

    def __init__(self):
        super().__init__(
            supported_entities=["PERSON"],
            supported_language="it",
            name="ItLegalNameRecognizer",
        )

    def load(self):
        pass

    def _trim_trailing_stopwords(self, text, start, end):
        """
        Rimuove dal fondo i token di ruolo/boilerplate catturati per
        errore ("Clotilde Parise Presidente" → "Clotilde Parise").
        Ritorna (start, end) aggiustati oppure None se non resta nulla.
        """
        span = text[start:end]
        tokens = list(re.finditer(r"\S+", span))
        while tokens and _clean_token(tokens[-1].group()) in FALSE_POSITIVE_STOPWORDS:
            tokens.pop()
        if not tokens:
            return None
        return start + tokens[0].start(), start + tokens[-1].end()

    def analyze(self, text, entities, nlp_artifacts=None):
        results = []
        if entities and "PERSON" not in entities:
            return results
        for regex, score in (
            (self.REGEX_NAME_CF, self.SCORE_NAME_CF),
            (self.REGEX_TITLE_NAME, self.SCORE_TITLE_NAME),
        ):
            for match in regex.finditer(text):
                trimmed = self._trim_trailing_stopwords(
                    text, match.start(1), match.end(1)
                )
                if trimmed is None:
                    continue
                start, end = trimmed
                if is_false_positive("PERSON", text[start:end]):
                    continue
                results.append(
                    RecognizerResult(
                        entity_type="PERSON",
                        start=start,
                        end=end,
                        score=score,
                    )
                )
        return results


# ============================================================
# INIZIALIZZAZIONE MOTORE DI ANALISI
# ============================================================

@st.cache_resource(show_spinner=False)
def initialize_analyzer():
    """Inizializza l'analyzer di Presidio con modello italiano."""
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "it", "model_name": "it_core_news_lg"}],
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    registry = RecognizerRegistry(supported_languages=["it"])
    registry.load_predefined_recognizers(languages=["it"])
    # R-03: nomi in contesti legali che il NER statistico manca
    registry.add_recognizer(ItLegalNameRecognizer())

    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
        supported_languages=["it"],
    )
    return analyzer


# ============================================================
# SANITIZZAZIONE PDF (M-01, M-03)
# ============================================================

def sanitize_pdf_metadata(doc):
    """
    M-01: Rimuove TUTTI i metadata del PDF (autore, titolo, oggetto,
    creator, producer) e l'XMP metadata stream.

    Un PDF generato da Word può avere autore "Mario Rossi" nei metadata;
    pdfinfo o qualsiasi PDF reader li mostra. Vanno azzerati.
    """
    try:
        # Azzera tutti i metadata standard
        doc.set_metadata({
            "title": "",
            "author": "",
            "subject": "",
            "keywords": "",
            "creator": "",
            "producer": "",
            "creationDate": "",
            "modDate": "",
        })
        # Rimuove anche l'XMP metadata stream (Adobe Extensible Metadata)
        doc.del_xml_metadata()
        logger.info("Metadata sanitizzati")
    except Exception as e:
        logger.warning("Sanitizzazione metadata fallita: %s", e)


def sanitize_pdf_objects(doc):
    """
    M-03: Rimuove annotazioni, allegati, AcroForm e JavaScript.

    Per documenti legali è critico: i commenti spesso contengono nomi,
    gli allegati possono essere CV/contratti, i campi form contengono
    dati inseriti, JavaScript può estrarre informazioni.
    """
    annotations_removed = 0
    forms_cleared = 0
    js_removed = 0

    try:
        # 1. Annotazioni (commenti, sticky note, evidenziature) su ogni pagina
        for page in doc:
            annots = list(page.annots() or [])
            for annot in annots:
                try:
                    page.delete_annot(annot)
                    annotations_removed += 1
                except Exception as e:
                    logger.warning("Rimozione annotazione fallita: %s", e)

        # 2. AcroForm fields (valori inseriti nei moduli)
        for page in doc:
            try:
                widgets = list(page.widgets() or [])
                for widget in widgets:
                    try:
                        # Svuota il valore del campo
                        widget.field_value = ""
                        widget.update()
                        forms_cleared += 1
                    except Exception:
                        pass
            except Exception:
                pass

        # 3. Allegati embedded (file collegati al PDF)
        attachments_removed = 0
        # M-03-R3 (#4): cancelliamo per indice, non per nome. embfile_del(name)
        # rimuove solo la prima occorrenza con quel nome — PDF prodotti fuori
        # PyMuPDF (Acrobat, Word) possono avere allegati con nomi duplicati.
        # L'eliminazione rinumera gli indici, quindi rileggiamo il count a
        # ogni iterazione e rimuoviamo sempre l'ultimo.
        try:
            max_iterations = doc.embfile_count() + 10  # safety cap
            iteration = 0
            while doc.embfile_count() > 0 and iteration < max_iterations:
                iteration += 1
                last_idx = doc.embfile_count() - 1
                try:
                    doc.embfile_del(last_idx)
                    attachments_removed += 1
                except Exception as e:
                    logger.warning(
                        "Rimozione allegato indice %d fallita: %s", last_idx, e
                    )
                    break  # evita loop infinito se un entry rifiuta di essere cancellato
        except Exception as e:
            logger.warning("Enumerazione allegati fallita: %s", e)

        # 4. JavaScript a livello documento (può eseguire codice all'apertura)
        # M-03-R1 (#2): doc.get_js() NON esiste in PyMuPDF — il vecchio guard
        # sollevava AttributeError che veniva ingoiato silenziosamente, quindi
        # questa branca non è mai eseguita dalla v1.0.0. Eseguiamo il loop xref
        # direttamente e logghiamo le singole eccezioni invece di nasconderle.
        for xref in range(1, doc.xref_length()):
            try:
                obj = doc.xref_object(xref)
                if "/JavaScript" in obj or "/JS" in obj:
                    # Sostituisce il contenuto con dict vuoto
                    doc.update_object(xref, "<<>>")
                    js_removed += 1
            except Exception as e:
                logger.warning("xref %d cleanup fallito: %s", xref, e)

        # M-03-R2 (#3): defense in depth. Anche con gli xref svuotati, il
        # catalog continua a riferire /Names/JavaScript e /OpenAction —
        # comportamento dei reader su dict vuoti è undefined (PDF spec) e in
        # ogni caso il documento "anonimizzato" continuerebbe ad annunciare
        # che conteneva JS. Strippiamo i riferimenti dal catalog.
        try:
            catalog_xref = doc.pdf_catalog()
            for catalog_key in ("OpenAction", "AA"):
                try:
                    doc.xref_set_key(catalog_xref, catalog_key, "null")
                except Exception as e:
                    logger.debug("Catalog /%s cleanup skipped: %s", catalog_key, e)
            # Per /Names rimuoviamo solo la subkey JavaScript (altri /Names
            # possono essere legittimi per dest, EmbeddedFiles ecc.).
            try:
                names_obj = doc.xref_get_key(catalog_xref, "Names")
                # xref_get_key restituisce ("xref","<xref> 0 R") oppure
                # ("dict","<< ... >>"); in entrambi i casi usiamo set_key
                # per rimuovere la subkey JavaScript se presente.
                if names_obj and len(names_obj) >= 2 and "JavaScript" in str(names_obj[1]):
                    doc.xref_set_key(catalog_xref, "Names", "null")
            except Exception as e:
                logger.debug("Catalog /Names cleanup skipped: %s", e)
            # xref_set_key(..., "null") NON cancella la chiave: lascia la
            # coppia "/Chiave null" nel dict (implementazione rebased,
            # PyMuPDF >= 1.24). Un valore null equivale a chiave assente per
            # la PDF spec (ISO 32000-1 §7.3.7), ma la coppia sopravvive anche
            # al save e il catalog continuerebbe ad annunciare che il
            # documento aveva OpenAction/JS. Il passaggio via set_key però
            # normalizza qualunque valore (ref indiretto, dict annidato) al
            # letterale "null", quindi ora possiamo rimuovere le coppie
            # testualmente in modo sicuro.
            try:
                catalog_text = doc.xref_object(catalog_xref, compressed=True)
                cleaned = re.sub(
                    r"/(?:OpenAction|AA|Names)\s+null", "", catalog_text
                )
                if cleaned != catalog_text:
                    doc.update_object(catalog_xref, cleaned)
            except Exception as e:
                logger.debug("Catalog null-key strip skipped: %s", e)
        except Exception as e:
            logger.warning("Catalog cleanup fallito: %s", e)

        logger.info(
            "Sanitizzazione: %d annotazioni, %d form fields, %d allegati, %d JS rimossi",
            annotations_removed, forms_cleared, attachments_removed, js_removed
        )

        return {
            "annotations": annotations_removed,
            "forms": forms_cleared,
            "attachments": attachments_removed,
            "javascript": js_removed,
        }

    except Exception as e:
        logger.warning("Sanitizzazione oggetti fallita: %s", e)
        return {"annotations": 0, "forms": 0, "attachments": 0, "javascript": 0}


# ============================================================
# UTILITY
# ============================================================

def is_scanned_page(page, threshold_chars=50):
    """Heuristica: pagina con pochissimo testo estraibile = probabilmente scansionata."""
    text = page.get_text()
    return len(text.strip()) < threshold_chars


def has_inline_images(page, min_image_area_ratio=0.05):
    """
    M-02: Detect immagini inline significative in una pagina testuale.

    Una pagina di contratto con testo + foto di carta d'identità
    NON viene rilevata come "scansionata" (ha abbondante testo),
    ma l'immagine contiene PII che vanno OCRate.

    Ritorna True se ci sono immagini che occupano almeno il 5%
    dell'area della pagina (escludiamo logo piccoli, watermark, ecc.).
    """
    try:
        images = page.get_images(full=True)
        if not images:
            return False

        page_area = abs(page.mediabox.width) * abs(page.mediabox.height)
        if page_area <= 0:
            return False

        # Calcola area totale delle immagini significative
        for img in images:
            xref = img[0]
            # Trova i bounding box dell'immagine sulla pagina
            try:
                bbox_list = page.get_image_bbox(img)
                if not isinstance(bbox_list, list):
                    bbox_list = [bbox_list]
                for bbox in bbox_list:
                    if hasattr(bbox, "width") and hasattr(bbox, "height"):
                        img_area = abs(bbox.width) * abs(bbox.height)
                        if img_area / page_area >= min_image_area_ratio:
                            return True
            except Exception:
                # Se non riusciamo a calcolare il bbox, conservativo: True
                return True

        return False
    except Exception as e:
        logger.warning("Detection immagini fallita: %s", e)
        return False


def safe_error_message(action, exception):
    """
    L-03: Restituisce un messaggio di errore SENZA esporre dettagli
    sensibili (stacktrace può contenere frammenti del PDF processato).
    """
    error_type = type(exception).__name__
    # Logghiamo i dettagli completi (file locale), ma all'utente diamo solo il tipo
    logger.error("%s: %s — %s", action, error_type, str(exception)[:200])
    return f"❌ {action}: {error_type}. Controlla i log per i dettagli."


# ============================================================
# REDAZIONE PAGINA TESTUALE (standard)
# ============================================================
# R-02: due fasi separate.
#   1. analyze_text_page  → analizza il testo ricostruito dalla
#      mappa parole e ritorna i risultati filtrati
#   2. apply_text_redactions → oscura SOLO le parole alle coordinate
#      dell'occorrenza rilevata (niente più search_for globale)

def analyze_text_page(page, selected_entities, analyzer, min_score,
                      page_num, debug_first=False):
    """
    Analizza una pagina testuale. Ritorna un dict con la mappa parole,
    i risultati validi e i contatori diagnostici.
    """
    full_text, entries = build_word_map(page)

    if debug_first:
        st.write(f"🔍 Pagina {page_num} (testuale) — primi 200 caratteri: `{full_text[:200]}`")

    raw_count = 0
    results = []
    dropped_fp = 0

    if full_text.strip() and selected_entities:
        try:
            all_results = analyzer.analyze(
                text=full_text,
                entities=selected_entities,
                language="it",
            )
            raw_count = len(all_results)

            if debug_first and all_results:
                debug_sample = [
                    f"{r.entity_type}={full_text[r.start:r.end][:25]!r}(s={r.score:.2f})"
                    for r in all_results[:6]
                ]
                st.write(f"   Esempi grezzi: {' | '.join(debug_sample)}")

            for r in all_results:
                if r.score < min_score:
                    continue
                # R-01: scarta i falsi positivi del NER
                if is_false_positive(r.entity_type, full_text[r.start:r.end]):
                    dropped_fp += 1
                    continue
                results.append(r)

        except Exception as e:
            # L-03: messaggio sanitizzato, dettagli solo nei log
            st.error(safe_error_message(f"Analisi pagina {page_num}", e))
            results = []

    return {
        "full_text": full_text,
        "entries": entries,
        "results": results,
        "raw": raw_count,
        "filtered": len(results),
        "dropped_fp": dropped_fp,
    }


def collect_person_tokens(analysis):
    """
    R-04: raccoglie i token dei nomi di persona rilevati, per
    propagarli a tutto il documento (es. "Cabalisti" rilevato a
    pagina 1 viene oscurato anche dove il NER lo manca).
    """
    tokens = set()
    full_text = analysis["full_text"]
    for r in analysis["results"]:
        if r.entity_type != "PERSON":
            continue
        for token in full_text[r.start:r.end].split():
            clean = _clean_token(token)
            if (
                len(clean) >= MIN_TOKEN_LEN
                and clean not in FALSE_POSITIVE_STOPWORDS
                and token[:1].isupper()
                and clean.isalpha()
            ):
                tokens.add(clean)
    return tokens


def apply_text_redactions(page, analysis, custom_terms, known_person_tokens,
                          log, page_num, redaction_mode="blackout",
                          assigner=None):
    """
    Applica le redazioni a una pagina testuale usando le coordinate.

    redaction_mode:
      - "blackout": rettangoli neri (default storico)
      - "codes": pseudonimizzazione — il testo è sostituito dal codice
        univoco assegnato da `assigner` (CodeAssigner)
    """
    full_text = analysis["full_text"]
    entries = analysis["entries"]
    use_codes = redaction_mode == "codes" and assigner is not None
    redacted_word_idx = set()

    def _log(tipo, testo, confidenza, code):
        row = {
            "Pagina": page_num,
            "Tipo": tipo,
            "Testo": testo,
            "Confidenza": confidenza,
            "Metodo": "Testo",
        }
        if use_codes:
            row["Codice"] = code
        log.append(row)

    # Ogni parola riceve UNA sola redazione (in modalità codici i label
    # non devono mai accavallarsi). Ordine di priorità:
    #   1. termini personalizzati (scelta esplicita dell'utente → codice
    #      TERM coerente in tutto il documento)
    #   2. entità deterministiche (CF, IBAN, ...)
    #   3. entità NER
    #   4. propagazione nomi

    # 1. Termini personalizzati: match per PAROLE INTERE
    for term in custom_terms:
        term = term.strip()
        if not term:
            continue
        for match_indexes in find_custom_term_matches(term, entries):
            word_hits = [(i, entries[i]["rect"]) for i in match_indexes]
            code = assigner.assign("TERMINE PERSONALIZZATO", term) if use_codes else None
            add_redaction_for_hits(page, entries, word_hits, redaction_mode, code)
            redacted_word_idx.update(match_indexes)
            _log("TERMINE PERSONALIZZATO", term, "100%", code)

    # 2-3. Entità rilevate dall'analisi (solo l'occorrenza alle sue coordinate)
    pattern_results = [r for r in analysis["results"]
                       if r.entity_type not in NER_ENTITY_TYPES]
    ner_results = [r for r in analysis["results"]
                   if r.entity_type in NER_ENTITY_TYPES]
    ordered_results = (
        sorted(pattern_results, key=lambda r: r.start)
        + sorted(ner_results, key=lambda r: r.start)
    )

    for result in ordered_results:
        found_text = full_text[result.start:result.end].strip()
        if not found_text:
            continue
        word_hits = rects_for_span(entries, result.start, result.end)
        # scarta le parole già redatte da un'entità precedente
        word_hits = [(i, r) for i, r in word_hits if i not in redacted_word_idx]
        if not word_hits:
            continue
        # se di un'entità NER resta solo un residuo non sostanziale
        # (es. "(C.F." dopo che il codice fiscale è già stato redatto), salta
        remaining_text = " ".join(entries[i]["text"] for i, _r in word_hits)
        if (result.entity_type in NER_ENTITY_TYPES
                and is_false_positive(result.entity_type, remaining_text)):
            continue
        code = assigner.assign(result.entity_type, found_text) if use_codes else None
        add_redaction_for_hits(page, entries, word_hits, redaction_mode, code)
        redacted_word_idx.update(idx for idx, _r in word_hits)
        _log(result.entity_type, found_text, f"{result.score:.0%}", code)

    # 4. R-04: propagazione dei nomi rilevati altrove nel documento
    #    (solo parole intere con iniziale maiuscola, mai sottostringhe)
    for idx, entry in enumerate(entries):
        if idx in redacted_word_idx:
            continue
        clean = _clean_token(entry["text"])
        if clean in known_person_tokens and entry["text"][:1].isupper():
            code = assigner.assign("PERSON (propagato)", entry["text"]) if use_codes else None
            add_redaction_for_hits(
                page, entries, [(idx, entry["rect"])], redaction_mode, code
            )
            redacted_word_idx.add(idx)
            _log("PERSON (propagato)", entry["text"], "—", code)

    page.apply_redactions()


# ============================================================
# REDAZIONE PAGINA SCANSIONATA (OCR)
# ============================================================

def process_scanned_page(src_page, out_doc, selected_entities, custom_terms,
                         analyzer, min_score, dpi, lang, log, page_num,
                         debug_first=False, known_person_tokens=None,
                         redaction_mode="blackout", assigner=None):
    """OCR su pagina scansionata + redazione con rettangoli su immagine."""
    known_person_tokens = known_person_tokens or set()
    use_codes = redaction_mode == "codes" and assigner is not None
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = src_page.get_pixmap(matrix=mat, alpha=False)
    img_data = pix.tobytes("png")
    img = Image.open(BytesIO(img_data))

    raw_count = 0
    filtered_count = 0

    try:
        ocr_data = pytesseract.image_to_data(
            img, lang=lang, output_type=pytesseract.Output.DICT
        )
    except Exception as e:
        # L-03: messaggio sanitizzato
        st.warning(safe_error_message(f"OCR pagina {page_num}", e))
        new_page = out_doc.new_page(width=src_page.rect.width, height=src_page.rect.height)
        img_bytes = BytesIO()
        img.save(img_bytes, format="JPEG", quality=85)
        new_page.insert_image(new_page.rect, stream=img_bytes.getvalue())
        return 0, 0

    words = []
    for i in range(len(ocr_data["text"])):
        word = ocr_data["text"][i].strip()
        try:
            conf = int(ocr_data["conf"][i])
        except (ValueError, TypeError):
            conf = 0
        if word and conf > 30:
            words.append({
                "text": word,
                "x": ocr_data["left"][i],
                "y": ocr_data["top"][i],
                "w": ocr_data["width"][i],
                "h": ocr_data["height"][i],
            })

    if debug_first:
        st.write(f"🔍 Pagina {page_num} (OCR) — parole rilevate: {len(words)}")
        if words:
            sample = " ".join([w["text"] for w in words[:20]])
            st.write(f"   Estratto OCR: `{sample}...`")

    draw = ImageDraw.Draw(img)

    def draw_redaction(matching, code=None):
        """Rettangolo nero, oppure riquadro bianco col codice (pseudonimizzazione)."""
        x_min = min(w["x"] for w in matching)
        y_min = min(w["y"] for w in matching)
        x_max = max(w["x"] + w["w"] for w in matching)
        y_max = max(w["y"] + w["h"] for w in matching)
        pad = 2
        box = [(x_min - pad, y_min - pad), (x_max + pad, y_max + pad)]
        if not (use_codes and code):
            draw.rectangle(box, fill="black")
            return
        draw.rectangle(box, fill="white", outline="black")
        label = f"[{code}]"
        size = max(10, int((y_max - y_min) * 0.75))
        while size >= 8:
            try:
                font = ImageFont.load_default(size=size)
            except TypeError:  # Pillow < 10.1: font bitmap a dimensione fissa
                font = ImageFont.load_default()
                break
            bbox = draw.textbbox((0, 0), label, font=font)
            if bbox[2] - bbox[0] <= (x_max - x_min):
                break
            size = int(size * 0.8)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            ((x_min + x_max - tw) / 2, (y_min + y_max - th) / 2),
            label, fill="black", font=font,
        )

    if words:
        full_text = ""
        word_positions = []
        for idx, w in enumerate(words):
            start = len(full_text)
            full_text += w["text"]
            end = len(full_text)
            word_positions.append((start, end, idx))
            full_text += " "

        results = []
        if selected_entities and full_text.strip():
            try:
                all_results = analyzer.analyze(
                    text=full_text,
                    entities=selected_entities,
                    language="it",
                )
                raw_count = len(all_results)
                # R-01: soglia + filtro falsi positivi NER
                results = [
                    r for r in all_results
                    if r.score >= min_score
                    and not is_false_positive(r.entity_type, full_text[r.start:r.end])
                ]
                filtered_count = len(results)

                if debug_first and all_results:
                    sample = [
                        f"{r.entity_type}={full_text[r.start:r.end][:25]!r}(s={r.score:.2f})"
                        for r in all_results[:6]
                    ]
                    st.write(f"   Entità grezze OCR: {' | '.join(sample)}")

            except Exception as e:
                # L-03: messaggio sanitizzato
                st.warning(safe_error_message(f"Presidio OCR pagina {page_num}", e))

        # Stesso ordine di priorità delle pagine testuali: ogni parola
        # riceve UNA sola redazione (termini utente → entità → propagazione)
        drawn_idx = set()

        def _log_ocr(tipo, testo, confidenza, code):
            row = {
                "Pagina": page_num,
                "Tipo": tipo,
                "Testo": testo,
                "Confidenza": confidenza,
                "Metodo": "OCR",
            }
            if use_codes:
                row["Codice"] = code
            log.append(row)

        # 1. Termini personalizzati
        for term in custom_terms:
            term = term.strip()
            if not term:
                continue
            term_words = term.split()
            for i in range(len(words) - len(term_words) + 1):
                match = all(
                    _clean_token(words[i + j]["text"]) == _clean_token(term_words[j])
                    for j in range(len(term_words))
                )
                if match:
                    code = assigner.assign("TERMINE PERSONALIZZATO", term) if use_codes else None
                    draw_redaction(words[i:i + len(term_words)], code)
                    drawn_idx.update(range(i, i + len(term_words)))
                    _log_ocr("TERMINE PERSONALIZZATO", term, "100%", code)

        # 2-3. Entità rilevate (prima deterministiche, poi NER)
        pattern_results = [r for r in results if r.entity_type not in NER_ENTITY_TYPES]
        ner_results = [r for r in results if r.entity_type in NER_ENTITY_TYPES]
        for result in (sorted(pattern_results, key=lambda r: r.start)
                       + sorted(ner_results, key=lambda r: r.start)):
            matching_idx = [
                idx for start, end, idx in word_positions
                if start < result.end and end > result.start
                and idx not in drawn_idx
            ]
            if matching_idx:
                found_text = full_text[result.start:result.end]
                remaining_text = " ".join(words[i]["text"] for i in matching_idx)
                if (result.entity_type in NER_ENTITY_TYPES
                        and is_false_positive(result.entity_type, remaining_text)):
                    continue
                code = assigner.assign(result.entity_type, found_text) if use_codes else None
                draw_redaction([words[i] for i in matching_idx], code)
                drawn_idx.update(matching_idx)
                _log_ocr(result.entity_type, found_text, f"{result.score:.0%}", code)

        # 4. R-04: propagazione dei nomi rilevati nelle pagine testuali
        # (parole intere con iniziale maiuscola, mai sottostringhe)
        for idx, w in enumerate(words):
            if idx in drawn_idx:
                continue
            clean = _clean_token(w["text"])
            if clean in known_person_tokens and w["text"][:1].isupper():
                code = assigner.assign("PERSON (propagato)", w["text"]) if use_codes else None
                draw_redaction([w], code)
                drawn_idx.add(idx)
                _log_ocr("PERSON (propagato)", w["text"], "—", code)

    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG", quality=85, optimize=True)
    img_bytes.seek(0)
    new_page = out_doc.new_page(width=src_page.rect.width, height=src_page.rect.height)
    new_page.insert_image(new_page.rect, stream=img_bytes.getvalue())

    return raw_count, filtered_count


# ============================================================
# FUNZIONE PRINCIPALE
# ============================================================

def redact_pdf(input_bytes, selected_entities, custom_terms, analyzer,
               min_score=0.4, ocr_mode="auto", ocr_dpi=300, ocr_lang="ita",
               redaction_mode="blackout"):
    """
    Anonimizza un PDF. Gestisce sia pagine testuali che scansionate.
    ocr_mode: 'auto' | 'always' | 'never'
    redaction_mode: 'blackout' (rettangoli neri) | 'codes' (pseudonimizzazione)

    Ritorna (bytes_pdf, log, mapping) dove mapping è la tabella di
    accoppiamento codice↔testo (vuota in modalità blackout).
    """
    src_doc = fitz.open(stream=input_bytes, filetype="pdf")
    out_doc = fitz.open()
    log = []
    assigner = CodeAssigner() if redaction_mode == "codes" else None

    st.write(f"📄 Documento: {len(src_doc)} pagine")
    st.write(f"🎯 Entità cercate ({len(selected_entities)}): {', '.join(selected_entities)}")
    st.write(f"📊 Soglia minima: {min_score:.0%} · Modalità OCR: **{ocr_mode}**")

    total_pages = len(src_doc)
    progress_bar = st.progress(0.0)
    status_text = st.empty()

    total_raw = 0
    total_filtered = 0
    total_dropped_fp = 0
    pages_ocr = 0
    pages_text = 0
    pages_with_inline_images = 0

    # ---------- PASSATA 1: analisi delle pagine testuali ----------
    # Analizziamo PRIMA tutto il documento per raccogliere i nomi di
    # persona rilevati (R-04): così "Cabalisti" trovato a pagina 1
    # viene oscurato anche nelle pagine dove il NER lo manca.
    page_plans = {}  # page_index -> {"use_ocr": bool, "analysis": dict|None}
    known_person_tokens = set()

    for page_index, src_page in enumerate(src_doc):
        page_num = page_index + 1
        progress_bar.progress((page_index + 1) / (total_pages * 2))
        status_text.text(f"🧠 Analisi pagina {page_num}/{total_pages}...")

        scanned = is_scanned_page(src_page)

        # M-02: rileva immagini inline significative in pagine testuali
        has_images = False
        if not scanned:
            has_images = has_inline_images(src_page)
            if has_images:
                pages_with_inline_images += 1

        # Decide se applicare OCR
        use_ocr = (
            (ocr_mode == "always" and TESSERACT_AVAILABLE) or
            (ocr_mode == "auto" and scanned and TESSERACT_AVAILABLE)
        )

        analysis = None
        if not use_ocr:
            analysis = analyze_text_page(
                src_page, selected_entities, analyzer, min_score,
                page_num, debug_first=(page_num == 1),
            )
            known_person_tokens |= collect_person_tokens(analysis)
            total_raw += analysis["raw"]
            total_filtered += analysis["filtered"]
            total_dropped_fp += analysis["dropped_fp"]

        page_plans[page_index] = {
            "use_ocr": use_ocr,
            "scanned": scanned,
            "has_images": has_images,
            "analysis": analysis,
        }

    # I termini personalizzati non vanno propagati come nomi, ma i
    # nomi utente sono comunque cercati parola-per-parola (vedi sotto).

    # ---------- PASSATA 2: redazione ----------
    for page_index, src_page in enumerate(src_doc):
        page_num = page_index + 1
        plan = page_plans[page_index]
        progress_bar.progress(0.5 + (page_index + 1) / (total_pages * 2))

        if plan["use_ocr"]:
            status_text.text(f"🔍 OCR pagina {page_num}/{total_pages}...")
            raw, filtered = process_scanned_page(
                src_page, out_doc, selected_entities, custom_terms,
                analyzer, min_score, ocr_dpi, ocr_lang, log, page_num,
                debug_first=(page_num == 1),
                known_person_tokens=known_person_tokens,
                redaction_mode=redaction_mode,
                assigner=assigner,
            )
            total_raw += raw
            total_filtered += filtered
            pages_ocr += 1
        else:
            if plan["scanned"] and not TESSERACT_AVAILABLE:
                status_text.text(f"⚠️ Pagina {page_num}/{total_pages} scansionata ma OCR non disponibile")
            elif plan["has_images"] and ocr_mode == "auto":
                status_text.text(f"📄 Pagina {page_num}/{total_pages} (⚠️ contiene immagini)")
            else:
                status_text.text(f"📄 Pagina {page_num}/{total_pages}...")

            out_doc.insert_pdf(src_doc, from_page=page_index, to_page=page_index)
            new_page = out_doc[-1]
            apply_text_redactions(
                new_page, plan["analysis"], custom_terms,
                known_person_tokens, log, page_num,
                redaction_mode=redaction_mode,
                assigner=assigner,
            )
            pages_text += 1

    progress_bar.empty()
    status_text.empty()

    # M-02: warning se ci sono immagini inline in modalità auto
    if pages_with_inline_images > 0 and ocr_mode == "auto":
        st.warning(
            f"⚠️ **Attenzione:** rilevate immagini significative in {pages_with_inline_images} pagine "
            f"testuali (firme scansionate, foto di documenti, timbri...). "
            f"Queste immagini **NON sono state OCRate**. Se possono contenere dati sensibili, "
            f"rilancia l'anonimizzazione in modalità **'Forza OCR su tutto'**."
        )

    # M-01 + M-03: sanitizzazione PDF di output
    status_text.text("🧹 Sanitizzazione metadata e oggetti residui...")
    sanitize_pdf_metadata(out_doc)
    sanitize_stats = sanitize_pdf_objects(out_doc)
    status_text.empty()

    # Riepilogo
    st.write(f"📈 **Riepilogo:** {pages_text} pagine testuali · {pages_ocr} pagine OCR")
    st.write(
        f"   Presidio: {total_raw} risultati grezzi → {total_filtered} validi "
        f"(soglia ≥{min_score:.0%}, {total_dropped_fp} falsi positivi scartati)"
    )
    if known_person_tokens:
        st.write(f"   👤 Nomi propagati a tutto il documento: {len(known_person_tokens)} token")

    sanitize_total = sum(sanitize_stats.values())
    if sanitize_total > 0:
        st.write(
            f"   🧹 Sanitizzazione: "
            f"{sanitize_stats['annotations']} annotazioni · "
            f"{sanitize_stats['forms']} form fields · "
            f"{sanitize_stats['attachments']} allegati · "
            f"{sanitize_stats['javascript']} JavaScript rimossi"
        )

    if total_raw > 0 and total_filtered == 0:
        st.warning(f"⚠️ Presidio ha trovato entità ma tutte con score < {min_score:.0%}. Abbassa la soglia nella sidebar.")

    output_bytes = BytesIO()
    out_doc.save(output_bytes, garbage=4, deflate=True, clean=True)
    out_doc.close()
    src_doc.close()
    output_bytes.seek(0)
    mapping = assigner.mapping if assigner else []
    return output_bytes.getvalue(), log, mapping


# ============================================================
# INTERFACCIA UTENTE
# ============================================================

st.title("🔒 Anonimizzatore PDF")
st.caption(f"Anonimizzazione documenti in locale · Powered by Microsoft Presidio + Tesseract OCR · v{__version__}")

# Banner stato OCR
if TESSERACT_AVAILABLE and ITALIAN_AVAILABLE:
    st.success(f"✅ OCR attivo (Tesseract {TESSERACT_VERSION}) — PDF scansionati supportati in italiano")
elif TESSERACT_AVAILABLE and not ITALIAN_AVAILABLE:
    st.warning("⚠️ Tesseract installato ma lingua italiana mancante. Reinstalla Tesseract scegliendo il pacchetto italiano.")
else:
    info_msg = "ℹ️ Tesseract OCR non rilevato — funzionano solo PDF testuali."
    if TESSERACT_INIT_ERROR:
        info_msg += f" (causa: {TESSERACT_INIT_ERROR})"
    info_msg += " Per installare Tesseract, vedi README.md"
    st.info(info_msg)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Cosa anonimizzare")

    st.subheader("Dati personali")
    use_person = st.checkbox("Nomi di persona", value=True)
    use_email = st.checkbox("Email", value=True)
    use_phone = st.checkbox("Numeri di telefono", value=True)
    use_location = st.checkbox("Località e indirizzi", value=True)
    use_date = st.checkbox("Date", value=False, help="Disabilitato di default: spesso le date servono nei documenti legali")

    st.subheader("Documenti italiani")
    use_cf = st.checkbox("Codice fiscale", value=True)
    use_piva = st.checkbox("Partita IVA", value=True)
    use_ci = st.checkbox("Carta d'identità", value=True)
    use_patente = st.checkbox("Patente di guida", value=True)
    use_passport = st.checkbox("Passaporto", value=True)

    st.subheader("Dati finanziari")
    use_iban = st.checkbox("IBAN", value=True)
    use_credit_card = st.checkbox("Carta di credito", value=True)

    st.subheader("Altri")
    use_url = st.checkbox("URL", value=False)
    use_ip = st.checkbox("Indirizzi IP", value=False)
    use_crypto = st.checkbox("Wallet crypto", value=False)

    st.divider()

    st.subheader("🖊️ Modalità redazione")
    redaction_mode = st.radio(
        "Come sostituire i dati sensibili",
        options=["blackout", "codes"],
        format_func=lambda x: {
            "blackout": "⬛ Oscuramento (rettangoli neri)",
            "codes": "🔖 Pseudonimizzazione con codici",
        }[x],
        help=(
            "Oscuramento: il testo viene rimosso e coperto da un rettangolo nero. "
            "Pseudonimizzazione: il testo viene rimosso e sostituito da un codice "
            "univoco (es. [PER-01]) — stessa stringa, stesso codice in tutto il "
            "documento. Viene generata a parte la tabella di accoppiamento "
            "codice↔testo originale. ATTENZIONE: il documento con i codici resta "
            "un dato personale ai sensi del GDPR finché esiste la tabella."
        ),
    )

    st.divider()

    st.subheader("🎚️ Soglia di confidenza")
    min_score = st.slider(
        "Sensibilità del rilevamento",
        min_value=0.1, max_value=1.0, value=0.4, step=0.05,
        help="Più alto = meno falsi positivi ma rischio di perdere occorrenze.",
    )

    st.divider()

    st.subheader("🔍 OCR (PDF scansionati)")
    if TESSERACT_AVAILABLE:
        ocr_mode = st.radio(
            "Modalità OCR",
            options=["auto", "always", "never"],
            format_func=lambda x: {
                "auto": "🤖 Automatica",
                "always": "🔄 Forza OCR su tutto (più sicuro)",
                "never": "❌ Mai OCR",
            }[x],
            help=(
                "Auto: rileva automaticamente le pagine scansionate. "
                "Forza OCR: applica OCR a ogni pagina anche se testuale, "
                "utile per documenti che contengono firme/timbri/foto di ID. Più sicuro ma più lento."
            ),
        )
        ocr_dpi = st.select_slider(
            "Qualità OCR (DPI)",
            options=[150, 200, 300, 400, 600],
            value=300,
            help="Più alto = OCR più accurato ma più lento. 300 è lo standard.",
        )
    else:
        ocr_mode = "never"
        ocr_dpi = 300
        st.caption("⚠️ Tesseract non installato — vedi README.md")

# Mappa entità - LISTA di tuple (non dict con bool come chiavi!)
entity_map = [
    (use_person, "PERSON"),
    (use_email, "EMAIL_ADDRESS"),
    (use_phone, "PHONE_NUMBER"),
    (use_location, "LOCATION"),
    (use_date, "DATE_TIME"),
    (use_cf, "IT_FISCAL_CODE"),
    (use_piva, "IT_VAT_CODE"),
    (use_ci, "IT_IDENTITY_CARD"),
    (use_patente, "IT_DRIVER_LICENSE"),
    (use_passport, "IT_PASSPORT"),
    (use_iban, "IBAN_CODE"),
    (use_credit_card, "CREDIT_CARD"),
    (use_url, "URL"),
    (use_ip, "IP_ADDRESS"),
    (use_crypto, "CRYPTO"),
]
selected_entities = [entity for flag, entity in entity_map if flag]

# --- MAIN ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📄 Documento")
    uploaded_file = st.file_uploader(
        "Carica il PDF da anonimizzare",
        type=["pdf"],
        label_visibility="collapsed",
    )

with col2:
    st.subheader("🎯 Termini specifici")
    custom_terms_text = st.text_area(
        "Inserisci nomi, ragioni sociali, indirizzi (uno per riga)",
        placeholder="Mario Rossi\nACME S.p.A.\nVia Roma 12, Milano",
        height=140,
        label_visibility="collapsed",
    )

custom_terms = [t for t in custom_terms_text.split("\n") if t.strip()] if custom_terms_text else []

if selected_entities or custom_terms:
    summary = []
    if selected_entities:
        summary.append(f"**{len(selected_entities)} categorie automatiche**")
    if custom_terms:
        summary.append(f"**{len(custom_terms)} termini specifici**")
    summary.append(f"OCR: **{ocr_mode}**" if TESSERACT_AVAILABLE else "OCR: **non disponibile**")
    st.info(" · ".join(summary))

st.divider()

# --- SEZIONE DIAGNOSTICA ---
with st.expander("🧪 Test e diagnostica"):
    st.markdown("**Verifica che tutti i componenti funzionino correttamente**")

    col_test1, col_test2 = st.columns(2)

    with col_test1:
        if st.button("Test Presidio (rilevamento entità)"):
            with st.spinner("Test in corso..."):
                try:
                    analyzer = initialize_analyzer()
                    test_text = """
                    Mario Rossi, nato il 15/03/1980 a Roma.
                    Email: mario.rossi@example.com
                    Telefono: +39 3201234567
                    Codice Fiscale: RSSMRA80C15H501U
                    Partita IVA: 12345678901
                    IBAN: IT60X0542811101000000123456
                    """
                    results = analyzer.analyze(
                        text=test_text,
                        entities=selected_entities if selected_entities else None,
                        language="it",
                    )
                    if results:
                        st.success(f"✅ Test OK: {len(results)} entità rilevate")
                        for r in results:
                            st.text(f"- {r.entity_type}: {test_text[r.start:r.end]} ({r.score:.0%})")
                    else:
                        st.warning("⚠️ Nessuna entità rilevata. Verifica i flag in sidebar.")
                except Exception as e:
                    st.error(safe_error_message("Test Presidio", e))

    with col_test2:
        st.markdown("**Stato componenti:**")
        st.markdown(f"- Versione app: **{__version__}**")
        st.markdown(f"- Presidio: ✅ pronto")
        st.markdown(f"- Categorie attive: **{len(selected_entities)}**")
        st.markdown(f"- Soglia: **{min_score:.0%}**")
        st.markdown(f"- Termini custom: **{len(custom_terms)}**")
        if TESSERACT_AVAILABLE:
            st.markdown(f"- Tesseract: ✅ versione {TESSERACT_VERSION}")
            st.markdown(f"- Lingua italiana: {'✅' if ITALIAN_AVAILABLE else '❌'}")
            if TESSERACT_PATH:
                st.caption(f"Path: `{TESSERACT_PATH}`")
        else:
            st.markdown(f"- Tesseract: ❌ non rilevato")
            if TESSERACT_INIT_ERROR:
                st.caption(f"Errore: {TESSERACT_INIT_ERROR}")
            st.caption("Installa Tesseract per supportare PDF scansionati")

st.divider()

# --- AZIONE ---
# N-03 (#7): guard difensivo contro OOM silenzioso su PDF molto grandi.
# Il limite reale è imposto da .streamlit/config.toml -> server.maxUploadSize
# (Streamlit blocca prima ancora di raggiungere Python). Questo check protegge
# il caso in cui qualcuno esegua `streamlit run` senza il config (es. fuori
# dal repo). Tenere MAX_PDF_BYTES in sync con il valore di config.toml.
MAX_PDF_BYTES = 100 * 1024 * 1024  # 100 MB
if uploaded_file is not None:
    if uploaded_file.size > MAX_PDF_BYTES:
        st.error(
            f"⚠️ PDF troppo grande ({uploaded_file.size / 1024**2:.0f} MB). "
            f"Limite: {MAX_PDF_BYTES // 1024**2} MB. "
            "Per file più grandi, suddividili o aumenta `maxUploadSize` "
            "in `.streamlit/config.toml`."
        )
        st.stop()
    if not selected_entities and not custom_terms:
        st.error("⚠️ Seleziona almeno una categoria nella sidebar o inserisci un termine specifico.")
    else:
        if st.button("🔒 Anonimizza documento", type="primary", use_container_width=True):

            with st.status("Caricamento motore di analisi...", expanded=False) as status:
                analyzer = initialize_analyzer()
                status.update(label="✅ Motore pronto", state="complete")

            input_bytes = uploaded_file.read()
            output_bytes, log, mapping = redact_pdf(
                input_bytes,
                selected_entities,
                custom_terms,
                analyzer,
                min_score=min_score,
                ocr_mode=ocr_mode,
                ocr_dpi=ocr_dpi,
                ocr_lang="ita" if ITALIAN_AVAILABLE else "eng",
                redaction_mode=redaction_mode,
            )

            # FIX rerun: ogni click su un download_button riesegue lo script
            # da capo, e st.button torna False — se i risultati vivessero solo
            # dentro questo if, dopo "Scarica PDF" sparirebbe anche il bottone
            # del CSV di accoppiamento. Li salviamo in session_state e li
            # renderizziamo SEMPRE (blocco sotto), finché il file non cambia.
            st.session_state["risultato"] = {
                "output_bytes": output_bytes,
                "log": log,
                "mapping": mapping,
                "redaction_mode": redaction_mode,
                "source_name": uploaded_file.name,
                "source_size": uploaded_file.size,
            }

        # --- RISULTATI (persistenti tra i rerun dei download) ---
        risultato = st.session_state.get("risultato")
        if risultato is not None and (
            risultato["source_name"] != uploaded_file.name
            or risultato["source_size"] != uploaded_file.size
        ):
            # il file caricato è cambiato: i vecchi risultati non valgono più
            risultato = None
            st.session_state.pop("risultato", None)

        if risultato is not None:
            res_log = risultato["log"]
            res_mapping = risultato["mapping"]
            res_mode = risultato["redaction_mode"]

            if res_log:
                if res_mode == "codes":
                    st.success(
                        f"✅ Pseudonimizzazione completata: **{len(res_log)} elementi "
                        f"sostituiti** con **{len(res_mapping)} codici univoci**"
                    )
                else:
                    st.success(f"✅ Anonimizzazione completata: **{len(res_log)} elementi oscurati**")

                col_a, col_b = st.columns([1, 2])

                with col_a:
                    prefix = "pseudonimizzato" if res_mode == "codes" else "anonimizzato"
                    output_filename = f"{prefix}_{risultato['source_name']}"
                    st.download_button(
                        label="📥 Scarica PDF",
                        data=risultato["output_bytes"],
                        file_name=output_filename,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                    )
                    if res_mapping:
                        # CSV con BOM utf-8 così Excel lo apre correttamente
                        csv_buf = StringIO()
                        writer = csv.DictWriter(
                            csv_buf,
                            fieldnames=["Codice", "Tipo", "Testo originale", "Occorrenze"],
                            delimiter=";",
                        )
                        writer.writeheader()
                        writer.writerows(res_mapping)
                        base_name = os.path.splitext(risultato["source_name"])[0]
                        st.download_button(
                            label="🔑 Scarica tabella di accoppiamento (CSV)",
                            data=csv_buf.getvalue().encode("utf-8-sig"),
                            file_name=f"accoppiamento_{base_name}.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )

                with col_b:
                    types_count = Counter(item["Tipo"] for item in res_log)
                    method_count = Counter(item["Metodo"] for item in res_log)
                    summary = " · ".join([f"{count} {tipo}" for tipo, count in types_count.most_common()])
                    st.caption(f"**Tipi:** {summary}")
                    st.caption(f"**Metodi:** {dict(method_count)}")

                if res_mapping:
                    st.warning(
                        "🔑 **La tabella di accoppiamento è la chiave di re-identificazione.** "
                        "Conservala separatamente dal documento e **non inviarla mai** insieme "
                        "al PDF pseudonimizzato. Ai sensi del GDPR, il documento con i codici "
                        "resta un dato personale finché la tabella esiste: per depositi o "
                        "pubblicazioni usa la modalità Oscuramento."
                    )
                    with st.expander(f"🔑 Tabella di accoppiamento ({len(res_mapping)} codici)"):
                        st.dataframe(res_mapping, use_container_width=True, hide_index=True)

                with st.expander(f"📊 Report completo ({len(res_log)} redazioni)"):
                    st.dataframe(res_log, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ Nessuna entità sensibile rilevata. Controlla il riepilogo Presidio sopra.")

# --- FOOTER ---
st.divider()
with st.expander("ℹ️ Informazioni e avvertenze"):
    st.markdown(f"""
    **Versione:** {__version__}
    **Privacy:** tutti i file sono elaborati in locale. Nessun dato esce dal computer.

    **Redazione testo:** rimozione fisica del testo + rettangolo nero (irreversibile).

    **Pseudonimizzazione (v1.3+):** in alternativa all'oscuramento, ogni stringa
    rilevata può essere sostituita da un codice univoco (es. `[PER-01]`): stessa
    stringa → stesso codice in tutto il documento, così il testo resta leggibile.
    Il testo originale viene comunque rimosso fisicamente. La tabella di
    accoppiamento codice↔testo va scaricata e custodita **separatamente**: è la
    chiave di re-identificazione. Il documento pseudonimizzato resta un dato
    personale ai sensi del GDPR finché la tabella esiste.

    **Redazione scansioni (OCR):** il PDF viene rasterizzato e ricostruito come immagine con rettangoli neri (la pagina diventa solo immagine, non selezionabile).

    **Sanitizzazione automatica (v1.1+):** il PDF di output viene ripulito da metadata (autore, titolo), annotazioni, allegati, campi form e JavaScript.

    **Precisione (v1.2+):**
    - La redazione avviene alle **coordinate esatte** dell'occorrenza rilevata:
      mai più sottostringhe oscurate dentro altre parole.
    - Le parole di intestazione dei provvedimenti (Numero, Data, Firmato, ...)
      non vengono più scambiate per nomi.
    - I nomi accanto a un codice fiscale ("Cognome Nome (C.F. ...)") e dopo i
      titoli (avv., dott., sig., ...) vengono riconosciuti anche quando il
      modello linguistico li manca, e propagati a tutto il documento.
    - I termini specifici corrispondono a **parole intere** (ignorando
      maiuscole e punteggiatura), non a frammenti.

    **Limiti:**
    - L'OCR può perdere parole con scansioni di bassa qualità.
    - Nomi inusuali possono sfuggire — usa sempre i "termini specifici" per certezza.
    - Date disabilitate di default perché spesso rilevanti nei documenti legali.
    - Per documenti che contengono firme scansionate, foto di documenti d'identità o timbri all'interno di pagine altrimenti testuali, usa la modalità **"Forza OCR su tutto"**.
    - Le filigrane diagonali (es. "copia comunicata ai soli fini...") possono
      perdere le lettere che attraversano fisicamente un'area oscurata.

    **Workflow:**
    1. Carica PDF
    2. Lascia i flag predefiniti per documenti italiani
    3. Aggiungi nei "termini specifici" nomi/società da oscurare con certezza
    4. Scegli modalità OCR (Auto va bene per testo puro; Forza OCR per documenti con immagini)
    5. Anonimizza
    6. **Verifica sempre il PDF risultante** prima dell'invio
    """)
