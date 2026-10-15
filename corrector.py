import os
import sys
import json
import re
import argparse
import subprocess
import concurrent.futures
import pymupdf
import requests
import time
import random
import unicodedata
import threading

class GeminiRateLimiter:
    """
    Controlador de tasa de peticiones concurrente (Thread-safe Rate Limiter)
    para la API de Gemini (Free Tier / Quota limit).
    Por defecto limita a 10 peticiones por minuto (mínimo 6.0 segundos entre llamadas).
    """
    def __init__(self, requests_per_minute: float = 10.0):
        self.interval = 60.0 / max(1.0, requests_per_minute)
        self.lock = threading.Lock()
        self.last_call_time = 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_call_time
            if elapsed < self.interval:
                sleep_time = self.interval - elapsed
                time.sleep(sleep_time)
            self.last_call_time = time.time()

# Instancia global compartida para todas las llamadas API a Gemini
gemini_rate_limiter = GeminiRateLimiter(requests_per_minute=10.0)

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from spellchecker import SpellChecker
    _SPELL_ES = SpellChecker(language="es", distance=1)
    HAS_SPELL = True
except Exception:
    _SPELL_ES = None
    HAS_SPELL = False

# Mapeo explícito de ligaduras tipográficas Unicode estándar
LIGATURE_MAP = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "ft",
    "\ufb06": "st",
}

# Codificación T1 (Cork) de LaTeX: fuentes sin mapa ToUnicode exportan las
# ligaduras y signos como caracteres de control (ej. 'veri\x1ccación').
# pdfplumber los entrega como (cid:28); PyMuPDF como el carácter literal.
T1_CONTROL_MAP = {
    0x10: "\u201c",  # comillas dobles de apertura
    0x11: "\u201d",  # comillas dobles de cierre
    0x15: "\u2013",  # guion corto (en dash)
    0x16: "\u2014",  # guion largo (em dash)
    0x1B: "ff",
    0x1C: "fi",
    0x1D: "fl",
    0x1E: "ffi",
    0x1F: "ffl",
}
T1_TRANSLATE = {code: rep for code, rep in T1_CONTROL_MAP.items()}
# Cualquier otro carácter de control (excepto \t y \n) se convierte en espacio
for _c in range(0x00, 0x20):
    if _c not in T1_TRANSLATE and _c not in (0x09, 0x0A):
        T1_TRANSLATE[_c] = " "

# Secuencias candidatas para reconstruir un glifo perdido (orden de prioridad)
LIGATURE_CANDIDATES = ["fi", "fl", "ff", "ffi", "ffl"]

# Patrones morfológicos y de referencias académicas para reconstruir texto
# donde la ligadura (fl, fi, ff) o guiones de rango fueron extraídos rotos
RECONSTRUCTION_PATTERNS = [
    # Rangos de páginas y números en referencias/bibliografía
    (r'\bpp\.\s*(\d+)\s+(\d+)\b', r'pp. \1-\2'),
    (r'\bno\.\s*(\d+)\s+(\d+)\b', r'no. \1-\2'),
    (r'\bvol\.\s*(\d+)\s+(\d+)\b', r'vol. \1-\2'),
    (r'\bpág\.\s*(\d+)\s+(\d+)\b', r'pág. \1-\2'),
    (r'\bpágs\.\s*(\d+)\s+(\d+)\b', r'págs. \1-\2'),
    
    # Palabras partidas o con PUA en 'fl' (con contexto claro a ambos lados)
    (r'\bcon(?:\s+|[\ue000-\uf8ff])icto\b', 'conflicto'),
    (r'\bcon(?:\s+|[\ue000-\uf8ff])ictos\b', 'conflictos'),
    (r'\bcon(?:\s+|[\ue000-\uf8ff])ictiv', 'conflictiv'),
    (r'\bin(?:\s+|[\ue000-\uf8ff])aci', 'inflaci'),
    (r'\bin(?:\s+|[\ue000-\uf8ff])uir\b', 'influir'),
    (r'\bin(?:\s+|[\ue000-\uf8ff])uyen\b', 'influyen'),
    (r'\bin(?:\s+|[\ue000-\uf8ff])uencia\b', 'influencia'),
    (r'\bin(?:\s+|[\ue000-\uf8ff])uencias\b', 'influencias'),
    (r'\bin(?:\s+|[\ue000-\uf8ff])ujo\b', 'influjo'),
    (r'\bin(?:\s+|[\ue000-\uf8ff])amaci', 'inflamaci'),
    (r'\bre(?:\s+|[\ue000-\uf8ff])exi', 'reflexi'),
    (r'\bre(?:\s+|[\ue000-\uf8ff])ej', 'reflej'),
    (r'\bre(?:\s+|[\ue000-\uf8ff])ujo\b', 'reflujo'),
    (r'\ba(?:\s+|[\ue000-\uf8ff])uent', 'afluent'),
    (r'\ba(?:\s+|[\ue000-\uf8ff])uenci', 'afluenci'),
    (r'\ba(?:\s+|[\ue000-\uf8ff])igi', 'afligi'),
    
    # Palabras partidas o con PUA en 'fi' / 'ff' / 'f'
    (r'\bPonti(?:\s+|[\ue000-\uf8ff])cia\b', 'Pontificia'),
    (r'\bponti(?:\s+|[\ue000-\uf8ff])cia\b', 'pontificia'),
    (r'\bDi(?:\s+|[\ue000-\uf8ff])erenti', 'Differenti'),
    (r'\bdi(?:\s+|[\ue000-\uf8ff])erenti', 'differenti'),
    (r'\bde(?:\s+|[\ue000-\uf8ff])nici', 'definici'),
    (r'\bde(?:\s+|[\ue000-\uf8ff])nir\b', 'definir'),
    (r'\bde(?:\s+|[\ue000-\uf8ff])nitiv', 'definitiv'),
    (r'\bde(?:\s+|[\ue000-\uf8ff])nid', 'definid'),
    (r'\bcon(?:\s+|[\ue000-\uf8ff])gura', 'configura'),
    (r'\bcon(?:\s+|[\ue000-\uf8ff])anza\b', 'confianza'),
    (r'\bcon(?:\s+|[\ue000-\uf8ff])ar\b', 'confiar'),
    (r'\bcon(?:\s+|[\ue000-\uf8ff])rm', 'confirm'),
    (r'\bsigni(?:\s+|[\ue000-\uf8ff])ica', 'significa'),
    (r'\bbene(?:\s+|[\ue000-\uf8ff])ici', 'benefici'),
    (r'\be(?:\s+|[\ue000-\uf8ff])caz\b', 'eficaz'),
    (r'\be(?:\s+|[\ue000-\uf8ff])caces\b', 'eficaces'),
    (r'\be(?:\s+|[\ue000-\uf8ff])cacia\b', 'eficacia'),
    (r'\bdi(?:\s+|[\ue000-\uf8ff])cult', 'dificult'),
    (r'\bdi(?:\s+|[\ue000-\uf8ff])ícil', 'difícil'),
    (r'\bdi(?:\s+|[\ue000-\uf8ff])icil', 'difícil'),
    (r'\bdi(?:\s+|[\ue000-\uf8ff])erenc', 'diferenc'),
    (r'\bdi(?:\s+|[\ue000-\uf8ff])erent', 'diferent'),
    (r'\bin(?:\s+|[\ue000-\uf8ff])ormaci', 'informaci'),
    (r'\bin(?:\s+|[\ue000-\uf8ff])orme\b', 'informe'),
    (r'\bin(?:\s+|[\ue000-\uf8ff])ormes\b', 'informes'),
    (r'\bin(?:\s+|[\ue000-\uf8ff])ormat', 'informat'),
]

# Expresiones regulares precompiladas para máxima velocidad
COMPILED_RECONSTRUCTIONS = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in RECONSTRUCTION_PATTERNS
]
DEHYPHEN_RE = re.compile(r'(\b\w+)-\n(\w+\b)')
PUA_RE = re.compile(r'[\ue000-\uf8ff]')
CID_RE = re.compile(r'\(cid:(\d+)\)')
# Palabra que contiene uno o más glifos no resueltos (PUA o carácter de reemplazo)
BROKEN_GLYPH_WORD_RE = re.compile(r'[^\W\d_]*[\ue000-\uf8ff\ufffd]+[^\W\d_]*')
# Dos fragmentos alfabéticos separados por un solo espacio (posible ligadura perdida)
SPLIT_PAIR_RE = re.compile(r'\b([^\W\d_]{1,})( )([^\W\d_]{2,})\b')
WORD_RE = re.compile(r'[^\W\d_]{3,}')
SUSPICIOUS_RE = re.compile(r'[\x00-\x08\x0b-\x1f\ue000-\uf8ff\ufffd]|\(cid:\d+\)')

def decode_cid_match(m) -> str:
    """Traduce códigos (cid:NNN) de fuentes PDF/pdfminer a caracteres legibles (ej. (cid:243) -> ó)."""
    try:
        code = int(m.group(1))
        if code < 32:
            # Codificación T1 de LaTeX (ej. (cid:28) -> 'fi')
            return T1_CONTROL_MAP.get(code, "")
        if code <= 255:
            return bytes([code]).decode('cp1252', errors='replace')
        return chr(code)
    except Exception:
        pass
    return ""

def _is_known_word(word: str) -> bool:
    """Indica si una palabra existe en el diccionario español."""
    if not HAS_SPELL or not word:
        return False
    return word.lower() in _SPELL_ES

def _match_case(template: str, word: str) -> str:
    """Aplica el patrón de mayúsculas de 'template' a 'word'."""
    if template.isupper() and len(template) > 1:
        return word.upper()
    if template[:1].isupper():
        return word[:1].upper() + word[1:]
    return word

def _resolve_broken_glyph_word(match) -> str:
    """Sustituye glifos desconocidos probando ligaduras hasta formar una palabra del diccionario."""
    word = match.group(0)
    parts = re.split(r'[\ue000-\uf8ff\ufffd]+', word)
    if HAS_SPELL and len(parts) == 2:
        for cand in LIGATURE_CANDIDATES + ["f", ""]:
            candidate = parts[0] + cand + parts[1]
            if _is_known_word(candidate):
                return candidate
    # Sin coincidencia: se elimina el glifo (comportamiento anterior)
    return "".join(parts)

def _rejoin_split_ligatures(text: str) -> str:
    """
    Repara palabras partidas por una ligadura perdida y sustituida por espacio
    (ej. 'veri cación' -> 'verificación'), solo si el resultado está en el diccionario
    y al menos uno de los fragmentos no es una palabra válida por sí misma.
    """
    if not HAS_SPELL:
        return text

    def repl(m):
        left, right = m.group(1), m.group(3)
        if _is_known_word(left) and _is_known_word(right):
            return m.group(0)
        for cand in LIGATURE_CANDIDATES:
            joined = left + cand + right
            if _is_known_word(joined):
                return _match_case(left, joined)
        return m.group(0)

    return SPLIT_PAIR_RE.sub(repl, text)

def clean_ligatures(text: str) -> str:
    """
    Heurística profunda de limpieza y reconstrucción de texto:
    1. Traduce códigos (cid:NNN) generados por pdfminer / pdfplumber.
    2. Traduce caracteres de control de la codificación T1 de LaTeX (\\x1c -> fi, etc.).
    3. Normaliza ligaduras Unicode estándar (fi, fl, ff, ffi, ffl, etc.).
    4. Resuelve dehyphenation (guiones de corte de palabra al final de línea).
    5. Normaliza caracteres Unicode mediante compatibilidad NFKC.
    6. Reconstruye palabras rotas por huecos o pérdidas de glifos en español/académico.
    7. Resuelve glifos de uso privado (PUA) con ayuda de un diccionario español.
    """
    if not text:
        return ""
    
    # 1. Traducir códigos CID no mapeados de pdfminer (ej. (cid:243) -> ó, (cid:28) -> fi)
    if "(cid:" in text:
        text = CID_RE.sub(decode_cid_match, text)
    
    # 2. Codificación T1 de LaTeX exportada como caracteres de control
    text = text.translate(T1_TRANSLATE)
    
    # 3. Ligaduras estándar conocidas
    for lig, rep in LIGATURE_MAP.items():
        if lig in text:
            text = text.replace(lig, rep)
        
    # 4. Dehyphenation básico
    text = DEHYPHEN_RE.sub(r'\1\2', text)
    
    # 5. Normalización NFKC
    text = unicodedata.normalize("NFKC", text)
    
    # 6. Reconstrucción morfológica con regex precompiladas
    for compiled_re, replacement in COMPILED_RECONSTRUCTIONS:
        def repl(match, rep=replacement):
            matched = match.group(0)
            if matched and matched[0].isupper():
                return rep.capitalize()
            return rep
        text = compiled_re.sub(repl, text)
    
    # 7. Glifos PUA: reconstrucción con diccionario y limpieza residual
    text = BROKEN_GLYPH_WORD_RE.sub(_resolve_broken_glyph_word, text)
    text = PUA_RE.sub('', text)
    
    # 8. Palabras partidas por una ligadura convertida en espacio
    text = _rejoin_split_ligatures(text)
    
    return text

def fast_normalize_word(text: str) -> str:
    """Normalización ultrarrápida en memoria para tokens individuales de búsqueda."""
    if not text:
        return ""
    if "(cid:" in text:
        text = CID_RE.sub(decode_cid_match, text)
    text = text.translate(T1_TRANSLATE)
    for lig, rep in LIGATURE_MAP.items():
        if lig in text:
            text = text.replace(lig, rep)
    return unicodedata.normalize("NFKC", text).lower()

def _text_quality_penalty(raw: str, cleaned: str) -> int:
    """
    Calcula una penalización de calidad para el texto extraído de una página.
    Menor es mejor: cuenta glifos sospechosos residuales y palabras desconocidas.
    """
    penalty = len(SUSPICIOUS_RE.findall(cleaned)) * 5
    if HAS_SPELL:
        words = WORD_RE.findall(cleaned)
        penalty += len(_SPELL_ES.unknown(words)) if words else 0
    return penalty

def extract_all_pages_text(pdf_path: str, doc) -> list:
    """
    Extrae el texto de todas las páginas con PyMuPDF y pdfplumber, y para cada
    página conserva la versión con menos glifos rotos / palabras desconocidas.
    PyMuPDF se prefiere en caso de empate (mejor manejo de ligaduras y orden).
    """
    total_pages = len(doc)
    print("Extrayendo texto con PyMuPDF...")
    mupdf_pages = []
    for page_num in range(total_pages):
        raw = doc[page_num].get_text("text") or ""
        mupdf_pages.append((raw, clean_ligatures(raw).strip()))

    plumber_pages = []
    if HAS_PDFPLUMBER and pdf_path and os.path.exists(pdf_path):
        try:
            print("Extrayendo texto con pdfplumber para comparación...")
            with pdfplumber.open(pdf_path) as pdf:
                for p in pdf.pages:
                    raw = p.extract_text(layout=False) or ""
                    plumber_pages.append((raw, clean_ligatures(raw).strip()))
        except Exception as e:
            print(f"Aviso con pdfplumber: {e}, se usará solo PyMuPDF.", file=sys.stderr)
            plumber_pages = []

    pages_text = []
    elegidas_plumber = 0
    for i in range(total_pages):
        m_raw, m_clean = mupdf_pages[i]
        if i >= len(plumber_pages):
            pages_text.append(m_clean)
            continue
        p_raw, p_clean = plumber_pages[i]
        if not m_clean:
            pages_text.append(p_clean)
            elegidas_plumber += bool(p_clean)
            continue
        if not p_clean:
            pages_text.append(m_clean)
            continue
        if _text_quality_penalty(p_raw, p_clean) < _text_quality_penalty(m_raw, m_clean):
            pages_text.append(p_clean)
            elegidas_plumber += 1
        else:
            pages_text.append(m_clean)

    if plumber_pages:
        print(f"Extracción: {total_pages - elegidas_plumber} páginas con PyMuPDF, {elegidas_plumber} con pdfplumber.")
    return pages_text

# Configuración del Prompt del Sistema para Gemini
DEFAULT_SYSTEM_PERSONALITY = (
    "Eres un corrector de estilo y ortografía profesional para textos académicos y reportes de estadías en español. "
    "Tu tarea es analizar el texto proporcionado en busca de errores ortográficos, gramaticales, de acentuación, "
    "concordancia, puntuación o de redacción."
)

SYSTEM_PROMPT_JSON_INSTRUCTIONS = (
    "Para cada error encontrado, debes devolver un objeto JSON. La respuesta completa debe ser un arreglo de objetos JSON "
    "con la siguiente estructura exacta:\n"
    "[\n"
    "  {\n"
    "    \"original\": \"palabra o frase incorrecta EXACTAMENTE como aparece en el texto para poder buscarla y resaltarla\",\n"
    "    \"corregido\": \"la versión corregida de la palabra o frase\",\n"
    "    \"tipo\": \"ortografía | gramática | acentuación | concordancia | puntuación | redacción\",\n"
    "    \"explicacion\": \"explicación breve y profesional de por qué es un error y cómo se corrige\"\n"
    "  }\n"
    "]\n\n"
    "REGLAS CRÍTICAS:\n"
    "1. Devuelve ÚNICAMENTE el arreglo JSON. No incluyas textos adicionales, introducciones, ni bloques de código markdown como ```json o ```.\n"
    "2. Si no hay errores objetivos en el texto, devuelve un arreglo vacío `[]`.\n"
    "3. La palabra o frase en 'original' DEBE coincidir carácter por carácter con el texto original y DEBE ser diferente de 'corregido'.\n"
    "4. NO marques como error palabras o frases válidas y bien escritas en español (ej. 'de otros', 'por otro lado', 'en otro', etc. son completamente correctas).\n"
    "5. El texto fue extraído automáticamente de un PDF. Las ligaduras tipográficas (fi, fl, ff, ffi, ffl) pueden aparecer perdidas, sustituidas por un espacio o por un símbolo extraño (ej. 'veri cación', 'vericación', 'con icto', 'de nir'). En el documento original estas palabras se ven CORRECTAS.\n"
    "6. No inventes errores de estilo subjetivos ni sugerencias innecesarias. Concéntrate en errores gramaticales u ortográficos reales y objetivos.\n"
    "7. No corrijas nombres propios de herramientas o tecnologías conocidas (ej. Python, PostgreSQL, Docker, etc.).\n"
    "8. NUNCA reportes como error una palabra cuya única diferencia con la forma correcta sea la falta de 'fi', 'fl', 'ff', 'ffi' o 'ffl', ni palabras partidas por un espacio en ese punto. Son artefactos de extracción, NO errores del autor.\n"
)

DEFAULT_GUIDE_PROMPT = (
    "Eres un Verificador de Formato y Lineamientos Académicos. "
    "Tu tarea es comparar el texto de un documento (tesis/memoria) contra un manual o guía de lineamientos proporcionado. "
    "Verifica si el documento cumple con la estructura, las reglas de formato, los apartados requeridos y demás exigencias descritas en la guía. "
    "Enumera los hallazgos: qué se cumple, qué falta y qué áreas deben corregirse para alinear el documento a la guía. "
    "Proporciona un reporte estructurado y profesional."
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_FILE = os.path.join(BASE_DIR, "prompts.json")

def load_prompts():
    if os.path.exists(PROMPTS_FILE):
        try:
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return (
                    data.get("system_personality", DEFAULT_SYSTEM_PERSONALITY), 
                    data.get("guide_prompt", DEFAULT_GUIDE_PROMPT)
                )
        except Exception:
            pass
    return DEFAULT_SYSTEM_PERSONALITY, DEFAULT_GUIDE_PROMPT

def run_agent_cli(text_content: str, page_num: int, agent: str = "Antigravity", model: str = "") -> list:
    """
    Ejecuta el agente instruyéndole a leer un archivo de texto y generar un JSON con los errores.
    Devuelve la lista de errores encontrados.
    """
    try:
        system_personality, _ = load_prompts()
        system_prompt = f"{system_personality}\n\n{SYSTEM_PROMPT_JSON_INSTRUCTIONS}"
        text_file_path = os.path.abspath(f"temp_page_{page_num}.txt")
        
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(text_content)
            
        prompt = (
            f"{system_prompt}\n\n"
            f"El texto a analizar se encuentra en el archivo: {text_file_path}\n"
            "Lee ese archivo y devuelve únicamente tu respuesta en formato JSON.\n"
            "Asegúrate de que tu respuesta sea únicamente el arreglo JSON, sin texto adicional."
        )
        
        prompt_str = prompt.strip()
        if agent == "GitHub CLI":
            cmd = ["gh", "copilot", "explain", prompt_str]
        elif agent == "Claude Code":
            cmd = ["claude", "-p", prompt_str]
        else: # Antigravity por defecto
            cmd = ["agy", "--dangerously-skip-permissions"]
            if model:
                cmd.extend(["--model", model])
            cmd.extend(["-p", prompt_str])
        
        max_retries = 5
        base_delay = 3
        
        for attempt in range(max_retries):
            # Ejecutar el comando
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            
            response_text = result.stdout.strip()
            if not response_text:
                err_msg = result.stderr.strip()
                if "429" in err_msg or "quota" in err_msg.lower() or "rate" in err_msg.lower() or "resource" in err_msg.lower():
                    delay = base_delay * (2 ** attempt) + random.uniform(1, 4)
                    print(f"  [AVISO Pág {page_num}] Límite de peticiones (429/Cuota) en {agent}. Reintentando en {delay:.1f}s...", file=sys.stderr)
                    time.sleep(delay)
                    continue
                print(f"  [ERROR Pág {page_num}] El agente no generó respuesta en stdout. Error: {result.stderr}", file=sys.stderr)
                return []
            break
        else:
            print(f"  [ERROR Pág {page_num}] Se excedió el número máximo de reintentos para el agente {agent}.", file=sys.stderr)
            return []
            
        # Remover códigos ANSI por si acaso
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_text = ansi_escape.sub('', response_text)
        
        parsed = None
        # Estrategia 1: Bloque markdown
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', clean_text)
        if match:
            try:
                parsed = json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        if parsed is None:
            # Estrategia 2: Extraer todo desde [ hasta ]
            match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', clean_text)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
                    
        if parsed is None:
            # Estrategia 3: Extraer desde { hasta } si devolvió un solo error
            match = re.search(r'\{\s*"original"[\s\S]*\}', clean_text)
            if match:
                try:
                    parsed = [json.loads(match.group(0))]
                except json.JSONDecodeError:
                    pass
                    
        if parsed is None:
            try:
                parsed = json.loads(clean_text)
            except json.JSONDecodeError:
                print(f"  [ERROR] No se pudo parsear el JSON generado:\n{clean_text}", file=sys.stderr)
                
        # Limpiar archivos temporales
        try:
            if os.path.exists(text_file_path): os.remove(text_file_path)
        except Exception as e:
            print(f"  [AVISO] No se pudieron borrar archivos temporales: {e}", file=sys.stderr)
            
        if isinstance(parsed, list): return parsed
        if isinstance(parsed, dict): return [parsed]
        
    except Exception as e:
        print(f"Ocurrió un error inesperado al invocar {agent}: {e}", file=sys.stderr)
        
    return []

def run_guide_review_cli(full_text: str, guide_text: str, agent: str = "Antigravity", model: str = "") -> str:
    """
    Ejecuta el agente para una verificación de guía usando el guide_prompt.
    """
    try:
        _, guide_prompt = load_prompts()
        text_file_path = os.path.abspath("temp_verificacion_guia.txt")
        
        content_to_write = f"=== GUÍA / MANUAL ===\n{guide_text}\n\n=== DOCUMENTO A REVISAR ===\n{full_text}"
        
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(content_to_write)
            
        prompt = (
            f"{guide_prompt}\n\n"
            f"El documento completo y la guía se encuentran en el archivo: {text_file_path}\n"
            "Lee ese archivo, realiza tu verificación y devuelve el reporte resultante como tu única respuesta."
        )
        
        prompt_str = prompt.strip()
        if agent == "GitHub CLI":
            cmd = ["gh", "copilot", "explain", prompt_str]
        elif agent == "Claude Code":
            cmd = ["claude", "-p", prompt_str]
        else:
            cmd = ["agy", "--dangerously-skip-permissions", "-p", prompt_str]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        revision = result.stdout.strip()
        if not revision:
            print(f"  [ERROR] El agente no generó respuesta en stdout para verificación de guía. Error: {result.stderr}", file=sys.stderr)
                
        # Limpiar
        try:
            if os.path.exists(text_file_path): os.remove(text_file_path)
        except Exception:
            pass
            
        return revision
            
    except Exception as e:
        print(f"Ocurrió un error inesperado al invocar {agent} para verificación de guía: {e}", file=sys.stderr)
        
    return ""


def run_agent_api(text_content: str, api_llm: str, api_model: str) -> list:
    """
    Ejecuta el agente utilizando llamadas directas a la API del proveedor seleccionado.
    """
    system_personality, _ = load_prompts()
    system_prompt = f"{system_personality}\n\n{SYSTEM_PROMPT_JSON_INSTRUCTIONS}"
    prompt = f"{system_prompt}\n\nEl texto a analizar es el siguiente:\n\n{text_content}"
    
    url = ""
    headers = {}
    payload = {}
    
    try:
        if api_llm == "ChatGPT":
            api_key = os.environ.get("OPENAI_API_KEY", "")
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": api_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }
        elif api_llm == "Gemini":
            api_key = os.environ.get("GEMINI_API_KEY", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{api_model}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2}
            }
        elif api_llm == "Claude":
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": api_model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }
        elif api_llm == "Grok":
            api_key = os.environ.get("XAI_API_KEY", "")
            url = "https://api.x.ai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": api_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }
        else:
            return []

        max_retries = 10
        base_delay = 5
        for attempt in range(max_retries):
            if api_llm == "Gemini":
                gemini_rate_limiter.wait()
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in [429, 500, 502, 503, 504]:
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    delay = float(retry_after) + random.uniform(1, 3)
                else:
                    delay = base_delay * (2 ** attempt) + random.uniform(1, 5)
                print(f"  [AVISO] HTTP {response.status_code} por {api_llm}. Reintentando en {delay:.1f}s...", file=sys.stderr)
                time.sleep(delay)
                continue
            response.raise_for_status()
            break
        else:
            response.raise_for_status()
        data = response.json()
        
        response_text = ""
        if api_llm in ["ChatGPT", "Grok"]:
            response_text = data["choices"][0]["message"]["content"]
        elif api_llm == "Gemini":
            response_text = data["candidates"][0]["content"]["parts"][0]["text"]
        elif api_llm == "Claude":
            response_text = data["content"][0]["text"]

        clean_text = response_text.strip()
        
        parsed = None
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', clean_text)
        if match:
            try:
                parsed = json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        if parsed is None:
            match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', clean_text)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
                    
        if parsed is None:
            match = re.search(r'\{\s*"original"[\s\S]*\}', clean_text)
            if match:
                try:
                    parsed = [json.loads(match.group(0))]
                except json.JSONDecodeError:
                    pass
                    
        if parsed is None:
            try:
                parsed = json.loads(clean_text)
            except json.JSONDecodeError:
                print(f"  [ERROR] No se pudo parsear el JSON generado por {api_llm}:\n{clean_text}", file=sys.stderr)
                
        if isinstance(parsed, list): return parsed
        if isinstance(parsed, dict): return [parsed]
        
    except Exception as e:
        print(f"Ocurrió un error inesperado al invocar {api_llm} via API: {e}", file=sys.stderr)
        
    return []

def run_guide_review_api(full_text: str, guide_text: str, api_llm: str, api_model: str) -> str:
    """
    Ejecuta el agente para verificación de guía utilizando la API directa.
    """
    _, guide_prompt = load_prompts()
    prompt = f"{guide_prompt}\n\n=== GUÍA / MANUAL ===\n{guide_text}\n\n=== DOCUMENTO A REVISAR ===\n{full_text}"
    
    url = ""
    headers = {}
    payload = {}
    
    try:
        if api_llm == "ChatGPT":
            api_key = os.environ.get("OPENAI_API_KEY", "")
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": api_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
        elif api_llm == "Gemini":
            api_key = os.environ.get("GEMINI_API_KEY", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{api_model}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3}
            }
        elif api_llm == "Claude":
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": api_model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
        elif api_llm == "Grok":
            api_key = os.environ.get("XAI_API_KEY", "")
            url = "https://api.x.ai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": api_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
        else:
            return ""

        max_retries = 10
        base_delay = 5
        for attempt in range(max_retries):
            if api_llm == "Gemini":
                gemini_rate_limiter.wait()
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in [429, 500, 502, 503, 504]:
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    delay = float(retry_after) + random.uniform(1, 3)
                else:
                    delay = base_delay * (2 ** attempt) + random.uniform(1, 5)
                print(f"  [AVISO] HTTP {response.status_code} por {api_llm}. Reintentando en {delay:.1f}s...", file=sys.stderr)
                time.sleep(delay)
                continue
            response.raise_for_status()
            break
        else:
            response.raise_for_status()
        data = response.json()
        
        if api_llm in ["ChatGPT", "Grok"]:
            return data["choices"][0]["message"]["content"].strip()
        elif api_llm == "Gemini":
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        elif api_llm == "Claude":
            return data["content"][0]["text"].strip()
            
    except Exception as e:
        print(f"Ocurrió un error al invocar {api_llm} para verificación de guía: {e}", file=sys.stderr)
        
    return ""

def find_text_bounds(page, target: str) -> list:
    """
    Busca una palabra o frase en la página del PDF y devuelve sus rectángulos.
    Usa coincidencia de palabras completas, normalización de ligaduras,
    búsqueda de variantes (guiones, espacios, ligaduras) y
    fusión de bloques contiguos si la palabra está fragmentada internamente en el PDF.
    """
    target = target.strip()
    if not target:
        return []
        
    cleaned_target = clean_ligatures(target).strip()
    
    # Lista de variantes seguras a buscar con search_for
    search_candidates = [
        target,
        cleaned_target,
        target.replace(" ", "-"),
        target.replace("-", " "),
        target.replace(" ", ""),
    ]
    seen_cand = set()
    unique_candidates = []
    for c in search_candidates:
        if c and c not in seen_cand:
            seen_cand.add(c)
            unique_candidates.append(c)

    # Si contiene espacios o guiones, es una frase o rango: probar search_for primero
    if " " in target or " " in cleaned_target or "-" in target or "-" in cleaned_target:
        for cand in unique_candidates:
            rects = page.search_for(cand)
            if rects:
                return rects
        
    # Formato de word: (x0, y0, x1, y1, "texto", block_no, line_no, word_no)
    words = page.get_text("words")
    rects = []
    cand_lowers = {c.lower() for c in unique_candidates}
    
    # 1. Coincidencia directa o normalizada en palabras individuales
    for w in words:
        w_text = w[4]
        # Limpiar signos de puntuación comunes alrededor de la palabra
        cleaned_w = w_text.strip(',.¡!¿?()[]{};:"\'')
        normalized_w = clean_ligatures(cleaned_w)
        
        if (
            cleaned_w.lower() in cand_lowers
            or normalized_w.lower() in cand_lowers
        ):
            rects.append(pymupdf.Rect(w[:4]))
            
    # 2. Si no se encontró, buscar palabras fragmentadas en 2 o 3 tokens contiguos (ej. "con" + "icto", "pp." + "45" + "55")
    if not rects and len(words) >= 2:
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i+1]
            if w1[5] == w2[5] and w1[6] == w2[6]:
                comb_no_space = w1[4].strip(',.¡!¿?()[]{};:"\'') + w2[4].strip(',.¡!¿?()[]{};:"\'')
                comb_space = w1[4].strip(',.¡!¿?()[]{};:"\'') + " " + w2[4].strip(',.¡!¿?()[]{};:"\'')
                norm_no_space = clean_ligatures(comb_no_space)
                norm_space = clean_ligatures(comb_space)
                
                if any(t in cand_lowers for t in [comb_no_space.lower(), comb_space.lower(), norm_no_space.lower(), norm_space.lower()]):
                    r1 = pymupdf.Rect(w1[:4])
                    r2 = pymupdf.Rect(w2[:4])
                    rects.append(r1 | r2)
            
    # 3. Fallback: búsqueda directa de todos los candidatos con search_for
    if not rects:
        for cand in unique_candidates:
            rects = page.search_for(cand)
            if rects:
                return rects
        
    return rects

_LIGATURE_SPLIT_RE = re.compile(r'(ffi|ffl|ff|fi|fl)', re.IGNORECASE)

def _ligature_variants(lig: str) -> list:
    """Formas en que una ligadura puede aparecer rota tras la extracción."""
    variants = {lig, "", " ", "-"}
    for i in range(len(lig)):
        for j in range(i + 1, len(lig) + 1):
            variants.add(lig[i:j])
    return sorted(variants, key=len, reverse=True)

def es_falso_positivo_ligadura(original: str, corregido: str, explicacion: str = "") -> bool:
    """
    Detecta sugerencias causadas por ligaduras perdidas en la extracción:
    'original' y 'corregido' solo difieren en secuencias fi/fl/ff/ffi/ffl
    (eliminadas, partidas o reemplazadas por espacio/guion).
    """
    if not original or not corregido:
        return False
    if "ligadura" in (explicacion or "").lower():
        return True
    if original.lower() == corregido.lower():
        return False
    parts = _LIGATURE_SPLIT_RE.split(corregido)
    if len(parts) == 1:
        return False
    pattern = []
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            alts = "|".join(re.escape(v) for v in _ligature_variants(part.lower()))
            pattern.append(f"(?:{alts})")
        else:
            pattern.append(re.escape(part))
    return re.fullmatch("".join(pattern), original, re.IGNORECASE) is not None

def filtrar_falsos_positivos_ligadura(errs) -> tuple:
    """Devuelve (errores_filtrados, cantidad_descartada)."""
    if not isinstance(errs, list):
        return [], 0
    filtrados = []
    for err in errs:
        if not isinstance(err, dict):
            continue
        if es_falso_positivo_ligadura(
            str(err.get("original", "")).strip(),
            str(err.get("corregido", "")).strip(),
            str(err.get("explicacion", "")),
        ):
            continue
        filtrados.append(err)
    return filtrados, len(errs) - len(filtrados)

def crear_barra_progreso(actual: int, total: int, ancho: int = 20) -> str:
    """Genera una barra de progreso visual en formato texto."""
    if total <= 0:
        return f"[{'░' * ancho}] 0/0 (0.0%)"
    porcentaje = (actual / total) * 100
    llenos = int(ancho * actual // total)
    barra = "█" * llenos + "░" * (ancho - llenos)
    return f"[{barra}] {actual}/{total} páginas ({porcentaje:.1f}%)"

def corregir_reporte_pdf(input_path: str, output_path: str, num_agents: int = 10, agent_name: str = "Antigravity", mode: str = "cli", api_llm: str = "", api_model: str = "", do_spelling: bool = True, do_methodology: bool = True, do_guide: bool = False, guide_path: str = "", cli_model: str = "", skip_first_pages: int = 0, stop_event=None, progress_callback=None):
    """
    Abre el PDF de entrada, analiza errores ortográficos y/o metodología de tesis,
    agrega anotaciones al PDF y guarda el resultado.
    """
    if not os.path.exists(input_path):
        print(f"Error: El archivo de entrada '{input_path}' no existe.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Abriendo PDF: {input_path}")
    doc = pymupdf.open(input_path)
    total_paginas = len(doc)
    
    print("\n==================================================")
    print("INICIANDO PROCESO DE CORRECCIÓN DE DOCUMENTO")
    print(f"Total de páginas a procesar: {total_paginas}")
    if skip_first_pages > 0:
        print(f"Páginas iniciales omitidas (portada/índice/agradecimientos): 1 a {skip_first_pages}")
    print(f"Progreso inicial: {crear_barra_progreso(0, total_paginas)}")
    print("==================================================\n")
    
    if progress_callback:
        progress_callback(0, total_paginas)
    
    total_errores_detectados = 0
    total_anotaciones_creadas = 0
    
    # Extracción de texto de todas las páginas con el motor de alta fidelidad
    all_pages_text_list = extract_all_pages_text(input_path, doc)
    all_pages_text = []
    for page_num, page_text in enumerate(all_pages_text_list):
        if page_num < skip_first_pages:
            continue
        if page_text:
            all_pages_text.append(f"--- PÁGINA {page_num + 1} ---\n{page_text}")
    full_text = "\n\n".join(all_pages_text)
    
    if do_spelling:
        page_errors = {}
        # Agrupar páginas en lotes (chunks) para reducir llamadas al LLM hasta un 80%
        # Lotes de hasta 4 páginas o 12,000 caracteres
        PAGE_BATCH_SIZE = 4
        batches = []
        current_batch = []
        current_chars = 0
        for p_idx in range(total_paginas):
            if p_idx < skip_first_pages:
                continue
            p_txt = all_pages_text_list[p_idx] if p_idx < len(all_pages_text_list) else ""
            if not p_txt.strip():
                continue
            if len(current_batch) >= PAGE_BATCH_SIZE or (current_chars + len(p_txt) > 12000 and current_batch):
                batches.append(current_batch)
                current_batch = [p_idx]
                current_chars = len(p_txt)
            else:
                current_batch.append(p_idx)
                current_chars += len(p_txt)
        if current_batch:
            batches.append(current_batch)

        total_batches = len(batches)
        print(f"\n--- Analizando ortografía optimizada: {total_paginas} páginas agrupadas en {total_batches} lotes ({num_agents} hilos) ---")

        def procesar_lote(batch_indices: list):
            if stop_event and stop_event.is_set():
                return batch_indices, {}
            # Construir texto del lote con delimitadores claros
            chunk_sections = []
            for b_idx in batch_indices:
                t = all_pages_text_list[b_idx]
                chunk_sections.append(f"=== PÁGINA {b_idx + 1} ===\n{t}")
            chunk_text = "\n\n".join(chunk_sections)

            lbl_pages = f"{batch_indices[0] + 1}-{batch_indices[-1] + 1}" if len(batch_indices) > 1 else f"{batch_indices[0] + 1}"
            print(f"Lanzando revisión de Lote [Págs {lbl_pages}] ({len(batch_indices)} págs)...")

            if mode == "api":
                raw_errs = run_agent_api(chunk_text, api_llm, api_model)
            else:
                raw_errs = run_agent_cli(chunk_text, batch_indices[0] + 1, agent_name, cli_model)

            raw_errs, _ = filtrar_falsos_positivos_ligadura(raw_errs)

            # Distribuir los errores a la página que efectivamente contiene la frase original
            results_by_page = {idx: [] for idx in batch_indices}
            for err in raw_errs:
                orig = err.get("original", "").strip()
                if not orig:
                    continue
                orig_lower = orig.lower()
                matched = False
                for b_idx in batch_indices:
                    ptxt = all_pages_text_list[b_idx].lower()
                    if orig_lower in ptxt:
                        err_copy = dict(err)
                        err_copy["pagina"] = b_idx + 1
                        results_by_page[b_idx].append(err_copy)
                        matched = True
                        break
                if not matched and batch_indices:
                    # Fallback a la primera página del lote
                    err_copy = dict(err)
                    err_copy["pagina"] = batch_indices[0] + 1
                    results_by_page[batch_indices[0]].append(err_copy)

            return batch_indices, results_by_page

        batches_procesados = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_agents) as executor:
            futures = {executor.submit(procesar_lote, b): b for b in batches}
            for future in concurrent.futures.as_completed(futures):
                if stop_event and stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                try:
                    b_indices, res_map = future.result()
                    for b_idx, err_list in res_map.items():
                        page_errors[b_idx] = err_list
                    batches_procesados += 1
                    paginas_procesadas = sum(len(b) for b in batches[:batches_procesados])
                    barra_txt = crear_barra_progreso(paginas_procesadas, total_paginas)
                    tot_errs_batch = sum(len(el) for el in res_map.values())
                    lbl_pages = f"{b_indices[0] + 1}-{b_indices[-1] + 1}" if len(b_indices) > 1 else f"{b_indices[0] + 1}"
                    print(f"✓ {barra_txt} | Lote [Págs {lbl_pages}] completado ({tot_errs_batch} errores).")
                    if progress_callback:
                        progress_callback(paginas_procesadas, total_paginas)
                except Exception as exc:
                    batches_procesados += 1
                    paginas_procesadas = sum(len(b) for b in batches[:batches_procesados])
                    barra_txt = crear_barra_progreso(paginas_progreso if (paginas_progreso := paginas_procesadas) <= total_paginas else total_paginas, total_paginas)
                    print(f"✗ {barra_txt} | El lote generó una excepción: {exc}", file=sys.stderr)
                    if progress_callback:
                        progress_callback(paginas_procesadas, total_paginas)

        if stop_event and stop_event.is_set():
            print("Proceso detenido por el usuario.")
            return

        print("\n--- Aplicando anotaciones de ortografía al PDF ---")
        for page_num in range(total_paginas):
            page = doc[page_num]
            errors = page_errors.get(page_num, [])
            
            if not errors:
                continue
                
            for err in errors:
                original = err.get("original", "").strip()
                corregido = err.get("corregido", "").strip()
                tipo = err.get("tipo", "ortografía").strip()
                explicacion = err.get("explicacion", "").strip()
                
                # Filtrar entradas vacías o falsos positivos idénticos
                if not original or not corregido or original.lower() == corregido.lower():
                    continue
                    
                total_errores_detectados += 1
                
                # Buscar la ubicación del error en la página
                rects = find_text_bounds(page, original)
                
                if not rects:
                    print(f"  [AVISO Pág {page_num + 1}] No se encontraron coordenadas exactas para la palabra '{original}' en el PDF.")
                    continue
                    
                print(f"  [ERROR Pág {page_num + 1}] '{original}' -> '{corregido}' ({tipo})")
                
                for rect in rects:
                    highlight = page.add_highlight_annot(rect)
                    contenido_comentario = (
                        f"Tipo: {tipo.capitalize()}\n"
                        f"Corrección sugerida: {corregido}\n"
                        f"Detalle: {explicacion}"
                    )
                    highlight.set_info(
                        title="Quirón",
                        subject=f"Error de {tipo}",
                        content=contenido_comentario
                    )
                    highlight.set_colors(stroke=(1.0, 0.8, 0.0))
                    highlight.update()
                    total_anotaciones_creadas += 1

    # Guardar estado actual del documento antes de la revisión metodológica
    temp_intermediate_path = output_path + ".spelling_tmp.pdf"
    doc.save(temp_intermediate_path)
    doc.close()

    if do_methodology:
        if stop_event and stop_event.is_set():
            if os.path.exists(temp_intermediate_path):
                os.remove(temp_intermediate_path)
            return
        # --- REVISIÓN DE METODOLOGÍA (THESIS REVIEWER / 4 SINODALES) ---
        print("\n==================================================")
        print("INICIANDO REVISIÓN DE METODOLOGÍA Y ESTRUCTURA (4 SINODALES)")
        print("==================================================")
        try:
            from thesis_reviewer import ThesisReviewPipeline
            pipeline = ThesisReviewPipeline(agy_command="agy", model=cli_model)
            temp_meth_output = output_path + ".meth_tmp.pdf"
            
            # Ejecutar auditoría sobre el PDF con anotaciones previas
            pipeline.run(input_pdf=temp_intermediate_path, output_pdf=temp_meth_output, skip_first_pages=skip_first_pages)
            
            # Reemplazar el archivo intermedio por el que tiene las anotaciones metodológicas
            if os.path.exists(temp_intermediate_path):
                os.remove(temp_intermediate_path)
            temp_intermediate_path = temp_meth_output
            print("✓ Revisión de metodología y anotaciones de sinodales aplicadas exitosamente.")
        except Exception as e:
            print(f"  [ERROR] Falló la revisión de metodología: {e}", file=sys.stderr)

    # Reabrir el doc resultante si aún requerimos tareas posteriores o guardado final
    doc = pymupdf.open(temp_intermediate_path)

    if do_guide and guide_path and os.path.exists(guide_path):
        if stop_event and stop_event.is_set():
            return
        print(f"\n--- Iniciando extracción de texto de la guía: {guide_path} ---")
        try:
            guide_doc = pymupdf.open(guide_path)
            guide_pages_list = extract_all_pages_text(guide_path, guide_doc)
            guide_full_text = "\n\n".join([gt for gt in guide_pages_list if gt])
            guide_doc.close()
            
            agent_display = f"{api_llm} ({api_model})" if mode == "api" else (f"{agent_name} ({cli_model})" if cli_model else agent_name)
            print(f"--- Iniciando verificación de guía usando {agent_display} ---")
            
            if mode == "api":
                verificacion_guia = run_guide_review_api(full_text, guide_full_text, api_llm, api_model)
            else:
                verificacion_guia = run_guide_review_cli(full_text, guide_full_text, agent_name, cli_model)
                
            if verificacion_guia:
                base, _ = os.path.splitext(input_path)
                guia_output_path = f"{base}_verificacion_guia.txt"
                with open(guia_output_path, "w", encoding="utf-8") as f:
                    f.write(verificacion_guia)
                print(f"Verificación de guía guardada exitosamente en: {guia_output_path}")
            else:
                print("No se pudo obtener la verificación de guía.")
        except Exception as e:
            print(f"Error al procesar la guía: {e}", file=sys.stderr)

    # Guardar el PDF copia con las anotaciones
    print(f"\nGuardando PDF corregido en: {output_path}...")
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        temp_output_path = output_path + ".tmp.pdf"
        doc.save(temp_output_path)
        doc.close()
        os.replace(temp_output_path, output_path)
    else:
        doc.save(output_path)
        doc.close()
    
    # Limpiar archivo temporal intermedio si aún existiera
    if os.path.exists(temp_intermediate_path) and os.path.abspath(temp_intermediate_path) != os.path.abspath(output_path):
        try:
            os.remove(temp_intermediate_path)
        except Exception:
            pass

    print("\n==================================================")
    print("PROCESO TERMINADO EXITOSAMENTE")
    print(f"Archivo original: {input_path}")
    print(f"Copia comentada:  {output_path}")
    print(f"Errores ortográficos detectados: {total_errores_detectados}")
    print(f"Anotaciones agregadas en PDF: {total_anotaciones_creadas}")
    print("==================================================")

def main():
    parser = argparse.ArgumentParser(
        description="Corrige errores ortográficos y audita metodología en reportes/tesis PDF usando antigravity-cli."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Ruta al archivo PDF original (reporte de estadía o tesis)."
    )
    parser.add_argument(
        "-o", "--output",
        help="Ruta donde se guardará el PDF corregido. Por defecto sobrescribe el archivo original."
    )
    parser.add_argument(
        "-a", "--agents",
        type=int,
        default=10,
        help="Número de hilos a ejecutar en paralelo para ortografía. Por defecto es 10."
    )
    parser.add_argument(
        "-g", "--guide",
        help="Ruta al PDF de la guía/manual para verificar el cumplimiento. Opcional."
    )
    parser.add_argument(
        "--agent-cli",
        choices=["Antigravity", "GitHub CLI", "Claude Code"],
        default="Antigravity",
        help="CLI a utilizar para la corrección."
    )
    parser.add_argument(
        "-m", "--model",
        default="",
        help="Modelo a utilizar en CLI (ej. gemini-3.7-flash, gemini-3.7-pro, claude-3-7-sonnet)."
    )
    parser.add_argument(
        "--skip-spelling",
        action="store_true",
        help="Omite la corrección ortográfica."
    )
    parser.add_argument(
        "--skip-methodology",
        action="store_true",
        help="Omite la revisión de metodología y sinodales."
    )
    
    args = parser.parse_args()
    
    input_path = os.path.abspath(args.input)
    
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        # Sobrescribir el archivo original
        output_path = input_path
        
    guide_path = ""
    if args.guide:
        guide_path = os.path.abspath(args.guide)
        
    corregir_reporte_pdf(input_path, output_path, args.agents, args.agent_cli, do_spelling=not args.skip_spelling, do_methodology=not args.skip_methodology, do_guide=bool(guide_path), guide_path=guide_path, cli_model=args.model)

if __name__ == "__main__":
    main()
