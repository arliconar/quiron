"""
Sistema Automatizado de Revisión de Tesis en PDF con Agentes Especializados
Integración con antigravity-cli (`agy`) en la PC del usuario.
==========================================================================
Módulos:
1. PdfStructuredExtractor: Extracción tipográfica y espacial con PyMuPDF.
2. SectionSplitter: Segmentación semántica por coordenadas y solapamiento.
3. BaseAgyReviewer & Agentes: Ejecución de prompts LLM vía `agy -p`.
4. PdfAnnotator: Inyección visual con fallback por bbox y compresión limpia.
"""

from __future__ import annotations

import os
import json
import logging
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ThesisReviewer-AGY")


# ============================================================================
# CONTRATOS DE DATOS (ReviewSchema)
# ============================================================================

ReviewCategory = Literal[
    "coherencia_objetivos",
    "rigor_metodologico",
    "validacion_resultados",
    "formalismo_tecnico",
]

ReviewSeverity = Literal["sugerencia", "observacion", "critica"]


@dataclass
class ReviewComment:
    """
    Contrato unificado de hallazgos emitidos por agentes revisores.
    Todo agente LLM orquestado por `agy` debe cumplir obligatoriamente esta estructura.
    """
    target_id: str
    page: int  # Base 1
    quote: str
    reviewer_name: str
    category: ReviewCategory
    severity: ReviewSeverity
    comment: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TextBlockMetadata:
    """Metadatos tipográficos y espaciales de cada bloque de texto extraído."""
    target_id: str
    page: int  # Base 1
    block_idx: int  # Base 0 por página
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y2]
    text: str
    avg_font_size: float
    max_font_size: float
    is_bold: bool
    is_heading_candidate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageBlockMetadata:
    """Metadatos espaciales y ruta de imagen extraída/rasterizada."""
    target_id: str
    page: int  # Base 1
    image_idx: int  # Base 0 por página
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y2]
    image_path: str
    caption: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Section:
    """Segmento semántico canónico delimitado espacialmente."""
    canonical_name: str
    heading_title: str
    start_page: int
    start_y0: float
    blocks: List[TextBlockMetadata] = field(default_factory=list)
    overlap_blocks: List[TextBlockMetadata] = field(default_factory=list)
    images: List[ImageBlockMetadata] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Texto propio de la sección con formato [P{page}-B{block_idx}] {texto}."""
        lines = [f"[{b.target_id}] {b.text}" for b in self.blocks]
        if self.images:
            lines.append("\n--- FIGURAS / IMÁGENES ASOCIADAS A ESTE CAPÍTULO ---")
            for img in self.images:
                cap_txt = f" (Leyenda: '{img.caption}')" if img.caption else ""
                lines.append(f"[{img.target_id}] [FIGURA/IMAGEN Pág {img.page}]{cap_txt} Archivo: {img.image_path}")
        return "\n".join(lines)

    @property
    def context_text(self) -> str:
        """Texto con overlap contextual previo + contenido de la sección e imágenes."""
        chunks: List[str] = []
        if self.overlap_blocks:
            chunks.append("--- CONTEXTO PREVIO (SOLAPAMIENTO DE LA SECCIÓN ANTERIOR) ---")
            chunks.extend(f"[{b.target_id}] {b.text}" for b in self.overlap_blocks)
            chunks.append("--- INICIO SECCIÓN AUDITADA ---")
        chunks.extend(f"[{b.target_id}] {b.text}" for b in self.blocks)
        if self.images:
            chunks.append("\n--- FIGURAS / IMÁGENES ASOCIADAS A ESTE CAPÍTULO ---")
            for img in self.images:
                cap_txt = f" (Leyenda: '{img.caption}')" if img.caption else ""
                chunks.append(f"[{img.target_id}] [FIGURA/IMAGEN Pág {img.page}]{cap_txt} Archivo: {img.image_path}")
        return "\n".join(chunks)


# ============================================================================
# CLIENTE WRAPPER PARA ANTIGRAVITY-CLI (`agy`)
# ============================================================================

class AgyClient:
    """
    Wrapper para interactuar con antigravity-cli (`agy`) instalado en la PC.
    Ejecuta agentes en modo headless mediante `agy -p "<prompt>"` y parsea
    la respuesta estructurada en formato JSON hacia instancias de ReviewComment.
    """

    def __init__(self, cli_command: str = "agy", timeout_seconds: int = 120):
        self.cli_command = cli_command
        self.timeout_seconds = timeout_seconds
        self.is_installed = self._check_installation()

    def _check_installation(self) -> bool:
        """Verifica si `agy` está disponible en el PATH del sistema."""
        path_bin = shutil.which(self.cli_command)
        if path_bin:
            logger.info("antigravity-cli detectado en el sistema: %s", path_bin)
            return True
        logger.warning(
            "No se encontró el ejecutable '%s' en el PATH del sistema. "
            "Asegúrate de que antigravity-cli esté instalado y accesible.",
            self.cli_command
        )
        return False

    def query(self, prompt: str) -> str:
        """
        Ejecuta `agy -p "<prompt>"` de forma no interactiva y captura stdout.
        Para evitar desbordamientos de buffer o límites de argumentos en la consola de Windows,
        si el prompt es extenso se almacena en un archivo temporal y se le indica a agy que lo lea.
        """
        if not self.is_installed:
            raise RuntimeError(
                f"antigravity-cli ('{self.cli_command}') no está instalado o no se encuentra en el PATH."
            )

        # Si el prompt es muy largo (> 2000 caracteres), usar archivo temporal para Windows CLI
        temp_file = None
        prompt_arg = prompt
        if len(prompt) > 2000:
            import tempfile
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".txt") as tf:
                tf.write(prompt)
                temp_file = tf.name
            prompt_arg = (
                f"Lee atentamente el archivo completo en: {temp_file}\n"
                f"Sigue todas las instrucciones y reglas descritas en dicho archivo y genera tu respuesta."
            )

        cmd = [self.cli_command, "--dangerously-skip-permissions", "-p", prompt_arg]
        logger.debug("Invocando antigravity-cli: %s", " ".join(cmd[:2]))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout_seconds,
                check=False
            )
        except subprocess.TimeoutExpired as exc:
            logger.error("Tiempo de espera agotado al ejecutar '%s' (%ds)", self.cli_command, self.timeout_seconds)
            raise TimeoutError(f"antigravity-cli excedió el tiempo límite de {self.timeout_seconds}s") from exc
        except Exception as exc:
            logger.error("Error al invocar '%s': %s", self.cli_command, exc)
            raise
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

        if result.returncode != 0:
            err_msg = result.stderr.strip() or result.stdout.strip()
            logger.error("antigravity-cli falló con código %d: %s", result.returncode, err_msg)
            raise RuntimeError(f"Falla en antigravity-cli ({self.cli_command}): {err_msg}")

        return result.stdout.strip()

    def query_json_comments(
        self,
        system_prompt: str,
        reviewer_name: str,
        category: ReviewCategory,
        audited_text: str,
        context_text: Optional[str] = None
    ) -> List[ReviewComment]:
        """
        Estructura el prompt para que `agy` emita exclusivamente un array JSON
        cumpliendo el contrato ReviewComment, y lo deserializa de forma segura.
        """
        json_schema_desc = f"""[
  {{
    "target_id": "P1-B0",
    "page": 1,
    "quote": "frase textual exacta de la auditoria",
    "reviewer_name": "{reviewer_name}",
    "category": "{category}",
    "severity": "sugerencia" | "observacion" | "critica",
    "comment": "Explicacion detallada del problema y recomendacion tecnica de solucion"
  }}
]"""

        full_prompt = f"""[INSTRUCCIONES DE SISTEMA]
{system_prompt}

[REGLAS ESTRICTAS DE SALIDA]
1. Audita el texto e imágenes proporcionados respetando los identificadores de bloque:
   - Bloques de texto: [P{pagina}-B{bloque}]
   - Bloques de figuras/imágenes: [P{pagina}-IMG{indice}]
2. Si un problema reside en una figura/imagen (gráfica errónea, falta de unidades en ejes, diagrama incompleto, discrepancia visual con el texto), utiliza el target_id de la imagen (ej. P17-IMG0), la página correspondiente y en 'quote' la leyenda/título de la figura o el archivo.
3. Para cada problema detectado, extrae el target_id exacto (ej. P1-B0 o P17-IMG0), el número de página como entero, y la quote textual idéntica a como aparece en el texto o pie de figura.
4. El campo 'category' DEBE ser estrictamente "{category}".
5. El campo 'reviewer_name' DEBE ser estrictamente "{reviewer_name}".
6. El campo 'severity' debe ser uno de: "sugerencia", "observacion", "critica".
7. IMPORTANTE: Devuelve ÚNICAMENTE un array JSON válido sin texto previo ni posterior, siguiendo este esquema:
{json_schema_desc}
Si no encuentras ningún problema, devuelve exactamente un array vacío: []
"""

        if context_text and context_text.strip():
            full_prompt += f"\n[CONTEXTO DE REFERENCIA (Capítulos o secciones previas)]\n{context_text.strip()}\n"

        full_prompt += f"\n[TEXTO E IMÁGENES A AUDITAR]\n{audited_text.strip()}\n"

        raw_output = self.query(full_prompt)
        return self._parse_comments(raw_output, default_reviewer=reviewer_name, default_category=category)

    @staticmethod
    def _parse_comments(
        raw_output: str,
        default_reviewer: str,
        default_category: ReviewCategory
    ) -> List[ReviewComment]:
        """Extrae y valida los objetos ReviewComment desde la respuesta de agy."""
        cleaned = raw_output.strip()
        if "```" in cleaned:
            m = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", cleaned)
            if m:
                cleaned = m.group(1).strip()
            else:
                cleaned = re.sub(r"^```(?:json)?|```$", "", cleaned, flags=re.MULTILINE).strip()

        json_match = re.search(r"\[[\s\S]*\]", cleaned)
        if not json_match:
            logger.warning("No se localizó un array JSON en la salida de agy. Salida: %s", raw_output[:150])
            return []

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError as err:
            logger.error("Error al decodificar JSON devuelto por agy: %s", err)
            return []

        comments: List[ReviewComment] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                target_id = str(item.get("target_id", "P1-B0"))
                page = item.get("page")
                if not isinstance(page, int):
                    m_p = re.search(r"P(\d+)", target_id)
                    page = int(m_p.group(1)) if m_p else 1

                quote = str(item.get("quote", "")).strip()
                if not quote:
                    continue

                category = item.get("category", default_category)
                severity = item.get("severity", "observacion")
                if severity not in ("sugerencia", "observacion", "critica"):
                    severity = "observacion"

                comment_txt = str(item.get("comment", "")).strip()

                comments.append(ReviewComment(
                    target_id=target_id,
                    page=page,
                    quote=quote,
                    reviewer_name=str(item.get("reviewer_name", default_reviewer)),
                    category=category,  # type: ignore
                    severity=severity,  # type: ignore
                    comment=comment_txt
                ))
            except Exception as e:
                logger.warning("Error al procesar comentario individual de agy: %s", e)

        return comments


# ============================================================================
# MÓDULO 1: EXTRACTOR ESTRUCTURADO (PdfStructuredExtractor)
# ============================================================================

class PdfStructuredExtractor:
    """
    Recorre el documento PDF página por página extrayendo texto limpio,
    geometría (bbox) y propiedades tipográficas (tamaño y flags de negrita).
    """

    def __init__(self, bold_ratio_threshold: float = 0.4):
        self.bold_ratio_threshold = bold_ratio_threshold

    def extract(
        self, pdf_path: str | Path, images_output_dir: Optional[str | Path] = None
    ) -> Tuple[str, Dict[str, Dict[str, Any]], List[TextBlockMetadata], List[ImageBlockMetadata]]:
        """
        Genera:
        1. String etiquetado: [P{page}-B{block_idx}] {texto}
        2. metadata_index: Diccionario para mapeo inverso {target_id: {...}}
        3. text_blocks: Lista secuencial de objetos TextBlockMetadata
        4. image_blocks: Lista secuencial de objetos ImageBlockMetadata con archivos PNG renderizados
        """
        if fitz is None:
            raise ImportError("PyMuPDF (fitz) es requerido pero no está instalado.")

        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {pdf_file}")

        if images_output_dir is None:
            img_dir = pdf_file.parent / ".quiron_thesis_images"
        else:
            img_dir = Path(images_output_dir)
        img_dir.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(pdf_file)
        total_pages = len(doc)
        labeled_lines: List[str] = []
        metadata_index: Dict[str, Dict[str, Any]] = {}
        all_blocks: List[TextBlockMetadata] = []
        all_images: List[ImageBlockMetadata] = []

        try:
            for page_index in range(total_pages):
                page_num = page_index + 1  # Base 1
                page = doc[page_index]
                page_dict = page.get_text("dict")

                raw_blocks = page_dict.get("blocks", [])
                text_block_idx = 0
                page_text_blocks: List[TextBlockMetadata] = []

                # 1. Extraer bloques de texto
                for raw_block in raw_blocks:
                    if raw_block.get("type", 0) != 0:
                        continue

                    block_text_lines: List[str] = []
                    font_sizes: List[float] = []
                    bold_spans = 0
                    total_spans = 0

                    for line in raw_block.get("lines", []):
                        line_parts = []
                        for span in line.get("spans", []):
                            txt = span.get("text", "").strip()
                            if not txt:
                                continue
                            line_parts.append(txt)

                            size = float(span.get("size", 10.0))
                            font_sizes.append(size)

                            flags = span.get("flags", 0)
                            font_name = span.get("font", "").lower()
                            is_bold = bool((flags & 16 != 0) or ("bold" in font_name) or ("black" in font_name))
                            if is_bold:
                                bold_spans += 1
                            total_spans += 1

                        if line_parts:
                            block_text_lines.append(" ".join(line_parts))

                    clean_text = " ".join(block_text_lines).strip()
                    clean_text = re.sub(r"\s+", " ", clean_text)
                    if not clean_text:
                        continue

                    target_id = f"P{page_num}-B{text_block_idx}"
                    bbox = tuple(float(c) for c in raw_block.get("bbox", (0.0, 0.0, 0.0, 0.0)))
                    avg_size = sum(font_sizes) / len(font_sizes) if font_sizes else 10.0
                    max_size = max(font_sizes) if font_sizes else 10.0
                    is_predominantly_bold = (bold_spans / total_spans >= self.bold_ratio_threshold) if total_spans else False

                    is_heading = (max_size >= 14.5) or (is_predominantly_bold and max_size >= 12.0)

                    block_meta = TextBlockMetadata(
                        target_id=target_id,
                        page=page_num,
                        block_idx=text_block_idx,
                        bbox=bbox,  # type: ignore
                        text=clean_text,
                        avg_font_size=round(avg_size, 2),
                        max_font_size=round(max_size, 2),
                        is_bold=is_predominantly_bold,
                        is_heading_candidate=is_heading,
                    )

                    all_blocks.append(block_meta)
                    page_text_blocks.append(block_meta)
                    metadata_index[target_id] = block_meta.to_dict()
                    labeled_lines.append(f"[{target_id}] {clean_text}")

                    text_block_idx += 1

                # 2. Extraer imágenes/figuras de la página
                page_imgs = page.get_images()
                img_idx = 0
                for img_info in page_imgs:
                    xref = img_info[0]
                    rects = page.get_image_rects(xref)
                    if not rects:
                        continue
                    for rect in rects:
                        # Filtrar miniaturas o elementos decorativos muy pequeños (< 40x40 pt)
                        if rect.width < 40 or rect.height < 40:
                            continue

                        img_target_id = f"P{page_num}-IMG{img_idx}"
                        img_filename = f"page_{page_num}_img_{img_idx}.png"
                        img_path = img_dir / img_filename

                        # Renderizar recorte de la imagen a alta resolución
                        try:
                            # Renderizar la región exacta
                            pix = page.get_pixmap(clip=rect, dpi=150)
                            pix.save(str(img_path))
                        except Exception:
                            # Fallback: extraer stream directo
                            try:
                                base_image = doc.extract_image(xref)
                                image_bytes = base_image["image"]
                                with open(img_path, "wb") as f_out:
                                    f_out.write(image_bytes)
                            except Exception as ex:
                                logger.warning("No se pudo extraer imagen xref %d: %s", xref, ex)
                                continue

                        # Buscar pie de figura más cercano debajo de la imagen (y0 > rect.y1)
                        caption = ""
                        candidate_captions = [
                            b for b in page_text_blocks
                            if b.bbox[1] >= (rect.y1 - 10) and b.bbox[1] <= (rect.y1 + 100)
                        ]
                        for cand in candidate_captions:
                            if re.search(r"^\s*(?:figura|fig\.|gr[aá]fica|diagrama)\s*\d+", cand.text, re.I):
                                caption = cand.text
                                break
                        if not caption and candidate_captions:
                            # Usar el texto inmediato siguiente si es breve (< 120 caracteres)
                            first_cand = candidate_captions[0]
                            if len(first_cand.text) <= 120:
                                caption = first_cand.text

                        img_meta = ImageBlockMetadata(
                            target_id=img_target_id,
                            page=page_num,
                            image_idx=img_idx,
                            bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                            image_path=str(img_path.resolve()),
                            caption=caption
                        )
                        all_images.append(img_meta)
                        metadata_index[img_target_id] = img_meta.to_dict()
                        img_idx += 1

        finally:
            doc.close()

        labeled_text = "\n".join(labeled_lines)
        logger.info(
            "Extracción finalizada: %d páginas analizadas, %d bloques procesados, %d imágenes guardadas.",
            total_pages,
            len(all_blocks),
            len(all_images)
        )
        return labeled_text, metadata_index, all_blocks, all_images


# ============================================================================
# MÓDULO 2: SEGMENTADOR SEMÁNTICO HÍBRIDO (SectionSplitter)
# ============================================================================

class SectionSplitter:
    """
    Segmenta el documento en capítulos académicos reales y los agrupa
    en categorías canónicas para que cada Agente Sinodal audite sus áreas pertinentes.
    """

    CHAPTER_RE = re.compile(r"^(?:cap[íi]tulo\s+)?(\d+)\s+([A-ZÁÉÍÓÚ].*)", re.I)

    CANONICAL_SECTIONS: Dict[str, List[re.Pattern]] = {
        "Planteamiento/Objetivos": [
            re.compile(r"(?:planteamiento|problem[aá]tica|justificaci[oó]n|hip[oó]tesis|objetivos?|introducci[oó]n)", re.I),
        ],
        "Marco Teórico/Estado del Arte": [
            re.compile(r"(?:marco\s+te[oó]rico|estado\s+del\s+arte|antecedentes|marco\s+conceptual|fundamentaci[oó]n)", re.I),
        ],
        "Metodología": [
            re.compile(r"(?:metodolog[ií]a|planeaci[oó]n|dise[ñn]o|requerimientos?|conceptos?|manufactura|an[aá]lisis\s+de\s+elementos\s+finitos|fea|materiales\s+y\s+m[eé]todos|modelo\s+matem[aá]tico|cinem[aá]tic|din[aá]mic|control|modos\s+deslizantes|identificaci[oó]n|interfaz|hmi)", re.I),
        ],
        "Resultados/Discusión": [
            re.compile(r"(?:resultados|an[aá]lisis\s+de\s+resultados|discusi[oó]n|pruebas|evaluaci[oó]n|conclusiones?|trabajo\s+futuro|recomendaciones?)", re.I),
        ],
    }

    def __init__(self, heading_min_size: float = 14.0, overlap_count: int = 2):
        self.heading_min_size = heading_min_size
        self.overlap_count = overlap_count

    def categorize_title(self, title: str) -> str:
        for canonical, patterns in self.CANONICAL_SECTIONS.items():
            for pat in patterns:
                if pat.search(title):
                    return canonical
        return "Metodología"  # Los capítulos de desarrollo técnico caen naturalmente aquí

    def split(
        self, blocks: List[TextBlockMetadata], images: Optional[List[ImageBlockMetadata]] = None
    ) -> List[Section]:
        """
        Segmenta secuencialmente todos los capítulos del documento y asocia
        los bloques de texto e imágenes/figuras correspondientes a cada uno.
        Retorna la lista ordenada de capítulos detectados.
        """
        if not blocks:
            return []

        images_list = images or []

        body_sizes = [b.avg_font_size for b in blocks if not b.is_heading_candidate]
        body_font_base = (sum(body_sizes) / len(body_sizes)) if body_sizes else 11.0

        detected_headings: List[Tuple[int, str, str, TextBlockMetadata]] = []
        expected_next_chap = 1

        for idx, block in enumerate(blocks):
            clean = block.text.strip()
            is_large = block.max_font_size >= self.heading_min_size
            is_bold_title = block.is_bold and (block.max_font_size >= body_font_base * 1.15)
            is_concise = len(clean.split()) <= 15

            if (is_large or is_bold_title) and is_concise:
                m = self.CHAPTER_RE.match(clean)
                if m:
                    chap_num_str = m.group(1)
                    if "." not in chap_num_str:
                        num = int(chap_num_str)
                        if num == expected_next_chap or (num > expected_next_chap and num <= expected_next_chap + 2):
                            title = m.group(2).strip()
                            # Verificar si el siguiente bloque es continuación del título
                            if idx + 1 < len(blocks):
                                next_b = blocks[idx + 1]
                                if next_b.page == block.page and next_b.max_font_size >= self.heading_min_size and len(next_b.text.split()) <= 10:
                                    title += " " + next_b.text.strip()

                            canonical = self.categorize_title(title)
                            full_heading = f"Capítulo {num}: {title}"
                            detected_headings.append((idx, canonical, full_heading, block))
                            logger.info(
                                "Capítulo detectado: '%s' -> %s [P%d, y0=%.1f]",
                                full_heading, canonical, block.page, block.bbox[1]
                            )
                            expected_next_chap = num + 1

        if not detected_headings:
            fallback = Section(
                canonical_name="General",
                heading_title="Documento Completo",
                start_page=blocks[0].page,
                start_y0=blocks[0].bbox[1],
                blocks=blocks,
                images=images_list,
            )
            return [fallback]

        sections: List[Section] = []
        for h_idx, (start_idx, canonical_name, heading_title, heading_block) in enumerate(detected_headings):
            end_idx = detected_headings[h_idx + 1][0] if (h_idx + 1 < len(detected_headings)) else len(blocks)
            section_blocks = blocks[start_idx:end_idx]

            overlap: List[TextBlockMetadata] = []
            if start_idx > 0 and self.overlap_count > 0:
                overlap_start = max(0, start_idx - self.overlap_count)
                overlap = blocks[overlap_start:start_idx]

            # Determinar rango de páginas de este capítulo
            start_p = heading_block.page
            if h_idx + 1 < len(detected_headings):
                end_p = detected_headings[h_idx + 1][3].page
                # Imágenes pertenecientes a las páginas de este capítulo
                section_imgs = [
                    img for img in images_list
                    if (img.page > start_p and img.page < end_p)
                    or (img.page == start_p and img.bbox[1] >= heading_block.bbox[1])
                    or (img.page == end_p and img.bbox[1] < detected_headings[h_idx + 1][3].bbox[1])
                ]
            else:
                section_imgs = [
                    img for img in images_list
                    if (img.page > start_p)
                    or (img.page == start_p and img.bbox[1] >= heading_block.bbox[1])
                ]

            sections.append(Section(
                canonical_name=canonical_name,
                heading_title=heading_title,
                start_page=heading_block.page,
                start_y0=heading_block.bbox[1],
                blocks=section_blocks,
                overlap_blocks=overlap,
                images=section_imgs,
            ))

        return sections


# ============================================================================
# MÓDULO 3 (EXTENDIDO): AGENTES REVISORES CON AGY (ANTIGRAVITY-CLI)
# ============================================================================

class BaseAgyReviewer:
    """Clase base de agentes con invocación a antigravity-cli (`agy`)."""
    reviewer_name: str = "Base Reviewer"
    category: ReviewCategory = "formalismo_tecnico"
    system_prompt: str = ""

    def __init__(self, agy_client: Optional[AgyClient] = None):
        self.agy_client = agy_client or AgyClient()

    def evaluate(self, section_text: str, context_text: Optional[str] = None) -> List[ReviewComment]:
        """
        Ejecuta la revisión invocando antigravity-cli (`agy`). Si la sección es extensa,
        la divide en lotes de bloques (máximo ~50 bloques o ~15,000 caracteres por lote)
        para permitir que el modelo analice con rigurosidad y sin perder detalles.
        """
        if not section_text or not section_text.strip():
            return []

        if self.agy_client.is_installed:
            try:
                # Partir en bloques [P{n}-B{m}] si excede el tamaño razonable
                lines = section_text.splitlines()
                chunks: List[str] = []
                current_chunk: List[str] = []
                current_chars = 0

                for line in lines:
                    current_chunk.append(line)
                    current_chars += len(line) + 1
                    # Corte cada ~40 bloques o ~12,000 caracteres
                    if len(current_chunk) >= 40 or current_chars >= 12000:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = []
                        current_chars = 0
                if current_chunk:
                    chunks.append("\n".join(current_chunk))

                all_results: List[ReviewComment] = []
                for idx, chunk in enumerate(chunks):
                    chunk_ctx = context_text
                    if len(chunks) > 1:
                        logger.info(
                            "[%s] Invocando agy para lote %d/%d (%d líneas)...",
                            self.reviewer_name, idx + 1, len(chunks), len(chunk.splitlines())
                        )
                    else:
                        logger.info("[%s] Invocando antigravity-cli ('agy')...", self.reviewer_name)

                    res = self.agy_client.query_json_comments(
                        system_prompt=self.system_prompt,
                        reviewer_name=self.reviewer_name,
                        category=self.category,
                        audited_text=chunk,
                        context_text=chunk_ctx
                    )
                    all_results.extend(res)
                return all_results
            except Exception as err:
                logger.warning("[%s] Falla en llamada a agy (%s). Usando motor heurístico local.", self.reviewer_name, err)

        return self._local_heuristic_evaluate(section_text, context_text)

    def _local_heuristic_evaluate(self, section_text: str, context_text: Optional[str] = None) -> List[ReviewComment]:
        """Motor heurístico de respaldo en caso de que agy no esté configurado en la máquina."""
        return []


class CoherenceReviewer(BaseAgyReviewer):
    """
    Agente 1: Coherencia y Objetivos.
    Entrada: Texto de Introducción, Planteamiento del Problema y Objetivos.
    """
    reviewer_name = "Agente Coherencia y Objetivos"
    category: ReviewCategory = "coherencia_objetivos"
    system_prompt = (
        "Eres un sinodal evaluador doctoral de ingeniería. Audita la alineación entre el "
        "Planteamiento del Problema y los Objetivos. Verifica que:\n"
        "1. Los objetivos específicos representen etapas técnicas medibles y reproducibles, "
        "no actividades ambiguas.\n"
        "2. El objetivo general resuelva directamente la problemática delimitada.\n"
        "Devuelve tus hallazgos usando el esquema JSON con category=\"coherencia_objetivos\"."
    )

    def _local_heuristic_evaluate(self, section_text: str, context_text: Optional[str] = None) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        rules = [
            (
                r"\b(comprender|estudiar|investigar|conocer|analizar\s+a\s+fondo)\b",
                "El objetivo específico utiliza verbos cognitivos no medibles ni verificables en ingeniería. "
                "Debe sustituirse por acciones técnicas concretas (ej. 'Modelar matemáticamente...', 'Implementar un algoritmo de...').",
                "critica"
            ),
            (
                r"\b(mejorar\s+la\s+eficiencia(?!\s+en\s+(?:al\s+menos\s+)?\d+))\b",
                "El objetivo general declara 'mejorar la eficiencia' de manera laxa sin fijar una métrica porcentual o cota cuantificable.",
                "observacion"
            ),
        ]
        for line in section_text.splitlines():
            m_block = re.match(r"\[(P\d+-B\d+)\]\s*(.*)", line)
            if not m_block:
                continue
            tid, text = m_block.group(1), m_block.group(2)
            page_num = int(re.search(r"P(\d+)", tid).group(1))

            for pat, exp, sev in rules:
                m = re.search(pat, text, re.I)
                if m:
                    comments.append(ReviewComment(
                        target_id=tid,
                        page=page_num,
                        quote=m.group(0),
                        reviewer_name=self.reviewer_name,
                        category=self.category,
                        severity=sev,  # type: ignore
                        comment=exp
                    ))
        return comments


class MethodologyReviewer(BaseAgyReviewer):
    """
    Agente 2: Rigor Metodológico y Diseño.
    Entrada: Contexto (Objetivos específicos extraídos) + Texto auditado (Metodología y Diseño Experimental).
    """
    reviewer_name = "Agente Rigor Metodológico y Diseño"
    category: ReviewCategory = "rigor_metodologico"
    system_prompt = (
        "Eres un revisor técnico de ingeniería aplicada. Audita el capítulo de METODOLOGÍA "
        "(tanto el texto como las figuras/diagramas/esquemas asociados) contrastándolo con los OBJETIVOS dados. Verifica que:\n"
        "1. Cada objetivo específico cuente con una técnica, modelo matemático, simulación "
        "o diseño experimental asociado.\n"
        "2. Se justifique la selección de componentes, sensores, tasas de muestreo y "
        "arquitecturas frente a alternativas estándar.\n"
        "3. Exista suficiente detalle para garantizar la reproducibilidad del experimento o prototipo.\n"
        "4. En las FIGURAS/DIAGRAMAS (bloques [P{p}-IMG{i}]): inspecciona visualmente el archivo PNG indicado y verifica "
        "que los diagramas de flujo, esquemas de hardware o arquitecturas sean legibles, contengan todas las etapas descritas "
        "en el texto, y no tengan elementos confusos o flechas sin destino.\n"
        "Devuelve tus hallazgos usando el esquema JSON con category=\"rigor_metodologico\"."
    )

    def _local_heuristic_evaluate(self, section_text: str, context_text: Optional[str] = None) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        rules = [
            (
                r"\b(sensores?\s+sin\s+especificar|frecuencia\s+arbitraria|tasa\s+de\s+muestreo\s+adecuada)\b",
                "Falta de justificación técnica en la instrumentación: no se especifica el modelo del sensor, margen de error "
                "ni la tasa de muestreo requerida para satisfacer el criterio de Nyquist-Shannon.",
                "critica"
            ),
            (
                r"\b(se\s+utiliz[oó]\s+python\s+por\s+comodidad|se\s+seleccion[oó]\s+por\s+su\s+facilidad)\b",
                "Criterio de diseño no ingenieril: justificar componentes por 'comodidad' o 'facilidad' es inadmisible en una tesis. "
                "Debe justificarse en función del tiempo de ciclo, soporte de librerías en tiempo real o consumo de recursos.",
                "observacion"
            ),
        ]
        for line in section_text.splitlines():
            m_block = re.match(r"\[(P\d+-B\d+)\]\s*(.*)", line)
            if not m_block:
                continue
            tid, text = m_block.group(1), m_block.group(2)
            page_num = int(re.search(r"P(\d+)", tid).group(1))

            for pat, exp, sev in rules:
                m = re.search(pat, text, re.I)
                if m:
                    comments.append(ReviewComment(
                        target_id=tid,
                        page=page_num,
                        quote=m.group(0),
                        reviewer_name=self.reviewer_name,
                        category=self.category,
                        severity=sev,  # type: ignore
                        comment=exp
                    ))
        return comments


class ResultsReviewer(BaseAgyReviewer):
    """
    Agente 3: Validación de Resultados y Discusión.
    Entrada: Contexto (Objetivos + Metodología resumida) + Texto auditado (Resultados, Análisis y Conclusiones).
    """
    reviewer_name = "Agente Validación de Resultados"
    category: ReviewCategory = "validacion_resultados"
    system_prompt = (
        "Eres un revisor de publicaciones IEEE/Elsevier. Audita los capítulos de RESULTADOS "
        "y CONCLUSIONES, inspeccionando tanto el texto como las figuras/gráficas de resultados asociadas. Verifica que:\n"
        "1. No existan afirmaciones cualitativas sin soporte cuantitativo (errores, tiempos "
        "de convergencia, métricas estadísticas).\n"
        "2. Se comparen los resultados con las soluciones citadas en el estado del arte.\n"
        "3. Las conclusiones deriven directamente de las pruebas mostradas y aborden "
        "el cumplimiento real de los objetivos.\n"
        "4. En las GRÁFICAS Y FIGURAS DE RESULTADOS (bloques [P{p}-IMG{i}]): inspecciona visualmente el archivo PNG correspondiente "
        "y comprueba que los ejes cartesianos tengan nombres de variables claras, unidades de medida normalizadas (ej. segundos, Voltios, %), "
        "que las curvas cuenten con leyendas/identificadores legibles, y que la tendencia gráfica realmente coincida con lo que el autor "
        "asegura en el texto (sin contradicciones visuales o sobreinterpretaciones).\n"
        "Devuelve tus hallazgos usando el esquema JSON con category=\"validacion_resultados\"."
    )

    def _local_heuristic_evaluate(self, section_text: str, context_text: Optional[str] = None) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        rules = [
            (
                r"\b(los\s+resultados\s+fueron\s+excelentes|demostr[oó]\s+un\s+rendimiento\s+muy\s+bueno|funciona\s+perfectamente)\b",
                "Afirmación cualitativa carente de validez científica. Es indispensable presentar métricas numéricas verificables "
                "(ej. error cuadrático medio, desviación típica, tiempo de respuesta con p < 0.05).",
                "critica"
            ),
            (
                r"\b(supera\s+a\s+los\s+m[eé]todos\s+existentes(?!\s+en\s+un))\b",
                "Ausencia de benchmarking: se afirma superioridad frente al estado del arte sin incluir tabla comparativa directa "
                "con las metodologías citadas como referencia.",
                "observacion"
            ),
        ]
        for line in section_text.splitlines():
            m_block = re.match(r"\[(P\d+-B\d+)\]\s*(.*)", line)
            if not m_block:
                continue
            tid, text = m_block.group(1), m_block.group(2)
            page_num = int(re.search(r"P(\d+)", tid).group(1))

            for pat, exp, sev in rules:
                m = re.search(pat, text, re.I)
                if m:
                    comments.append(ReviewComment(
                        target_id=tid,
                        page=page_num,
                        quote=m.group(0),
                        reviewer_name=self.reviewer_name,
                        category=self.category,
                        severity=sev,  # type: ignore
                        comment=exp
                    ))
        return comments


class TechnicalStyleReviewer(BaseAgyReviewer):
    """
    Agente 4: Formalismo Técnico y Estilo.
    Entrada: Cualquier sección del documento.
    """
    reviewer_name = "Agente Formalismo Técnico y Estilo"
    category: ReviewCategory = "formalismo_tecnico"
    system_prompt = (
        "Eres el revisor de estilo técnico para publicaciones de ingeniería. Verifica que:\n"
        "1. Las variables matemáticas en ecuaciones queden definidas en el texto adyacente.\n"
        "2. Se respete la notación del Sistema Internacional (SI) y el espaciado adecuado "
        "entre número y unidad (ej. 5 ms, no 5ms).\n"
        "3. Toda tabla o figura esté referenciada explícitamente en el cuerpo del texto.\n"
        "Devuelve tus hallazgos usando el esquema JSON con category=\"formalismo_tecnico\"."
    )

    def _local_heuristic_evaluate(self, section_text: str, context_text: Optional[str] = None) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        si_regex = re.compile(r"\b(\d+(?:\.\d+)?)(ms|kHz|MHz|GHz|Hz|V|mA|A|kg|cm|mm|km|s|min)\b")

        for line in section_text.splitlines():
            m_block = re.match(r"\[(P\d+-B\d+)\]\s*(.*)", line)
            if not m_block:
                continue
            tid, text = m_block.group(1), m_block.group(2)
            page_num = int(re.search(r"P(\d+)", tid).group(1))

            for m_si in si_regex.finditer(text):
                val, unit = m_si.group(1), m_si.group(2)
                bad_quote = m_si.group(0)
                comments.append(ReviewComment(
                    target_id=tid,
                    page=page_num,
                    quote=bad_quote,
                    reviewer_name=self.reviewer_name,
                    category=self.category,
                    severity="sugerencia",
                    comment=f"Violación de norma SI: debe existir un espacio inseparable entre el valor y su unidad "
                            f"(escribir '{val} {unit}' en lugar de '{bad_quote}').",
                ))

            if re.search(r"\b(?:en|la|esta)\s+figura\b", text, re.I) and not re.search(r"\bfigura\s+\d+", text, re.I):
                comments.append(ReviewComment(
                    target_id=tid,
                    page=page_num,
                    quote="figura",
                    reviewer_name=self.reviewer_name,
                    category=self.category,
                    severity="observacion",
                    comment="Referencia ambigua a ilustración. Toda figura debe numerarse y citarse explícitamente (ej. 'Figura 2.1').",
                ))

        return comments


def mock_agent_review(
    methodology_section: Section,
    objectives_context: Section,
    agy_client: Optional[AgyClient] = None
) -> List[ReviewComment]:
    """
    Función de evaluación de la sección 'Metodología' utilizando el contexto de 'Objetivos',
    utilizando `agy` si está disponible.
    """
    agent = MethodologyReviewer(agy_client=agy_client)
    return agent.evaluate(
        section_text=methodology_section.full_text,
        context_text=objectives_context.full_text
    )


# ============================================================================
# MÓDULO 4: INYECTOR DE ANOTACIONES EN PDF (PdfAnnotator)
# ============================================================================

class PdfAnnotator:
    """
    Inyecta anotaciones visuales y notas emergentes sobre el PDF original
    mediante PyMuPDF, aplicando la paleta de colores normalizada y algoritmo
    de resaltado con doble fallback de coordenadas.
    """

    COLOR_PALETTE: Dict[ReviewCategory, Tuple[float, float, float]] = {
        "rigor_metodologico": (1.0, 0.2, 0.2),      # Rojo
        "coherencia_objetivos": (1.0, 0.5, 0.0),    # Naranja
        "validacion_resultados": (0.8, 0.2, 0.8),   # Magenta
        "formalismo_tecnico": (1.0, 0.85, 0.0),     # Amarillo
    }

    def __init__(self, metadata_index: Dict[str, Dict[str, Any]]):
        self.metadata_index = metadata_index

    def annotate(
        self,
        input_pdf_path: str | Path,
        comments: List[ReviewComment],
        output_pdf_path: str | Path = "tesis_revisada_con_comentarios.pdf"
    ) -> Path:
        """
        Aplica resaltados y notas emergentes al PDF y exporta con compresión limpia.
        """
        if fitz is None:
            raise ImportError("PyMuPDF (fitz) es necesario para realizar la inyección de anotaciones.")

        src_path = Path(input_pdf_path)
        dest_path = Path(output_pdf_path)

        if not src_path.exists():
            raise FileNotFoundError(f"Archivo PDF original no encontrado: {src_path}")

        doc = fitz.open(src_path)
        applied_count = 0

        try:
            for comment in comments:
                page_idx = comment.page - 1  # Base 0
                if page_idx < 0 or page_idx >= len(doc):
                    logger.warning("Página %d fuera de rango para el bloque %s", comment.page, comment.target_id)
                    continue

                page = doc[page_idx]
                color = self.COLOR_PALETTE.get(comment.category, (1.0, 1.0, 0.0))
                annot = None

                # Paso 1: Búsqueda exacta de la frase (quote) en el texto renderizado
                quads = page.search_for(comment.quote)
                if quads:
                    annot = page.add_highlight_annot(quads)

                # Paso 2 (Fallback 1): Si falla la búsqueda de texto, usar el bbox del bloque indexado
                if annot is None and comment.target_id in self.metadata_index:
                    block_info = self.metadata_index[comment.target_id]
                    raw_bbox = block_info.get("bbox")
                    if raw_bbox:
                        rect = fitz.Rect(raw_bbox)
                        annot = page.add_highlight_annot(rect)
                        logger.info("Fallback por bbox aplicado para %s", comment.target_id)

                # Paso 3 (Fallback 2): Si no hay bbox, insertar nota adhesiva en el margen (72, 72 pt)
                if annot is None:
                    point = fitz.Point(72.0, 72.0)
                    annot = page.add_text_annot(point, comment.quote)
                    logger.warning("Fallback por nota adhesiva marginal aplicado para %s", comment.target_id)

                # Configurar color, metadatos y contenido emergente
                if annot is not None:
                    annot.set_colors(stroke=color)
                    annot.set_info(
                        title=f"[{comment.reviewer_name}] ({comment.severity.upper()})",
                        content=f"Categoría: {comment.category}\n\nObservación:\n{comment.comment}"
                    )
                    annot.update()
                    applied_count += 1

            # Exportar con recolección de basura y deflación para compresión óptima
            doc.save(str(dest_path), garbage=4, deflate=True)
            logger.info("PDF anotado exportado en '%s' con %d anotaciones.", dest_path, applied_count)

        finally:
            doc.close()

        return dest_path


# ============================================================================
# ORQUESTADOR DEL PIPELINE CON AGY
# ============================================================================

class ThesisReviewPipeline:
    """
    Orquestador integral del flujo de revisión:
    Extracción -> Segmentación Semántica -> Agentes antigravity-cli (`agy`) -> Anotación Visual
    """

    def __init__(self, agy_command: str = "agy"):
        self.agy_client = AgyClient(cli_command=agy_command)
        self.extractor = PdfStructuredExtractor()
        self.splitter = SectionSplitter()
        self.coherence_agent = CoherenceReviewer(agy_client=self.agy_client)
        self.methodology_agent = MethodologyReviewer(agy_client=self.agy_client)
        self.results_agent = ResultsReviewer(agy_client=self.agy_client)
        self.style_agent = TechnicalStyleReviewer(agy_client=self.agy_client)

    def run(
        self,
        input_pdf: str | Path,
        output_pdf: str | Path = "tesis_revisada_con_comentarios.pdf"
    ) -> Tuple[Path, List[ReviewComment]]:
        logger.info(">>> Iniciando Pipeline de Auditoría de Tesis con antigravity-cli ('agy')...")

        # 1. Extracción Estructurada de Texto e Imágenes/Figuras
        labeled_text, metadata_index, blocks, images = self.extractor.extract(input_pdf)

        # 2. Segmentación Semántica Híbrida (Capítulos Reales con Imágenes Asociadas)
        sections = self.splitter.split(blocks, images=images)
        logger.info(
            "Capítulos detectados: %d | Bloques de texto: %d | Figuras/imágenes extraídas: %d",
            len(sections), len(blocks), len(images)
        )

        all_comments: List[ReviewComment] = []

        # Identificar secciones clave para paso contextual
        obj_sections = [s for s in sections if s.canonical_name == "Planteamiento/Objetivos"]
        meth_sections = [s for s in sections if s.canonical_name == "Metodología"]
        res_sections = [s for s in sections if s.canonical_name == "Resultados/Discusión"]

        # Resumen de contexto de objetivos para los agentes posteriores
        ctx_objs = "\n".join(s.full_text for s in obj_sections)
        # Resumen de metodología para el agente de resultados
        ctx_meth_summary = "\n".join(
            f"[{s.heading_title}]\n" + "\n".join(f"[{b.target_id}] {b.text}" for b in s.blocks[:8])
            for s in meth_sections
        )
        ctx_acumulado = f"{ctx_objs}\n{ctx_meth_summary}"

        # 3. Auditoría por Agentes con antigravity-cli
        # Agente 1: Coherencia y Objetivos (Capítulos de Planteamiento/Objetivos e Introducción)
        logger.info(">>> Ejecutando Agente 1 (Coherencia y Objetivos) en capítulos pertinentes...")
        for sec in obj_sections:
            logger.info("Auditoría de Objetivos sobre: %s", sec.heading_title)
            all_comments.extend(self.coherence_agent.evaluate(sec.full_text))

        # Agente 2: Rigor Metodológico y Diseño (Capítulos técnicos, desarrollo, modelos, simulación)
        logger.info(">>> Ejecutando Agente 2 (Rigor Metodológico y Diseño) en capítulos técnicos...")
        for sec in meth_sections:
            logger.info("Auditoría Metodológica sobre: %s", sec.heading_title)
            all_comments.extend(self.methodology_agent.evaluate(sec.context_text, context_text=ctx_objs))

        # Agente 3: Validación de Resultados y Conclusiones
        logger.info(">>> Ejecutando Agente 3 (Validación de Resultados) en capítulos de pruebas y conclusiones...")
        for sec in res_sections:
            logger.info("Auditoría de Resultados sobre: %s", sec.heading_title)
            all_comments.extend(self.results_agent.evaluate(sec.context_text, context_text=ctx_acumulado))

        # Agente 4: Formalismo Técnico y Estilo (sobre todos los capítulos)
        logger.info(">>> Ejecutando Agente 4 (Formalismo Técnico y Estilo) en todos los capítulos...")
        for sec in sections:
            logger.info("Auditoría de Estilo sobre: %s", sec.heading_title)
            all_comments.extend(self.style_agent.evaluate(sec.full_text))

        logger.info("Auditoría finalizada. Total de observaciones detectadas: %d", len(all_comments))

        # 4. Inyección Visual de Anotaciones en el PDF
        annotator = PdfAnnotator(metadata_index=metadata_index)
        final_pdf_path = annotator.annotate(input_pdf, all_comments, output_pdf)

        logger.info(">>> Flujo completado exitosamente.")
        return final_pdf_path, all_comments


# ============================================================================
# GENERADOR DE PDF SINTÉTICO (Para Validación y Demostración)
# ============================================================================

def create_synthetic_thesis_pdf(output_path: str | Path) -> Path:
    """
    Genera un documento PDF académico con secciones típicas y fallas
    deliberadas para validar el comportamiento del pipeline completo.
    """
    if fitz is None:
        raise ImportError("PyMuPDF no está disponible.")

    doc = fitz.open()

    # Página 1: Capítulo 1 - Planteamiento y Objetivos
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 60), "Capítulo 1: Planteamiento y Objetivos", fontsize=18, fontname="helv", color=(0, 0, 0))
    p1.insert_text((50, 100), "1.1 Planteamiento del Problema", fontsize=14, fontname="helv")
    p1.insert_text((50, 130), "La latencia en redes industriales inalámbricas compromete la seguridad operacional.", fontsize=11, fontname="helv")
    p1.insert_text((50, 170), "1.2 Objetivo General", fontsize=14, fontname="helv")
    p1.insert_text((50, 200), "El objetivo es mejorar la eficiencia de la red en entornos de manufactura.", fontsize=11, fontname="helv")
    p1.insert_text((50, 240), "1.3 Objetivos Específicos", fontsize=14, fontname="helv")
    p1.insert_text((50, 270), "Primero, estudiar los protocolos existentes y comprender las causas de retardo.", fontsize=11, fontname="helv")

    # Página 2: Capítulo 2 - Metodología y Diseño Experimental
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 60), "Capítulo 2: Metodología y Diseño Experimental", fontsize=18, fontname="helv")
    p2.insert_text((50, 100), "2.1 Selección de Instrumentación", fontsize=14, fontname="helv")
    p2.insert_text((50, 130), "Se implementó un nodo embebido con sensores sin especificar y una tasa de muestreo adecuada.", fontsize=11, fontname="helv")
    p2.insert_text((50, 170), "2.2 Arquitectura de Software", fontsize=14, fontname="helv")
    p2.insert_text((50, 200), "Para el procesamiento, se utilizó python por comodidad en las pruebas de laboratorio.", fontsize=11, fontname="helv")
    p2.insert_text((50, 240), "2.3 Parámetros de Transmisión", fontsize=14, fontname="helv")
    p2.insert_text((50, 270), "El tiempo de muestreo fue registrado cada 5ms a una frecuencia de 16MHz.", fontsize=11, fontname="helv")

    # Página 3: Capítulo 3 - Resultados y Discusión
    p3 = doc.new_page(width=595, height=842)
    p3.insert_text((50, 60), "Capítulo 3: Resultados y Discusión", fontsize=18, fontname="helv")
    p3.insert_text((50, 100), "3.1 Análisis de Pruebas", fontsize=14, fontname="helv")
    p3.insert_text((50, 130), "Durante las evaluaciones piloto, los resultados fueron excelentes en todas las condiciones.", fontsize=11, fontname="helv")
    p3.insert_text((50, 170), "3.2 Comparativa con el Estado del Arte", fontsize=14, fontname="helv")
    p3.insert_text((50, 200), "La topología propuesta supera a los métodos existentes sin requerir repetidores.", fontsize=11, fontname="helv")
    p3.insert_text((50, 240), "3.3 Validación de Dispersión", fontsize=14, fontname="helv")
    p3.insert_text((50, 270), "Como se aprecia en la figura, la tasa de error de paquete se redujo notablemente.", fontsize=11, fontname="helv")

    out_p = Path(output_path)
    doc.save(str(out_p))
    doc.close()
    return out_p


# ============================================================================
# BLOQUE PRINCIPAL DE EJECUCIÓN (Demo de Extremo a Extremo)
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print(" AUDITORÍA AUTOMATIZADA DE TESIS EN PDF CON ANTIGRAVITY-CLI (`agy`)")
    print("=" * 80)

    pdf_entrada = Path("tesis_demo.pdf")
    pdf_salida = Path("tesis_revisada_con_comentarios.pdf")

    # Comprobación de agy en la PC
    agy_instalado = bool(shutil.which("agy"))
    print(f"[*] antigravity-cli ('agy') detectado en PATH: {'SÍ' if agy_instalado else 'NO (usando fallback heurístico)'}")
    print(f"[*] PyMuPDF (fitz) detectado en Python       : {'SÍ' if fitz is not None else 'NO'}\n")

    try:
        if fitz is not None:
            # 1. Crear documento sintético de muestra
            create_synthetic_thesis_pdf(pdf_entrada)

            # 2. Instanciar y ejecutar pipeline configurado con `agy`
            pipeline = ThesisReviewPipeline(agy_command="agy")
            resultado_pdf, hallazgos = pipeline.run(pdf_entrada, pdf_salida)

            # 3. Mostrar resumen en consola
            print(f"\n[ÉXITO] Pipeline completado.")
            print(f"[PDF Generado] : {resultado_pdf.resolve()}")
            print(f"[Total Hallazgos]: {len(hallazgos)}\n")
            print("-" * 80)
            print("REPORTE DE OBSERVACIONES REGISTRADAS EN EL PDF:")
            print("-" * 80)
            for idx, h in enumerate(hallazgos, 1):
                print(f"{idx:02d}. [{h.reviewer_name}] | Pág. {h.page} ({h.target_id}) | {h.severity.upper()}")
                print(f"    Categoría : {h.category}")
                print(f"    Cita      : \"{h.quote}\"")
                print(f"    Comentario: {h.comment}\n")
        else:
            print("[AVISO] Para ejecutar la demostración completa con generación y anotación de PDF,")
            print("        asegúrate de tener instalado: pip install pymupdf")

    except Exception as err:
        logger.error("Falla en la ejecución del pipeline: %s", err, exc_info=True)