"""
Anonimizzatore PDF
Basato su Microsoft Presidio + PyMuPDF + Tesseract OCR
Anonimizzazione locale di documenti legali italiani (testo + scansioni).

Versione: 1.1.0
Licenza: GNU AGPL v3.0
"""

import streamlit as st
import fitz  # PyMuPDF
import os
import sys
import logging
from io import BytesIO
from collections import Counter
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

__version__ = "1.1.0"

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
    from PIL import Image, ImageDraw

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
)


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
        try:
            embedded_count = doc.embfile_count()
            # embfile_del lavora per indice o nome; iteriamo a ritroso
            for i in range(embedded_count - 1, -1, -1):
                try:
                    info = doc.embfile_info(i)
                    doc.embfile_del(info["filename"])
                    attachments_removed += 1
                except Exception as e:
                    logger.warning("Rimozione allegato fallita: %s", e)
        except Exception:
            pass

        # 4. JavaScript a livello documento (può eseguire codice all'apertura)
        try:
            js_count = doc.get_js()
            if js_count:
                # Cerca e rimuove ogni JS azione
                for xref in range(1, doc.xref_length()):
                    try:
                        obj = doc.xref_object(xref)
                        if "/JavaScript" in obj or "/JS" in obj:
                            # Sostituisce il contenuto con vuoto
                            doc.update_object(xref, "<< >>")
                            js_removed += 1
                    except Exception:
                        pass
        except Exception:
            pass

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
                        img_area = bbox.width * bbox.height
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

def redact_text_page(page, selected_entities, custom_terms, analyzer, min_score,
                     log, page_num, debug_first=False):
    """Redazione su pagina con testo selezionabile."""
    text = page.get_text()

    if debug_first:
        st.write(f"🔍 Pagina {page_num} (testuale) — primi 200 caratteri: `{text[:200]}`")

    raw_count = 0
    filtered_count = 0

    if text.strip() and selected_entities:
        try:
            all_results = analyzer.analyze(
                text=text,
                entities=selected_entities,
                language="it",
            )
            raw_count = len(all_results)

            if debug_first and all_results:
                debug_sample = [
                    f"{r.entity_type}={text[r.start:r.end][:25]!r}(s={r.score:.2f})"
                    for r in all_results[:6]
                ]
                st.write(f"   Esempi grezzi: {' | '.join(debug_sample)}")

            results = [r for r in all_results if r.score >= min_score]
            filtered_count = len(results)

        except Exception as e:
            # L-03: messaggio sanitizzato, dettagli solo nei log
            st.error(safe_error_message(f"Analisi pagina {page_num}", e))
            results = []

        for result in results:
            found_text = text[result.start:result.end].strip()
            if not found_text or len(found_text) < 2:
                continue
            areas = page.search_for(found_text)
            for area in areas:
                page.add_redact_annot(area, fill=(0, 0, 0))
                log.append({
                    "Pagina": page_num,
                    "Tipo": result.entity_type,
                    "Testo": found_text,
                    "Confidenza": f"{result.score:.0%}",
                    "Metodo": "Testo",
                })

    for term in custom_terms:
        term = term.strip()
        if not term:
            continue
        areas = page.search_for(term)
        for area in areas:
            page.add_redact_annot(area, fill=(0, 0, 0))
            log.append({
                "Pagina": page_num,
                "Tipo": "TERMINE PERSONALIZZATO",
                "Testo": term,
                "Confidenza": "100%",
                "Metodo": "Testo",
            })

    page.apply_redactions()
    return raw_count, filtered_count


# ============================================================
# REDAZIONE PAGINA SCANSIONATA (OCR)
# ============================================================

def process_scanned_page(src_page, out_doc, selected_entities, custom_terms,
                         analyzer, min_score, dpi, lang, log, page_num,
                         debug_first=False):
    """OCR su pagina scansionata + redazione con rettangoli su immagine."""
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
                results = [r for r in all_results if r.score >= min_score]
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

        for result in results:
            matching_idx = [
                idx for start, end, idx in word_positions
                if start < result.end and end > result.start
            ]
            if matching_idx:
                matching = [words[i] for i in matching_idx]
                x_min = min(w["x"] for w in matching)
                y_min = min(w["y"] for w in matching)
                x_max = max(w["x"] + w["w"] for w in matching)
                y_max = max(w["y"] + w["h"] for w in matching)
                pad = 2
                draw.rectangle(
                    [(x_min - pad, y_min - pad), (x_max + pad, y_max + pad)],
                    fill="black",
                )
                log.append({
                    "Pagina": page_num,
                    "Tipo": result.entity_type,
                    "Testo": full_text[result.start:result.end],
                    "Confidenza": f"{result.score:.0%}",
                    "Metodo": "OCR",
                })

        for term in custom_terms:
            term = term.strip()
            if not term:
                continue
            term_words = term.split()
            for i in range(len(words) - len(term_words) + 1):
                match = all(
                    words[i + j]["text"].lower() == term_words[j].lower()
                    for j in range(len(term_words))
                )
                if match:
                    matching = words[i:i + len(term_words)]
                    x_min = min(w["x"] for w in matching)
                    y_min = min(w["y"] for w in matching)
                    x_max = max(w["x"] + w["w"] for w in matching)
                    y_max = max(w["y"] + w["h"] for w in matching)
                    pad = 2
                    draw.rectangle(
                        [(x_min - pad, y_min - pad), (x_max + pad, y_max + pad)],
                        fill="black",
                    )
                    log.append({
                        "Pagina": page_num,
                        "Tipo": "TERMINE PERSONALIZZATO",
                        "Testo": term,
                        "Confidenza": "100%",
                        "Metodo": "OCR",
                    })

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
               min_score=0.4, ocr_mode="auto", ocr_dpi=300, ocr_lang="ita"):
    """
    Anonimizza un PDF. Gestisce sia pagine testuali che scansionate.
    ocr_mode: 'auto' | 'always' | 'never'
    """
    src_doc = fitz.open(stream=input_bytes, filetype="pdf")
    out_doc = fitz.open()
    log = []

    st.write(f"📄 Documento: {len(src_doc)} pagine")
    st.write(f"🎯 Entità cercate ({len(selected_entities)}): {', '.join(selected_entities)}")
    st.write(f"📊 Soglia minima: {min_score:.0%} · Modalità OCR: **{ocr_mode}**")

    total_pages = len(src_doc)
    progress_bar = st.progress(0.0)
    status_text = st.empty()

    total_raw = 0
    total_filtered = 0
    pages_ocr = 0
    pages_text = 0
    pages_with_inline_images = 0

    for page_num, src_page in enumerate(src_doc, start=1):
        progress_bar.progress(page_num / total_pages)

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

        is_first_processed_page = (page_num == 1)

        if use_ocr:
            status_text.text(f"🔍 OCR pagina {page_num}/{total_pages}...")
            raw, filtered = process_scanned_page(
                src_page, out_doc, selected_entities, custom_terms,
                analyzer, min_score, ocr_dpi, ocr_lang, log, page_num,
                debug_first=is_first_processed_page,
            )
            pages_ocr += 1
        else:
            if scanned and not TESSERACT_AVAILABLE:
                status_text.text(f"⚠️ Pagina {page_num}/{total_pages} scansionata ma OCR non disponibile")
            elif has_images and ocr_mode == "auto":
                status_text.text(f"📄 Pagina {page_num}/{total_pages} (⚠️ contiene immagini)")
            else:
                status_text.text(f"📄 Pagina {page_num}/{total_pages}...")

            out_doc.insert_pdf(src_doc, from_page=page_num - 1, to_page=page_num - 1)
            new_page = out_doc[-1]
            raw, filtered = redact_text_page(
                new_page, selected_entities, custom_terms,
                analyzer, min_score, log, page_num,
                debug_first=is_first_processed_page,
            )
            pages_text += 1

        total_raw += raw
        total_filtered += filtered

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
    st.write(f"   Presidio: {total_raw} risultati grezzi → {total_filtered} dopo filtro soglia ≥{min_score:.0%}")

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
    return output_bytes.getvalue(), log


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
if uploaded_file is not None:
    if not selected_entities and not custom_terms:
        st.error("⚠️ Seleziona almeno una categoria nella sidebar o inserisci un termine specifico.")
    else:
        if st.button("🔒 Anonimizza documento", type="primary", use_container_width=True):

            with st.status("Caricamento motore di analisi...", expanded=False) as status:
                analyzer = initialize_analyzer()
                status.update(label="✅ Motore pronto", state="complete")

            input_bytes = uploaded_file.read()
            output_bytes, log = redact_pdf(
                input_bytes,
                selected_entities,
                custom_terms,
                analyzer,
                min_score=min_score,
                ocr_mode=ocr_mode,
                ocr_dpi=ocr_dpi,
                ocr_lang="ita" if ITALIAN_AVAILABLE else "eng",
            )

            if log:
                st.success(f"✅ Anonimizzazione completata: **{len(log)} elementi oscurati**")

                col_a, col_b = st.columns([1, 2])

                with col_a:
                    output_filename = f"anonimizzato_{uploaded_file.name}"
                    st.download_button(
                        label="📥 Scarica PDF anonimizzato",
                        data=output_bytes,
                        file_name=output_filename,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                    )

                with col_b:
                    types_count = Counter(item["Tipo"] for item in log)
                    method_count = Counter(item["Metodo"] for item in log)
                    summary = " · ".join([f"{count} {tipo}" for tipo, count in types_count.most_common()])
                    st.caption(f"**Tipi:** {summary}")
                    st.caption(f"**Metodi:** {dict(method_count)}")

                with st.expander(f"📊 Report completo ({len(log)} redazioni)"):
                    st.dataframe(log, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ Nessuna entità sensibile rilevata. Controlla il riepilogo Presidio sopra.")

# --- FOOTER ---
st.divider()
with st.expander("ℹ️ Informazioni e avvertenze"):
    st.markdown(f"""
    **Versione:** {__version__}
    **Privacy:** tutti i file sono elaborati in locale. Nessun dato esce dal computer.

    **Redazione testo:** rimozione fisica del testo + rettangolo nero (irreversibile).

    **Redazione scansioni (OCR):** il PDF viene rasterizzato e ricostruito come immagine con rettangoli neri (la pagina diventa solo immagine, non selezionabile).

    **Sanitizzazione automatica (v1.1+):** il PDF di output viene ripulito da metadata (autore, titolo), annotazioni, allegati, campi form e JavaScript.

    **Limiti:**
    - L'OCR può perdere parole con scansioni di bassa qualità.
    - Nomi inusuali possono sfuggire — usa sempre i "termini specifici" per certezza.
    - Date disabilitate di default perché spesso rilevanti nei documenti legali.
    - Per documenti che contengono firme scansionate, foto di documenti d'identità o timbri all'interno di pagine altrimenti testuali, usa la modalità **"Forza OCR su tutto"**.

    **Workflow:**
    1. Carica PDF
    2. Lascia i flag predefiniti per documenti italiani
    3. Aggiungi nei "termini specifici" nomi/società da oscurare con certezza
    4. Scegli modalità OCR (Auto va bene per testo puro; Forza OCR per documenti con immagini)
    5. Anonimizza
    6. **Verifica sempre il PDF risultante** prima dell'invio
    """)
