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
import time

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

def run_agent_cli(text_content: str, page_num: int, agent: str = "Antigravity") -> list:
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
            print(f"  [ERROR] El agente no generó respuesta en stdout. Error: {result.stderr}", file=sys.stderr)
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

def run_content_review_cli(text_content: str, agent: str = "Antigravity") -> str:
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

def run_guide_review_cli(full_text: str, guide_text: str, agent: str = "Antigravity") -> str:
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
    Usa coincidencia de palabras completas para evitar falsos positivos de substrings.
    """
    target = target.strip()
    if not target:
        return []
        
    # Si contiene espacios, es una frase: usamos search_for directo
    if " " in target:
        return page.search_for(target)
        
    # Si es una sola palabra, filtramos por palabra completa usando page.get_text("words")
    # Formato de word: (x0, y0, x1, y1, "texto", block_no, line_no, word_no)
    words = page.get_text("words")
    rects = []
    target_lower = target.lower()
    
    for w in words:
        w_text = w[4]
        # Limpiar signos de puntuación comunes alrededor de la palabra
        cleaned_w = w_text.strip(',.¡!¿?()[]{};:"\'')
        if cleaned_w.lower() == target_lower:
            rects.append(pymupdf.Rect(w[:4]))
            
    # Si por alguna razón no se encontró (ej. ligaduras o guiones de división), usamos search_for como respaldo
    if not rects:
        rects = page.search_for(target)
        
    return rects

def corregir_reporte_pdf(input_path: str, output_path: str, num_agents: int = 10, agent_name: str = "Antigravity", mode: str = "cli", api_llm: str = "", api_model: str = "", report_path: str = "", do_spelling: bool = True, do_dictamen: bool = True, do_guide: bool = False, guide_path: str = "", do_crossref: bool = True):
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
    
    # Guardamos el texto completo para el final
    print("Extrayendo texto de todas las páginas...")
    all_pages_text = []
    for page_num in range(total_paginas):
        page_text = doc[page_num].get_text("text").strip()
        if page_text:
            all_pages_text.append(f"--- PÁGINA {page_num + 1} ---\n{page_text}")
    full_text = "\n\n".join(all_pages_text)
    
    if do_spelling:
        # Diccionario para guardar los errores detectados por página
        page_errors = {}
        
        def procesar_pagina(page_index: int):
            page_text = doc[page_index].get_text("text").strip()
            if not page_text:
                return page_index, []
            print(f"Lanzando revisión de Página {page_index + 1}...")
            if mode == "api":
                errs = run_agent_api(page_text, api_llm, api_model)
            else:
                errs = run_agent_cli(page_text, page_index + 1, agent_name)
            return page_index, errs

        print(f"\n--- Analizando ortografía en paralelo ({num_agents} instancias) ---")
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_agents) as executor:
            futures = {executor.submit(procesar_pagina, i): i for i in range(total_paginas)}
            for future in concurrent.futures.as_completed(futures):
                try:
                    page_index, errs = future.result()
                    page_errors[page_index] = errs
                    print(f"✓ Página {page_index + 1} completada ({len(errs)} errores).")
                except Exception as exc:
                    print(f"La página generó una excepción: {exc}", file=sys.stderr)

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

    if do_crossref:
        print("\n--- Verificando Referencias Cruzadas (Imágenes y Bibliografía) ---")
        import re
        figuras = set(re.findall(r'(Figura\s+\d+|Fig\.\s+\d+|Ilustración\s+\d+|Tabla\s+\d+|Cuadro\s+\d+)', full_text, re.IGNORECASE))
        citas = set(re.findall(r'\[\d+\]', full_text))
        
        # 1. Detectar páginas de índice de figuras (suelen estar al principio y tener muchas menciones)
        paginas_indice = set()
        for page_num in range(min(total_paginas, max(10, int(total_paginas * 0.25)))):
            page_text = doc[page_num].get_text("text").lower()
            # Si se mencionan 4 o más figuras distintas, asumimos que es el índice
            figuras_mencionadas = sum(1 for f in figuras if f.lower() in page_text)
            if figuras_mencionadas >= 4:
                paginas_indice.add(page_num)
                
        for fig in figuras:
            # Contar ignorando el índice
            conteo_real = 0
            for page_num in range(total_paginas):
                if page_num in paginas_indice:
                    continue
                conteo_real += doc[page_num].get_text("text").lower().count(fig.lower())
                
            if conteo_real <= 1:
                print(f"  [AVISO] '{fig}' parece no estar referenciada en el texto (fuera del índice).")
                for page_num in range(total_paginas):
                    page = doc[page_num]
                    rects = find_text_bounds(page, fig)
                    for rect in rects:
                        highlight = page.add_highlight_annot(rect)
                        highlight.set_colors(stroke=(1.0, 0.5, 0.0))
                        highlight.set_info(
                            title="Quirón",
                            subject="Falta Referencia",
                            content=f"Advertencia: '{fig}' aparece aquí pero parece no tener referencia cruzada en el texto principal."
                        )
                        highlight.update()
                        total_anotaciones_creadas += 1

        for cita in citas:
            conteo = full_text.count(cita)
            if conteo == 1:
                print(f"  [AVISO] La cita '{cita}' parece no estar referenciada en el texto.")
                for page_num in range(total_paginas):
                    page = doc[page_num]
                    rects = find_text_bounds(page, cita)
                    for rect in rects:
                        highlight = page.add_highlight_annot(rect)
                        highlight.set_colors(stroke=(1.0, 0.5, 0.0))
                        highlight.set_info(
                            title="Quirón",
                            subject="Cita sin Uso",
                            content=f"Advertencia: La cita '{cita}' aparece aquí pero parece no estar referenciada en el texto principal."
                        )
                        highlight.update()
                        total_anotaciones_creadas += 1

    txt_output_path = ""
    if do_dictamen:
        # --- REVISIÓN DE CONTENIDO (DICTAMEN ACADÉMICO) ---
        agent_display = f"{api_llm} ({api_model})" if mode == "api" else agent_name
        print(f"\n--- Iniciando revisión de contenido global usando {agent_display} ---")
        
        print("Enviando el documento completo para revisión de contenido (esto puede tardar unos momentos)...")
        if mode == "api":
            revision_contenido = run_content_review_api(full_text, api_llm, api_model)
        else:
            revision_contenido = run_content_review_cli(full_text, agent_name)
        
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
        print(f"\n--- Iniciando extracción de texto de la guía: {guide_path} ---")
        try:
            guide_doc = pymupdf.open(guide_path)
            guide_pages_text = []
            for i in range(len(guide_doc)):
                gt = guide_doc[i].get_text("text").strip()
                if gt:
                    guide_pages_text.append(gt)
            guide_full_text = "\n\n".join(guide_pages_text)
            guide_doc.close()
            
            agent_display = f"{api_llm} ({api_model})" if mode == "api" else agent_name
            print(f"--- Iniciando verificación de guía usando {agent_display} ---")
            
            if mode == "api":
                verificacion_guia = run_guide_review_api(full_text, guide_full_text, api_llm, api_model)
            else:
                verificacion_guia = run_guide_review_cli(full_text, guide_full_text, agent_name)
                
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
        
    corregir_reporte_pdf(input_path, output_path, args.agents, args.agent_cli, report_path=report_output_path, do_spelling=not args.skip_spelling, do_dictamen=not args.skip_dictamen, do_guide=bool(guide_path), guide_path=guide_path)

if __name__ == "__main__":
    main()
