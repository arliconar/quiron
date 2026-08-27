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

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

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

# Patrones morfológicos y de referencias académicas para reconstruir texto
# donde la ligadura (fl, fi, ff) o guiones de rango fueron extraídos rotos o con espacios
RECONSTRUCTION_PATTERNS = [
    # Rangos de páginas y números en referencias/bibliografía
    (r'\bpp\.\s*(\d+)\s+(\d+)\b', r'pp. \1-\2'),
    (r'\bno\.\s*(\d+)\s+(\d+)\b', r'no. \1-\2'),
    (r'\bvol\.\s*(\d+)\s+(\d+)\b', r'vol. \1-\2'),
    (r'\bpág\.\s*(\d+)\s+(\d+)\b', r'pág. \1-\2'),
    (r'\bpágs\.\s*(\d+)\s+(\d+)\b', r'págs. \1-\2'),
    
    # Palabras con 'fl'
    (r'\bcon[\s\ue000-\uf8ff]?icto\b', 'conflicto'),
    (r'\bcon[\s\ue000-\uf8ff]?ictos\b', 'conflictos'),
    (r'\bcon[\s\ue000-\uf8ff]?ictiv', 'conflictiv'),
    (r'\bin[\s\ue000-\uf8ff]?aci', 'inflaci'),
    (r'\bin[\s\ue000-\uf8ff]?uir\b', 'influir'),
    (r'\bin[\s\ue000-\uf8ff]?uyen', 'influyen'),
    (r'\bin[\s\ue000-\uf8ff]?uencia', 'influencia'),
    (r'\bin[\s\ue000-\uf8ff]?uencias', 'influencias'),
    (r'\bin[\s\ue000-\uf8ff]?ujo\b', 'influjo'),
    (r'\bin[\s\ue000-\uf8ff]?amaci', 'inflamaci'),
    (r'\bre[\s\ue000-\uf8ff]?exi', 'reflexi'),
    (r'\bre[\s\ue000-\uf8ff]?ej', 'reflej'),
    (r'\bre[\s\ue000-\uf8ff]?ujo\b', 'reflujo'),
    (r'\ba[\s\ue000-\uf8ff]?uent', 'afluent'),
    (r'\ba[\s\ue000-\uf8ff]?uenci', 'afluenci'),
    (r'\ba[\s\ue000-\uf8ff]?igi', 'afligi'),
    (r'\b[\s\ue000-\uf8ff]?ujo\b', 'flujo'),
    (r'\b[\s\ue000-\uf8ff]?ujos\b', 'flujos'),
    (r'\b[\s\ue000-\uf8ff]?uido\b', 'fluido'),
    (r'\b[\s\ue000-\uf8ff]?uidos\b', 'fluidos'),
    (r'\b[\s\ue000-\uf8ff]?uid', 'fluid'),
    (r'\b[\s\ue000-\uf8ff]?exib', 'flexib'),
    (r'\b[\s\ue000-\uf8ff]?echa\b', 'flecha'),
    (r'\b[\s\ue000-\uf8ff]?echas\b', 'flechas'),
    (r'\b[\s\ue000-\uf8ff]?ora\b', 'flora'),
    (r'\b[\s\ue000-\uf8ff]?ores\b', 'flores'),
    (r'\b[\s\ue000-\uf8ff]?or\b', 'flor'),
    (r'\b[\s\ue000-\uf8ff]?ot', 'flot'),
    
    # Palabras con 'fi' / 'ff' / 'f' y casos científicos/académicos comunes
    (r'\bPonti[\s\ue000-\uf8ff]?cia\b', 'Pontificia'),
    (r'\bponti[\s\ue000-\uf8ff]?cia\b', 'pontificia'),
    (r'\bDi[\s\ue000-\uf8ff]?erenti', 'Differenti'),
    (r'\bdi[\s\ue000-\uf8ff]?erenti', 'differenti'),
    (r'\bde[\s\ue000-\uf8ff]?nici', 'definici'),
    (r'\bde[\s\ue000-\uf8ff]?nir\b', 'definir'),
    (r'\bde[\s\ue000-\uf8ff]?nitiv', 'definitiv'),
    (r'\bde[\s\ue000-\uf8ff]?nid', 'definid'),
    (r'\bcon[\s\ue000-\uf8ff]?gura', 'configura'),
    (r'\bcon[\s\ue000-\uf8ff]?anza\b', 'confianza'),
    (r'\bcon[\s\ue000-\uf8ff]?ar\b', 'confiar'),
    (r'\bcon[\s\ue000-\uf8ff]?rm', 'confirm'),
    (r'\bsigni[\s\ue000-\uf8ff]?ica', 'significa'),
    (r'\bbene[\s\ue000-\uf8ff]?ici', 'benefici'),
    (r'\be[\s\ue000-\uf8ff]?ici', 'efici'),
    (r'\be[\s\ue000-\uf8ff]?caz\b', 'eficaz'),
    (r'\be[\s\ue000-\uf8ff]?caces\b', 'eficaces'),
    (r'\be[\s\ue000-\uf8ff]?cacia\b', 'eficacia'),
    (r'\bdi[\s\ue000-\uf8ff]?cult', 'dificult'),
    (r'\bdi[\s\ue000-\uf8ff]?ícil', 'difícil'),
    (r'\bdi[\s\ue000-\uf8ff]?icil', 'difícil'),
    (r'\bdi[\s\ue000-\uf8ff]?erenc', 'diferenc'),
    (r'\bdi[\s\ue000-\uf8ff]?erent', 'diferent'),
    (r'\bin[\s\ue000-\uf8ff]?ormaci', 'informaci'),
    (r'\bin[\s\ue000-\uf8ff]?orme\b', 'informe'),
    (r'\bin[\s\ue000-\uf8ff]?ormes\b', 'informes'),
    (r'\bin[\s\ue000-\uf8ff]?ormat', 'informat'),
    (r'\b[\s\ue000-\uf8ff]?iltro\b', 'filtro'),
    (r'\b[\s\ue000-\uf8ff]?iltros\b', 'filtros'),
    (r'\b[\s\ue000-\uf8ff]?iltr', 'filtr'),
    (r'\b[\s\ue000-\uf8ff]?inal\b', 'final'),
    (r'\b[\s\ue000-\uf8ff]?inanz', 'finanz'),
    (r'\b[\s\ue000-\uf8ff]?ísica\b', 'física'),
    (r'\b[\s\ue000-\uf8ff]?isic', 'fisic'),
]

# Expresiones regulares precompiladas para máxima velocidad
COMPILED_RECONSTRUCTIONS = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in RECONSTRUCTION_PATTERNS
]
DEHYPHEN_RE = re.compile(r'(\b\w+)-\n(\w+\b)')
PUA_RE = re.compile(r'[\ue000-\uf8ff]')
CID_RE = re.compile(r'\(cid:(\d+)\)')

def decode_cid_match(m) -> str:
    """Traduce códigos (cid:NNN) de fuentes PDF/pdfminer a caracteres legibles (ej. (cid:243) -> ó)."""
    try:
        code = int(m.group(1))
        if 32 <= code <= 255:
            return bytes([code]).decode('cp1252', errors='replace')
        elif code > 255:
            return chr(code)
    except Exception:
        pass
    return ""

def clean_ligatures(text: str) -> str:
    """
    Heurística profunda de limpieza y reconstrucción de texto:
    1. Traduce códigos (cid:NNN) generados por pdfminer / pdfplumber.
    2. Normaliza ligaduras Unicode estándar (fi, fl, ff, ffi, ffl, etc.).
    3. Resuelve dehyphenation (guiones de corte de palabra al final de línea).
    4. Normaliza caracteres Unicode mediante compatibilidad NFKC.
    5. Reconstruye palabras rotas por huecos o pérdidas de glifos en español/académico.
    6. Limpia códigos residuales de la zona de uso privado (PUA).
    """
    if not text:
        return ""
    
    # 1. Traducir códigos CID no mapeados de pdfminer (ej. (cid:243) -> ó)
    if "(cid:" in text:
        text = CID_RE.sub(decode_cid_match, text)
    
    # 2. Ligaduras estándar conocidas
    for lig, rep in LIGATURE_MAP.items():
        if lig in text:
            text = text.replace(lig, rep)
        
    # 3. Dehyphenation básico
    text = DEHYPHEN_RE.sub(r'\1\2', text)
    
    # 4. Normalización NFKC
    text = unicodedata.normalize("NFKC", text)
    
    # 5. Reconstrucción morfológica con regex precompiladas
    for compiled_re, replacement in COMPILED_RECONSTRUCTIONS:
        def repl(match, rep=replacement):
            matched = match.group(0)
            if matched and matched[0].isupper():
                return rep.capitalize()
            return rep
        text = compiled_re.sub(repl, text)
        
    # 6. Limpieza residual de caracteres de uso privado no asignados
    text = PUA_RE.sub('', text)
    
    return text

def fast_normalize_word(text: str) -> str:
    """Normalización ultrarrápida en memoria para tokens individuales de búsqueda."""
    if not text:
        return ""
    if "(cid:" in text:
        text = CID_RE.sub(decode_cid_match, text)
    for lig, rep in LIGATURE_MAP.items():
        if lig in text:
            text = text.replace(lig, rep)
    return unicodedata.normalize("NFKC", text).lower()

def extract_all_pages_text(pdf_path: str, doc) -> list:
    """
    Extrae el texto de todas las páginas de un PDF usando pdfplumber como motor principal
    para máxima fidelidad en fuentes y ligaduras rotas, con respaldo en PyMuPDF.
    """
    pages_text = []
    total_pages = len(doc)
    
    if HAS_PDFPLUMBER and pdf_path and os.path.exists(pdf_path):
        try:
            print("Extrayendo texto con motor de alta precisión (pdfplumber)...")
            with pdfplumber.open(pdf_path) as pdf:
                for p in pdf.pages:
                    txt = p.extract_text(layout=False) or ""
                    pages_text.append(clean_ligatures(txt).strip())
        except Exception as e:
            print(f"Aviso con pdfplumber: {e}, usando PyMuPDF...", file=sys.stderr)
            pages_text = []
            
    if not pages_text:
        print("Extrayendo texto con PyMuPDF...")
        for page_num in range(total_pages):
            txt = doc[page_num].get_text("text") or ""
            pages_text.append(clean_ligatures(txt).strip())
            
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
    "2. Si no hay errores, devuelve un arreglo vacío `[]`.\n"
    "3. La palabra o frase en 'original' DEBE coincidir carácter por carácter con el texto original. Presta mucha atención a mayúsculas, minúsculas y acentos.\n"
    "4. No inventes errores de estilo subjetivos. Concéntrate en errores objetivos.\n"
    "5. No corrijas nombres propios de herramientas o tecnologías conocidas (ej. Python, PostgreSQL, Docker, etc.).\n"
    "6. Si encuentras una palabra que parece haber perdido letras o tener espacios extra por problemas de extracción de fuentes del PDF (ej. ligaduras como 'fl' o 'fi'), devuélvela corregida con su grafía completa y correcta en español.\n"
)

DEFAULT_DICTAMEN_PROMPT = (
    "Eres un Académico evaluando un documento (reporte, tesis, memoria, etc.). "
    "Tu tarea es revisar rigurosamente el contenido técnico, la estructura, la coherencia y la profundidad del trabajo. "
    "Crea un dictamen con correcciones y sugerencias acerca del contenido. "
    "Para cada observación, incluye (si es posible): el capítulo, la hoja/página, el texto original al que haces referencia, y la mejora sugerida. "
    "Tu respuesta debe estar en texto claro, estructurado y profesional."
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
                    data.get("dictamen_prompt", DEFAULT_DICTAMEN_PROMPT),
                    data.get("guide_prompt", DEFAULT_GUIDE_PROMPT)
                )
        except Exception:
            pass
    return DEFAULT_SYSTEM_PERSONALITY, DEFAULT_DICTAMEN_PROMPT, DEFAULT_GUIDE_PROMPT

def run_agent_cli(text_content: str, page_num: int, agent: str = "Antigravity", model: str = "") -> list:
    """
    Ejecuta el agente instruyéndole a leer un archivo de texto y generar un JSON con los errores.
    Devuelve la lista de errores encontrados.
    """
    try:
        system_personality, _, _ = load_prompts()
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
            cmd = ["agy", "--dangerously-skip-permissions", "-p", prompt_str]
        
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

def run_content_review_cli(text_content: str, agent: str = "Antigravity", model: str = "") -> str:
    """
    Ejecuta el agente para una revisión de contenido técnico usando el dictamen,
    leyendo y escribiendo en archivos para evitar problemas de longitud.
    """
    try:
        _, dictamen_prompt, _ = load_prompts()
        text_file_path = os.path.abspath("temp_revision_contenido.txt")
        
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(text_content)
            
        prompt = (
            f"{dictamen_prompt}\n\n"
            f"El documento completo se encuentra en el archivo: {text_file_path}\n"
            "Lee ese archivo, realiza tu revisión y devuelve el reporte resultante como tu única respuesta."
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
            print(f"  [ERROR] El agente no generó respuesta en stdout para revisión de contenido. Error: {result.stderr}", file=sys.stderr)
                
        # Limpiar archivos temporales
        try:
            if os.path.exists(text_file_path): os.remove(text_file_path)
        except Exception as e:
            print(f"  [AVISO] No se pudieron borrar archivos temporales: {e}", file=sys.stderr)
            
        return revision
            
    except Exception as e:
        print(f"Ocurrió un error inesperado al invocar {agent} para revisión: {e}", file=sys.stderr)
        
    return ""

def run_guide_review_cli(full_text: str, guide_text: str, agent: str = "Antigravity", model: str = "") -> str:
    """
    Ejecuta el agente para una verificación de guía usando el guide_prompt.
    """
    try:
        _, _, guide_prompt = load_prompts()
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
    system_personality, _, _ = load_prompts()
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
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in [429, 500, 502, 503, 504]:
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

def run_content_review_api(text_content: str, api_llm: str, api_model: str) -> str:
    """
    Ejecuta el agente para revisión de contenido utilizando la API directa.
    """
    _, dictamen_prompt, _ = load_prompts()
    prompt = f"{dictamen_prompt}\n\nEl documento completo es el siguiente:\n\n{text_content}"
    
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
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in [429, 500, 502, 503, 504]:
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
        print(f"Ocurrió un error al invocar {api_llm} para revisión: {e}", file=sys.stderr)
        
    return ""

def run_guide_review_api(full_text: str, guide_text: str, api_llm: str, api_model: str) -> str:
    """
    Ejecuta el agente para verificación de guía utilizando la API directa.
    """
    _, _, guide_prompt = load_prompts()
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
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in [429, 500, 502, 503, 504]:
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
    
    # Lista de variantes a buscar con search_for
    search_candidates = [
        target,
        cleaned_target,
        target.replace(" ", "-"),
        target.replace("-", " "),
        target.replace(" ", "fi"),
        target.replace(" ", "fl"),
        target.replace(" ", "ff"),
        target.replace("ff", " "),
        target.replace("fi", " "),
        target.replace("fl", " "),
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

def corregir_reporte_pdf(input_path: str, output_path: str, num_agents: int = 10, agent_name: str = "Antigravity", mode: str = "cli", api_llm: str = "", api_model: str = "", report_path: str = "", do_spelling: bool = True, do_dictamen: bool = True, do_guide: bool = False, guide_path: str = "", cli_model: str = "", stop_event=None):
    """
    Abre el PDF de entrada, analiza errores por página usando el CLI seleccionado,
    agrega anotaciones al PDF copia y guarda el resultado.
    """
    if not os.path.exists(input_path):
        print(f"Error: El archivo de entrada '{input_path}' no existe.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Abriendo PDF: {input_path}")
    doc = pymupdf.open(input_path)
    total_paginas = len(doc)
    print(f"Total de páginas a procesar: {total_paginas}")
    
    # Registro de errores globales para no repetirlos
    seen_errors_global = set()
    total_errores_detectados = 0
    total_anotaciones_creadas = 0
    
    # Extracción de texto de todas las páginas con el motor de alta fidelidad
    all_pages_text_list = extract_all_pages_text(input_path, doc)
    all_pages_text = []
    for page_num, page_text in enumerate(all_pages_text_list):
        if page_text:
            all_pages_text.append(f"--- PÁGINA {page_num + 1} ---\n{page_text}")
    full_text = "\n\n".join(all_pages_text)
    
    if do_spelling:
        # Diccionario para guardar los errores detectados por página
        page_errors = {}
        
        def procesar_pagina(page_index: int):
            if stop_event and stop_event.is_set():
                return page_index, []
            page_text = all_pages_text_list[page_index] if page_index < len(all_pages_text_list) else ""
            if not page_text:
                return page_index, []
            print(f"Lanzando revisión de Página {page_index + 1}...")
            if mode == "api":
                errs = run_agent_api(page_text, api_llm, api_model)
            else:
                errs = run_agent_cli(page_text, page_index + 1, agent_name, cli_model)
            return page_index, errs

        print(f"\n--- Analizando ortografía en paralelo ({num_agents} instancias) ---")
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_agents) as executor:
            futures = {executor.submit(procesar_pagina, i): i for i in range(total_paginas)}
            for future in concurrent.futures.as_completed(futures):
                if stop_event and stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                try:
                    page_index, errs = future.result()
                    page_errors[page_index] = errs
                    print(f"✓ Página {page_index + 1} completada ({len(errs)} errores).")
                except Exception as exc:
                    print(f"La página generó una excepción: {exc}", file=sys.stderr)

        if stop_event and stop_event.is_set():
            print("Proceso detenido por el usuario.")
            return

        print("\n--- Aplicando anotaciones al PDF ---")
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
                
                if not original:
                    continue
                    
                err_key = original.lower()
                
                # --- EVITAR REPETIR ERRORES (REQUERIMIENTO CLAVE) ---
                if err_key in seen_errors_global:
                    print(f"  [DEDUPLICADO Pág {page_num + 1}] Se omitió el error '{original}' porque ya fue marcado anteriormente.")
                    continue
                    
                seen_errors_global.add(err_key)
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

    txt_output_path = ""
    if do_dictamen:
        if stop_event and stop_event.is_set():
            return
        # --- REVISIÓN DE CONTENIDO (DICTAMEN ACADÉMICO) ---
        agent_display = f"{api_llm} ({api_model})" if mode == "api" else (f"{agent_name} ({cli_model})" if cli_model else agent_name)
        print(f"\n--- Iniciando revisión de contenido global usando {agent_display} ---")
        
        print("Enviando el documento completo para revisión de contenido (esto puede tardar unos momentos)...")
        if mode == "api":
            revision_contenido = run_content_review_api(full_text, api_llm, api_model)
        else:
            revision_contenido = run_content_review_cli(full_text, agent_name, cli_model)
        
        if revision_contenido:
            if report_path:
                txt_output_path = report_path
            else:
                base, _ = os.path.splitext(input_path)
                txt_output_path = f"{base}_revision_contenido.txt"
                
            with open(txt_output_path, "w", encoding="utf-8") as f:
                f.write(revision_contenido)
            print(f"Revisión de contenido guardada exitosamente en: {txt_output_path}")
        else:
            print("No se pudo obtener la revisión de contenido.")

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
    
    print("\n==================================================")
    print("PROCESO TERMINADO EXITOSAMENTE")
    print(f"Archivo original: {input_path}")
    print(f"Copia comentada:  {output_path}")
    if txt_output_path:
        print(f"Revisión de contenido: {txt_output_path}")
    print(f"Errores únicos detectados: {total_errores_detectados}")
    print(f"Anotaciones agregadas en PDF: {total_anotaciones_creadas}")
    print("==================================================")

def main():
    parser = argparse.ArgumentParser(
        description="Corrige errores ortográficos y gramaticales en reportes PDF usando antigravity-cli y crea un PDF copia anotado."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Ruta al archivo PDF original (reporte de estadía)."
    )
    parser.add_argument(
        "-o", "--output",
        help="Ruta donde se guardará el PDF corregido. Por defecto sobrescribe el archivo original."
    )
    parser.add_argument(
        "-a", "--agents",
        type=int,
        default=10,
        help="Número de hilos a ejecutar en paralelo. Por defecto es 10."
    )
    parser.add_argument(
        "-r", "--report-output",
        help="Ruta donde se guardará el reporte de revisión de contenido (txt). Opcional."
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
        "--skip-dictamen",
        action="store_true",
        help="Omite la generación del dictamen académico."
    )
    
    args = parser.parse_args()
    
    input_path = os.path.abspath(args.input)
    
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        # Sobrescribir el archivo original
        output_path = input_path
        
    report_output_path = ""
    if args.report_output:
        report_output_path = os.path.abspath(args.report_output)
        
    guide_path = ""
    if args.guide:
        guide_path = os.path.abspath(args.guide)
        
    corregir_reporte_pdf(input_path, output_path, args.agents, args.agent_cli, report_path=report_output_path, do_spelling=not args.skip_spelling, do_dictamen=not args.skip_dictamen, do_guide=bool(guide_path), guide_path=guide_path, cli_model=args.model)

if __name__ == "__main__":
    main()
