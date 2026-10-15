"""
Módulo de Auditoría Bibliográfica y de Integridad de Citas para Tesis en PDF (Quirón).
=====================================================================================
Audita la integridad bibliográfica en dos niveles:
1. Auditoría Interna:
   - Cruce entre citas en el cuerpo del documento vs. sección de Referencias.
   - Detección de "Citas huérfanas" (citadas en texto pero ausentes al final).
   - Detección de "Referencias de relleno" (declaradas al final pero jamás citadas).
2. Auditoría Externa:
   - Verificación de existencia formal en la API pública de Crossref.
   - Recuperación de metadatos reales (título, autores, año, DOI, abstract).
   - Contrastación con LLM Gemini (google-genai) para evaluar si la afirmación del
     estudiante coincide o tergiversa lo que la fuente afirma.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import re
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

# Configuración de Logging
logger = logging.getLogger("CitationAuditor")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

CROSSREF_USER_AGENT = "QuironThesisAuditor/1.0 (mailto:quiron_auditor@uaq.mx)"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


# ============================================================================
# CONTRATOS DE DATOS
# ============================================================================

@dataclass
class BodyCitation:
    """Representa una cita encontrada dentro del cuerpo de la tesis."""
    raw_citation: str
    citation_type: str  # 'numeric' (ej. [1], [1, 2]) o 'author_year' (ej. Smith (2020), (Smith, 2020))
    normalized_keys: List[str]  # Claves normalizadas para matching (ej. ['1'] o ['smith_2020'])
    page: int
    context_sentence: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ParsedReference:
    """Entrada estructurada de una referencia bibliográfica final."""
    ref_id: str  # Ej. '1' o 'smith_2020'
    raw_ref: str
    authors: List[str] = field(default_factory=list)
    year: str = ""
    title: str = ""
    doi: str = ""
    page: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# 1. EXTRACCIÓN Y SEGMENTACIÓN DE CITAS Y REFERENCIAS
# ============================================================================

REFERENCES_HEADER_REGEX = re.compile(
    r"^(?:\d+[\.\s]*)?(?:referencias\s+bibliogr[aá]ficas|referencias|bibliograf[ií]a|fuentes\s+consultadas|literature\s+cited)\s*$",
    re.I
)

# Patrones para citas en el cuerpo
NUMERIC_CITATION_RE = re.compile(r"\[([0-9\s,\-]+)\]")
AUTHOR_YEAR_PAREN_RE = re.compile(
    r"\(([A-ZÁÉÍÓÚ][a-záéíóúñA-ZÁÉÍÓÚ]+(?:\s+et\s+al\.?|\s+y\s+[A-ZÁÉÍÓÚ][a-záéíóúñ]+)?),\s*([12][0-9]{3}[a-z]?)\)"
)
AUTHOR_YEAR_INLINE_RE = re.compile(
    r"\b([A-ZÁÉÍÓÚ][a-záéíóúñA-ZÁÉÍÓÚ]+(?:\s+et\s+al\.?|\s+y\s+[A-ZÁÉÍÓÚ][a-záéíóúñ]+)?)\s*\(([12][0-9]{3}[a-z]?)\)"
)

DOI_REGEX = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")


def extract_citations_and_references(text: str, page_map: Optional[List[Tuple[int, str]]] = None) -> dict:
    """
    Separa el texto en 'cuerpo del documento' y 'lista de referencias',
    extrayendo las citas en texto y estructurando las referencias finales.

    Args:
        text: Texto completo del documento (o concatenación de páginas).
        page_map: Opcional, lista de tuplas (num_pagina, texto_pagina).

    Returns:
        dict: {
            'body_text': str,
            'references_text': str,
            'references_start_page': int,
            'body_citations': List[dict],
            'final_references': List[dict]
        }
    """
    ref_start_idx = -1
    ref_start_page = 1

    if page_map:
        # Búsqueda por página reversa para encontrar el encabezado de referencias
        for page_num, p_text in reversed(page_map):
            for line in p_text.splitlines():
                if REFERENCES_HEADER_REGEX.match(line.strip()):
                    ref_start_page = page_num
                    break
            if ref_start_page > 1:
                break

    # Si no se detectó por página o no hay page_map, buscar por regex sobre líneas
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        clean = line.strip()
        if len(clean) < 40 and REFERENCES_HEADER_REGEX.match(clean):
            ref_start_idx = idx
            break

    if ref_start_idx != -1:
        body_text = "\n".join(lines[:ref_start_idx])
        refs_text = "\n".join(lines[ref_start_idx:])
    else:
        # Fallback heurístico: buscar la última aparición de la palabra 'Referencias'
        matches = list(re.finditer(r"\n\s*(?:Referencias|Bibliografía)\s*\n", text, re.I))
        if matches:
            last_match = matches[-1]
            body_text = text[:last_match.start()]
            refs_text = text[last_match.start():]
        else:
            body_text = text
            refs_text = ""

    body_citations = _extract_body_citations(body_text, page_map, ref_start_page)
    final_references = _parse_references_section(refs_text, ref_start_page)

    return {
        "body_text": body_text,
        "references_text": refs_text,
        "references_start_page": ref_start_page,
        "body_citations": [c.to_dict() for c in body_citations],
        "final_references": [r.to_dict() for r in final_references],
    }


def _extract_body_citations(
    body_text: str, page_map: Optional[List[Tuple[int, str]]], ref_start_page: int
) -> List[BodyCitation]:
    """Extrae todas las citas (numéricas y autor-año) junto con su página y oración circundante."""
    citations: List[BodyCitation] = []

    # Procesar página a página si page_map está disponible
    if page_map:
        for page_num, p_text in page_map:
            if page_num >= ref_start_page and ref_start_page > 1:
                break
            citations.extend(_scan_text_for_citations(p_text, page_num))
    else:
        citations.extend(_scan_text_for_citations(body_text, 1))

    return citations


def _scan_text_for_citations(text: str, page: int) -> List[BodyCitation]:
    found: List[BodyCitation] = []

    # 1. Citas Numéricas: [1], [2, 3], [4-7]
    for m in NUMERIC_CITATION_RE.finditer(text):
        raw = m.group(0)
        inner = m.group(1).strip()
        keys = []
        for part in re.split(r"[,;]", inner):
            part = part.strip()
            if "-" in part:
                range_parts = part.split("-")
                if len(range_parts) == 2 and range_parts[0].isdigit() and range_parts[1].isdigit():
                    start_i, end_i = int(range_parts[0]), int(range_parts[1])
                    if end_i >= start_i and (end_i - start_i) <= 20:
                        keys.extend([str(k) for k in range(start_i, end_i + 1)])
            elif part.isdigit():
                keys.append(part)

        if keys:
            start_ctx = max(0, m.start() - 100)
            end_ctx = min(len(text), m.end() + 100)
            context_sentence = text[start_ctx:end_ctx].replace("\n", " ").strip()
            found.append(BodyCitation(
                raw_citation=raw,
                citation_type="numeric",
                normalized_keys=keys,
                page=page,
                context_sentence=context_sentence,
            ))

    # 2. Citas Autor-Año Parentéticas: (Pérez, 2020), (Smith et al., 2019)
    for m in AUTHOR_YEAR_PAREN_RE.finditer(text):
        raw = m.group(0)
        author = m.group(1).strip()
        year = m.group(2).strip()
        norm_key = _normalize_author_year_key(author, year)
        start_ctx = max(0, m.start() - 100)
        end_ctx = min(len(text), m.end() + 100)
        context_sentence = text[start_ctx:end_ctx].replace("\n", " ").strip()
        found.append(BodyCitation(
            raw_citation=raw,
            citation_type="author_year",
            normalized_keys=[norm_key],
            page=page,
            context_sentence=context_sentence,
        ))

    # 3. Citas Autor-Año Narrativas: Pérez (2020) observó que...
    for m in AUTHOR_YEAR_INLINE_RE.finditer(text):
        raw = m.group(0)
        author = m.group(1).strip()
        year = m.group(2).strip()
        norm_key = _normalize_author_year_key(author, year)
        start_ctx = max(0, m.start() - 100)
        end_ctx = min(len(text), m.end() + 100)
        context_sentence = text[start_ctx:end_ctx].replace("\n", " ").strip()
        found.append(BodyCitation(
            raw_citation=raw,
            citation_type="author_year",
            normalized_keys=[norm_key],
            page=page,
            context_sentence=context_sentence,
        ))

    return found


def _normalize_author_year_key(author: str, year: str) -> str:
    """Normaliza un autor y año a una clave canónica (ej. 'langhorne_2011')."""
    first_author = re.split(r"\s+et\s+al|\s+y\s+", author, flags=re.I)[0]
    first_author = re.sub(r"[^a-zA-ZáéíóúñÁÉÍÓÚÑ]", "", first_author).lower()
    year_digits = re.sub(r"\D", "", year)
    return f"{first_author}_{year_digits}"


def _parse_references_section(refs_text: str, start_page: int) -> List[ParsedReference]:
    """Segmenta y parsea cada entrada individual de la lista final de referencias."""
    if not refs_text.strip():
        return []

    entries: List[ParsedReference] = []

    # Detectar formato de lista: ¿es numérica [1] o párrafos con sangría francesa?
    has_numeric = bool(re.search(r"^\s*\[\d+\]", refs_text, re.MULTILINE))

    if has_numeric:
        raw_items = re.split(r"(?=\n\s*\[\d+\])", "\n" + refs_text)
        for item in raw_items:
            item_clean = item.strip()
            if not item_clean:
                continue
            m_num = re.match(r"^\[(\d+)\]\s*(.*)", item_clean, re.DOTALL)
            if m_num:
                ref_id = m_num.group(1)
                content = m_num.group(2).strip().replace("\n", " ")
                ref_obj = _parse_single_reference(content, ref_id=ref_id, page=start_page)
                entries.append(ref_obj)
    else:
        # Párrafos separados por líneas en blanco o sangría
        raw_items = re.split(r"\n\s*\n", refs_text)
        for idx, item in enumerate(raw_items):
            item_clean = item.strip().replace("\n", " ")
            if len(item_clean) < 25:
                continue
            ref_obj = _parse_single_reference(item_clean, ref_id=str(idx + 1), page=start_page)
            entries.append(ref_obj)

    return entries


def _parse_single_reference(content: str, ref_id: str, page: int) -> ParsedReference:
    """Extrae autores, año, título aproximado y DOI de una cita individual."""
    # Normalizar comillas y caracteres especiales de LaTeX (0x10, 0x11, comillas tipográficas)
    normalized = content.replace("\x10", '"').replace("\x11", '"')
    normalized = normalized.replace("\x15", "-").replace("\x1c", "fi").replace("\x1d", "fl")
    normalized = normalized.replace("“", '"').replace("”", '"').replace("«", '"').replace("»", '"')

    doi = ""
    m_doi = DOI_REGEX.search(normalized)
    if m_doi:
        doi = m_doi.group(0).rstrip(".")

    # Extracción de año (4 dígitos entre 1900 y 2099)
    year = ""
    m_year = re.search(r"\b(19\d\d|20\d\d)\b", normalized)
    if m_year:
        year = m_year.group(1)

    # Autores y Título heurísticos
    authors: List[str] = []
    title = ""

    # Caso típico IEEE/APA: Autores, "Título del artículo", Revista/Libro, Año.
    m_quotes = re.search(r'"([^"]{4,})"', normalized)
    if m_quotes:
        title = m_quotes.group(1).strip()
        authors_part = normalized[:m_quotes.start()].strip().rstrip(",").rstrip(".")
        if authors_part:
            authors = [a.strip() for a in re.split(r",\s*(?:and|y)?\s*", authors_part) if a.strip()]
    else:
        # División por puntos o comas
        parts = [p.strip() for p in normalized.split(".") if p.strip()]
        if len(parts) >= 2:
            authors_part = parts[0]
            authors = [a.strip() for a in re.split(r",\s*(?:and|y)?\s*", authors_part) if a.strip()]
            title = parts[1]
        elif len(parts) == 1:
            title = parts[0]

    if not title:
        title = normalized[:150]

    return ParsedReference(
        ref_id=ref_id,
        raw_ref=normalized,
        authors=authors,
        year=year,
        title=title,
        doi=doi,
        page=page,
    )


# ============================================================================
# 2. AUDITORÍA DE CONSISTENCIA INTERNA (Cruce Citas vs Referencias)
# ============================================================================

def audit_internal_consistency(body_citations: List[dict], final_references: List[dict]) -> dict:
    """
    Identifica:
    - Citas huérfanas: citadas en el cuerpo pero ausentes en la bibliografía final.
    - Referencias de relleno: declaradas en la lista final pero jamás citadas en el texto.
    """
    # 1. Indexar referencias finales por ref_id (numérico) y clave autor_año
    ref_ids_declared: Set[str] = set()
    author_year_declared: Set[str] = set()
    ref_lookup: Dict[str, dict] = {}

    for ref in final_references:
        rid = str(ref.get("ref_id", "")).strip()
        if rid:
            ref_ids_declared.add(rid)
            ref_lookup[rid] = ref

        year = str(ref.get("year", "")).strip()
        authors = ref.get("authors", [])
        if authors and year:
            first_a = authors[0]
            key = _normalize_author_year_key(first_a, year)
            author_year_declared.add(key)
            ref_lookup[key] = ref

    # 2. Analizar citas del cuerpo
    orphan_citations: List[dict] = []
    cited_declared_refs: Set[str] = set()

    for cite in body_citations:
        c_type = cite.get("citation_type")
        keys = cite.get("normalized_keys", [])
        raw = cite.get("raw_citation", "")
        page = cite.get("page", 1)
        sentence = cite.get("context_sentence", "")

        is_found = False
        for k in keys:
            if c_type == "numeric":
                if k in ref_ids_declared:
                    is_found = True
                    cited_declared_refs.add(k)
            elif c_type == "author_year":
                if k in author_year_declared:
                    is_found = True
                    cited_declared_refs.add(k)
                else:
                    # Intento de matching por similitud difusa si no es exacto
                    for dec_k in author_year_declared:
                        if difflib.SequenceMatcher(None, k, dec_k).ratio() > 0.8:
                            is_found = True
                            cited_declared_refs.add(dec_k)
                            break

        if not is_found:
            orphan_citations.append({
                "raw_citation": raw,
                "citation_type": c_type,
                "page": page,
                "context_sentence": sentence,
                "problem": "Cita huérfana: La fuente no existe en la sección de referencias final.",
            })

    # 3. Analizar referencias no citadas (relleno)
    filler_references: List[dict] = []
    for ref in final_references:
        rid = str(ref.get("ref_id", "")).strip()
        year = str(ref.get("year", "")).strip()
        authors = ref.get("authors", [])
        key = _normalize_author_year_key(authors[0], year) if (authors and year) else ""

        is_cited = (rid in cited_declared_refs) or (key and key in cited_declared_refs)
        if not is_cited:
            filler_references.append({
                "ref_id": rid,
                "raw_ref": ref.get("raw_ref", ""),
                "title": ref.get("title", ""),
                "year": year,
                "authors": authors,
                "page": ref.get("page", 1),
                "problem": "Referencia de relleno: Declarada en la bibliografía final pero jamás citada en el cuerpo del texto.",
            })

    total_citations = len(body_citations)
    total_references = len(final_references)
    consistency_rate = (
        round(((total_references - len(filler_references)) / total_references) * 100, 2)
        if total_references > 0 else 0.0
    )

    return {
        "total_body_citations": total_citations,
        "total_declared_references": total_references,
        "orphan_count": len(orphan_citations),
        "filler_count": len(filler_references),
        "consistency_rate_pct": consistency_rate,
        "orphan_citations": orphan_citations,
        "filler_references": filler_references,
    }


# ============================================================================
# 3. AUDITORÍA EXTERNA: VERIFICACIÓN CON API DE CROSSREF
# ============================================================================

def verify_external_crossref(title_or_doi: str, timeout_seconds: int = 8) -> dict:
    """
    Realiza una petición gratuita a la API de Crossref (usando el pool rápido 'polite').
    Verifica existencia de la obra y recupera metadatos reales y abstract si está disponible.

    Args:
        title_or_doi: Título del artículo o DOI (ej. '10.1016/...').
        timeout_seconds: Timeout de red para evitar colgar la aplicación.

    Returns:
        dict: {
            'exists': bool,
            'doi': str,
            'real_title': str,
            'real_authors': list,
            'real_year': str,
            'abstract': str or None,
            'similarity': float
        }
    """
    result_default = {
        "exists": False,
        "doi": "",
        "real_title": "",
        "real_authors": [],
        "real_year": "",
        "abstract": None,
        "similarity": 0.0,
    }

    clean_query = title_or_doi.strip()
    if not clean_query:
        return result_default

    headers = {"User-Agent": CROSSREF_USER_AGENT}

    # Caso 1: Búsqueda directa por DOI
    m_doi = DOI_REGEX.search(clean_query)
    if m_doi or clean_query.startswith("10."):
        exact_doi = m_doi.group(0) if m_doi else clean_query
        url = f"https://api.crossref.org/works/{urllib.parse.quote(exact_doi)}"
        try:
            r = requests.get(url, headers=headers, timeout=timeout_seconds)
            if r.status_code == 200:
                item = r.json().get("message", {})
                return _parse_crossref_item(item, clean_query)
        except Exception as err:
            logger.warning("Error de red consultando DOI en Crossref (%s): %s", exact_doi, err)

    # Caso 2: Búsqueda bibliográfica por título
    url = f"https://api.crossref.org/works?query.bibliographic={urllib.parse.quote(clean_query)}&rows=1"
    try:
        r = requests.get(url, headers=headers, timeout=timeout_seconds)
        if r.status_code != 200:
            logger.warning("Respuesta no exitosa de Crossref (HTTP %d)", r.status_code)
            return result_default

        items = r.json().get("message", {}).get("items", [])
        if not items:
            return result_default

        item = items[0]
        return _parse_crossref_item(item, clean_query)

    except requests.Timeout:
        logger.warning("Timeout agotado al contactar Crossref para query: '%s'", clean_query[:50])
        return result_default
    except Exception as err:
        logger.warning("Falla al consultar Crossref: %s", err)
        return result_default


def _parse_crossref_item(item: dict, original_query: str) -> dict:
    """Extrae metadatos limpios de un elemento devuelto por Crossref."""
    titles = item.get("title", [])
    real_title = titles[0] if titles else ""
    doi = item.get("DOI", "")

    # Autores
    real_authors: List[str] = []
    for a in item.get("author", []):
        family = a.get("family", "")
        given = a.get("given", "")
        if family and given:
            real_authors.append(f"{given} {family}")
        elif family:
            real_authors.append(family)

    # Año de publicación
    real_year = ""
    pub_date = item.get("published-print") or item.get("published-online") or item.get("created")
    if pub_date:
        parts = pub_date.get("date-parts", [[]])[0]
        if parts:
            real_year = str(parts[0])

    # Abstract (puede venir con tags JATS XML como <jats:p>)
    raw_abstract = item.get("abstract")
    clean_abstract = None
    if raw_abstract:
        clean_abstract = re.sub(r"<[^>]+>", " ", raw_abstract)
        clean_abstract = re.sub(r"\s+", " ", clean_abstract).strip()

    # Cálculo de similitud entre títulos
    similarity = difflib.SequenceMatcher(
        None,
        original_query.lower(),
        real_title.lower()
    ).ratio()

    # Se considera válida si coincide por DOI o tiene similitud >= 0.55
    exists = bool(doi) and (similarity >= 0.50 or DOI_REGEX.search(original_query) is not None)

    return {
        "exists": exists,
        "doi": doi,
        "real_title": real_title,
        "real_authors": real_authors,
        "real_year": real_year,
        "abstract": clean_abstract,
        "similarity": round(similarity, 3),
    }


# ============================================================================
# 4. CONTRASTACIÓN DE AFIRMACIÓN CON GEMINI (Verificación de Tergiversación)
# ============================================================================

CLAIM_ALIGNMENT_PROMPT = """Eres un Auditor Científico y Revisor Académico Estricto.
Tu tarea es evaluar si la afirmación o conclusión que un estudiante de tesis realiza en su documento está debidamente respaldada por el abstract oficial de la fuente científica citada, o si por el contrario tergiversa, falsea o sobreinterpreta la fuente.

[AFIRMACIÓN DEL ESTUDIANTE EN LA TESIS]
"{student_claim}"

[ABSTRACT OFICIAL DE LA FUENTE CIENTÍFICA RECUPERADO DE CROSSREF]
"{retrieved_abstract}"

[CRITERIOS DE EVALUACIÓN]
- SUPPORTED: El abstract respalda de forma directa, cualitativa o cuantitativamente la afirmación del estudiante.
- CONTRADICTED: El abstract contradice explícitamente lo que afirma el estudiante, o el estudiante atribuye hallazgos o conclusiones falsas que la fuente no obtuvo.
- UNVERIFIABLE: El abstract no contiene suficiente información para confirmar o desmentir la afirmación (ej. el abstract es muy breve o la afirmación corresponde a un detalle interno del artículo).

[REGLAS ESTRICTAS DE RESPUESTA]
Devuelve ÚNICAMENTE un objeto JSON válido con la siguiente estructura, sin texto adicional ni bloques markdown:
{{
  "verdict": "SUPPORTED" | "CONTRADICTED" | "UNVERIFIABLE",
  "confidence": 0.0 a 1.0,
  "explanation": "Explicación académica clara del veredicto en español (máx 3 oraciones)."
}}
"""


def evaluate_claim_alignment(client_gemini: Any, student_claim: str, retrieved_abstract: str) -> dict:
    """
    Evalúa mediante Gemini si la afirmación del estudiante coincide con la fuente real.

    Args:
        client_gemini: Instancia de google.genai.Client o None.
        student_claim: Oración o párrafo del estudiante donde cita la fuente.
        retrieved_abstract: Abstract oficial de la fuente científica recuperado de Crossref.

    Returns:
        dict: {"verdict": "SUPPORTED" | "CONTRADICTED" | "UNVERIFIABLE", "confidence": float, "explanation": str}
    """
    default_response = {
        "verdict": "UNVERIFIABLE",
        "confidence": 0.5,
        "explanation": "No se proporcionó abstract válido para contrastar la afirmación.",
    }

    if not retrieved_abstract or len(retrieved_abstract.strip()) < 30:
        return default_response

    if not student_claim or len(student_claim.strip()) < 10:
        default_response["explanation"] = "La afirmación del estudiante es demasiado breve para auditar."
        return default_response

    prompt = CLAIM_ALIGNMENT_PROMPT.format(
        student_claim=student_claim.strip(),
        retrieved_abstract=retrieved_abstract.strip(),
    )

    try:
        from corrector import gemini_rate_limiter
    except Exception:
        gemini_rate_limiter = None

    try:
        # 1. Intento vía google-genai Client oficial
        if client_gemini is not None and hasattr(client_gemini, "models"):
            if gemini_rate_limiter:
                gemini_rate_limiter.wait()
            response = client_gemini.models.generate_content(
                model=DEFAULT_GEMINI_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                }
            )
            raw_text = response.text.strip()
        else:
            # Fallback a variable de entorno GEMINI_API_KEY vía REST directo si no hay client
            api_key = os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                default_response["explanation"] = "Sin cliente Gemini ni GEMINI_API_KEY configurada para verificación."
                return default_response

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{DEFAULT_GEMINI_MODEL}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                }
            }
            max_retries = 5
            for attempt in range(max_retries):
                if gemini_rate_limiter:
                    gemini_rate_limiter.wait()
                r = requests.post(url, json=payload, timeout=20)
                if r.status_code in [429, 500, 502, 503, 504]:
                    retry_after = r.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else (6.0 * (attempt + 1))
                    logger.warning("HTTP %d en Gemini API. Pausando %.1fs...", r.status_code, delay)
                    time.sleep(delay)
                    continue
                r.raise_for_status()
                break
            else:
                r.raise_for_status()
            data = r.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Parsear respuesta JSON limpia
        if "```" in raw_text:
            m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw_text)
            raw_text = m.group(1) if m else raw_text

        parsed = json.loads(raw_text)
        verdict = str(parsed.get("verdict", "UNVERIFIABLE")).upper()
        if verdict not in ("SUPPORTED", "CONTRADICTED", "UNVERIFIABLE"):
            verdict = "UNVERIFIABLE"

        return {
            "verdict": verdict,
            "confidence": float(parsed.get("confidence", 0.7)),
            "explanation": str(parsed.get("explanation", "")).strip(),
        }

    except Exception as err:
        logger.warning("Falla al contrastar afirmación con Gemini: %s", err)
        default_response["explanation"] = f"Error al invocar Gemini: {err}"
        return default_response


# ============================================================================
# 5. ORQUESTADOR PRINCIPAL: AUDITORÍA INTEGRAL DE TESIS
# ============================================================================

def run_citation_audit(
    pdf_path: str | Path,
    gemini_api_key: Optional[str] = None,
    max_external_verifications: int = 15,
) -> dict:
    """
    Orquesta la auditoría bibliográfica completa de un PDF:
    1. Extracción con PyMuPDF mapeando texto y páginas.
    2. Segmentación del cuerpo y referencias finales.
    3. Auditoría de consistencia interna (citas huérfanas y relleno).
    4. Auditoría externa en Crossref de hasta max_external_verifications referencias.
    5. Evaluación con Gemini de tergiversación de afirmaciones si se cuenta con abstract.

    Args:
        pdf_path: Ruta al archivo PDF de la tesis.
        gemini_api_key: Opcional API Key de Gemini para evaluación de afirmaciones.
        max_external_verifications: Límite de consultas a Crossref para evitar saturación.

    Returns:
        dict: Reporte consolidado con métricas, inconsistencias y contrastaciones.
    """
    if fitz is None:
        raise ImportError("PyMuPDF no está disponible en el entorno.")

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF no encontrado: {pdf_file}")

    # Configurar API Key si se proporcionó
    client_gemini = None
    if gemini_api_key:
        os.environ["GEMINI_API_KEY"] = gemini_api_key
        try:
            from google import genai
            client_gemini = genai.Client(api_key=gemini_api_key)
        except Exception as e:
            logger.info("google.genai.Client no instanciado directamente (%s), usando REST fallback.", e)

    logger.info("Iniciando auditoría de citas y referencias para: %s", pdf_file.name)

    # 1. Extracción página por página
    doc = fitz.open(pdf_file)
    page_map: List[Tuple[int, str]] = []
    full_text_chunks: List[str] = []

    for idx in range(len(doc)):
        page_num = idx + 1
        p_text = doc[idx].get_text()
        page_map.append((page_num, p_text))
        full_text_chunks.append(f"--- PÁGINA {page_num} ---\n{p_text}")
    doc.close()

    full_document_text = "\n\n".join(full_text_chunks)

    # 2. Extracción de citas y referencias
    extracted = extract_citations_and_references(full_document_text, page_map=page_map)
    body_citations = extracted["body_citations"]
    final_references = extracted["final_references"]

    # 3. Auditoría Interna
    internal_audit = audit_internal_consistency(body_citations, final_references)

    # 4. Auditoría Externa (Crossref + Gemini)
    external_verifications: List[dict] = []
    # Seleccionar las primeras referencias o las más completas
    refs_to_verify = final_references[:max_external_verifications]

    # Mapear citas del cuerpo por ref_id para contrastar su afirmación asociada
    citation_by_id: Dict[str, dict] = {}
    for c in body_citations:
        for k in c.get("normalized_keys", []):
            if k not in citation_by_id:
                citation_by_id[k] = c

    logger.info("Verificando %d referencias en la API de Crossref...", len(refs_to_verify))

    for idx, ref in enumerate(refs_to_verify):
        query_term = ref.get("doi") or ref.get("title") or ref.get("raw_ref", "")
        rid = ref.get("ref_id", str(idx + 1))

        # Consulta Crossref
        crossref_data = verify_external_crossref(query_term)
        time.sleep(0.4)  # Respetar rate limit de Crossref

        claim_eval = None
        # Si se recuperó un abstract y la referencia fue citada con contexto en el cuerpo:
        matched_citation = citation_by_id.get(rid)
        if crossref_data["exists"] and crossref_data.get("abstract") and matched_citation:
            student_sentence = matched_citation.get("context_sentence", "")
            claim_eval = evaluate_claim_alignment(
                client_gemini=client_gemini,
                student_claim=student_sentence,
                retrieved_abstract=crossref_data["abstract"],
            )

        external_verifications.append({
            "ref_id": rid,
            "raw_ref": ref.get("raw_ref", ""),
            "searched_query": query_term[:100],
            "crossref_match": crossref_data,
            "claim_alignment": claim_eval,
            "citation_context": matched_citation.get("context_sentence", "") if matched_citation else None,
            "citation_page": matched_citation.get("page") if matched_citation else None,
        })

    # Resumen y métricas de integridad externa
    verified_count = sum(1 for v in external_verifications if v["crossref_match"]["exists"])
    contradicted_count = sum(
        1 for v in external_verifications
        if v.get("claim_alignment") and v["claim_alignment"].get("verdict") == "CONTRADICTED"
    )

    report = {
        "file_name": pdf_file.name,
        "total_pages": len(page_map),
        "references_start_page": extracted["references_start_page"],
        "internal_consistency": internal_audit,
        "external_audit": {
            "total_audited_external": len(external_verifications),
            "verified_in_crossref": verified_count,
            "contradicted_claims_count": contradicted_count,
            "verifications": external_verifications,
        },
    }

    logger.info(
        "Auditoría bibliográfica completada. Citas huérfanas: %d, Relleno: %d, Crossref verificadas: %d/%d",
        internal_audit["orphan_count"],
        internal_audit["filler_count"],
        verified_count,
        len(external_verifications),
    )

    return report


# ============================================================================
# BLOQUE DEMO / PRUEBA RÁPIDA
# ============================================================================

if __name__ == "__main__":
    import sys
    print("=" * 80)
    print(" AUDITOR DE CITAS Y REFERENCIAS BIBLIOGRÁFICAS (Quirón)")
    print("=" * 80)

    test_pdf = Path("main.pdf")
    if not test_pdf.exists():
        print(f"El archivo '{test_pdf}' no existe en el directorio de trabajo.")
        sys.exit(0)

    audit_result = run_citation_audit(test_pdf, max_external_verifications=5)
    print("\n--- RESUMEN DE AUDITORÍA INTERNA ---")
    int_audit = audit_result["internal_consistency"]
    print(f"Total Citas en Cuerpo: {int_audit['total_body_citations']}")
    print(f"Total Referencias Declaradas: {int_audit['total_declared_references']}")
    print(f"Citas Huérfanas (sin ref final): {int_audit['orphan_count']}")
    print(f"Referencias de Relleno (nunca citadas): {int_audit['filler_count']}")
    print(f"Tasa de Consistencia: {int_audit['consistency_rate_pct']}%\n")

    print("--- RESUMEN DE AUDITORÍA EXTERNA (CROSSREF) ---")
    ext_audit = audit_result["external_audit"]
    print(f"Auditadas: {ext_audit['total_audited_external']}")
    print(f"Verificadas en Crossref: {ext_audit['verified_in_crossref']}")
    print(f"Afirmaciones Contradichas: {ext_audit['contradicted_claims_count']}")
