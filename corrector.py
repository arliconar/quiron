import os
import sys
import json
import re
import argparse
import subprocess
import pymupdf

# Configuración del Prompt del Sistema para Gemini
SYSTEM_PROMPT = (
    "Eres un corrector de estilo y ortografía profesional para textos académicos y reportes de estadías en español. "
    "Tu tarea es analizar el texto proporcionado en busca de errores ortográficos, gramaticales, de acentuación, "
    "concordancia, puntuación o de redacción.\n\n"
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
    "5. No corrijas nombres propios de herramientas o tecnologías conocidas (ej. Python, PostgreSQL, Docker, etc.).\n\n"
    "Texto a analizar:"
)

DOCTOR_PROMPT = (
    "Eres un Doctor en Mecatrónica evaluando una memoria de estadía (reporte de prácticas profesionales). "
    "Tu tarea es revisar rigurosamente el contenido técnico, la estructura, la coherencia y la profundidad del trabajo. "
    "Crea un reporte con correcciones y sugerencias acerca del contenido. "
    "Para cada observación, incluye (si es posible): el capítulo, la hoja/página, el texto original al que haces referencia, y la mejora sugerida. "
    "Tu respuesta debe estar en texto claro, estructurado y profesional."
)

def get_gemini_js_path() -> str:
    """
    Intenta localizar el archivo de bundle de JavaScript de gemini-cli ('gemini.js')
    de la instalación global de npm.
    Devuelve la ruta absoluta si existe, o levanta una excepción.
    """
    # 1. Ruta absoluta conocida en el sistema del usuario
    known_path = r"C:\Users\artzm\AppData\Roaming\npm\node_modules\@google\gemini-cli\bundle\gemini.js"
    if os.path.exists(known_path):
        return known_path
        
    # 2. Intentar usar la variable de entorno APPDATA
    appdata = os.environ.get("APPDATA")
    if appdata:
        appdata_path = os.path.join(appdata, "npm", "node_modules", "@google", "gemini-cli", "bundle", "gemini.js")
        if os.path.exists(appdata_path):
            return appdata_path
            
    # 3. Fallback: buscar en directorios comunes
    raise FileNotFoundError(
        "No se pudo encontrar el bundle de 'gemini.js' en la instalación global de npm. "
        "Asegúrate de haber ejecutado 'npm install -g @google/gemini-cli'."
    )

def run_gemini_cli(text_content: str) -> list:
    """
    Ejecuta gemini-cli pasándole el texto por stdin y el prompt como parámetro -p.
    Devuelve la lista de errores encontrados.
    """
    try:
        js_path = get_gemini_js_path()
        
        # Invocar directamente el ejecutable 'node' con el script de gemini
        cmd = [
            "node",
            js_path,
            "-p",
            SYSTEM_PROMPT,
            "-o",
            "json"
        ]
        
        # Ejecutar el comando con el contenido de la página como stdin
        result = subprocess.run(
            cmd,
            input=text_content,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        if result.returncode != 0:
            print(f"Error al ejecutar gemini-cli:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}", file=sys.stderr)
            return []
            
        # Parsear la salida del CLI
        cli_output = json.loads(result.stdout)
        response_text = cli_output.get("response", "").strip()
        
        if not response_text:
            return []
            
        # Limpiar bloques de código markdown si los hay (e.g. ```json ... ```)
        cleaned_json = response_text
        if "```" in cleaned_json:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned_json)
            if match:
                cleaned_json = match.group(1).strip()
                
        # Parsear la respuesta del modelo (los errores)
        try:
            errors = json.loads(cleaned_json)
            if isinstance(errors, list):
                return errors
            elif isinstance(errors, dict):
                # Si devolvió un objeto único en vez de un array, lo envolvemos
                return [errors]
        except json.JSONDecodeError:
            # Reintentar limpieza agresiva de caracteres no válidos si es necesario
            # A veces el modelo añade texto fuera de las llaves
            match = re.search(r'(\[\s*\{[\s\S]*\}\s*\])', cleaned_json)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            print(f"No se pudo parsear el JSON de la respuesta del modelo: {response_text}", file=sys.stderr)
            
    except Exception as e:
        print(f"Ocurrió un error inesperado al invocar gemini-cli: {e}", file=sys.stderr)
        
    return []

def run_gemini_content_review(text_content: str) -> str:
    """
    Ejecuta gemini-cli para una revisión de contenido técnico usando el DOCTOR_PROMPT.
    """
    try:
        js_path = get_gemini_js_path()
        
        cmd = [
            "node",
            js_path,
            "-p",
            DOCTOR_PROMPT,
            "-o",
            "json"
        ]
        
        result = subprocess.run(
            cmd,
            input=text_content,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        if result.returncode != 0:
            print(f"Error al ejecutar gemini-cli (revisión de contenido):\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}", file=sys.stderr)
            return ""
            
        cli_output = json.loads(result.stdout)
        return cli_output.get("response", "").strip()
            
    except Exception as e:
        print(f"Ocurrió un error inesperado al invocar gemini-cli para revisión: {e}", file=sys.stderr)
        
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

def corregir_reporte_pdf(input_path: str, output_path: str):
    """
    Abre el PDF de entrada, analiza errores por página usando gemini-cli (sin repetir errores globales),
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
    
    # Iterar sobre cada página
    for page_num in range(total_paginas):
        page = doc[page_num]
        print(f"\n--- Procesando Página {page_num + 1}/{total_paginas} ---")
        
        # Extraer el texto de la página
        text_content = page.get_text("text").strip()
        if not text_content:
            print("Página vacía o sin texto extraíble. Omitiendo.")
            continue
            
        print("Enviando texto a Gemini...")
        errors = run_gemini_cli(text_content)
        
        if not errors:
            print("No se encontraron errores en esta página (o la respuesta fue vacía).")
            continue
            
        print(f"Gemini reportó {len(errors)} posibles errores.")
        
        # Procesar cada error reportado
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
                print(f"  [DEDUPLICADO] Se omitió el error '{original}' porque ya fue marcado anteriormente.")
                continue
                
            seen_errors_global.add(err_key)
            total_errores_detectados += 1
            
            # Buscar la ubicación del error en la página
            rects = find_text_bounds(page, original)
            
            if not rects:
                # Si falló, intentar buscar sin case-sensitivity o con ligeras modificaciones
                # (a veces Gemini devuelve la palabra con su corrección o sin un acento del original)
                print(f"  [AVISO] No se encontraron coordenadas exactas para la palabra '{original}' en el PDF.")
                continue
                
            # Crear anotaciones de resaltado con comentario
            print(f"  [ERROR] '{original}' -> '{corregido}' ({tipo})")
            
            # Resaltar todas las instancias encontradas en esta página
            for rect in rects:
                highlight = page.add_highlight_annot(rect)
                
                # Configurar el popup/comentario de la anotación
                contenido_comentario = (
                    f"Tipo: {tipo.capitalize()}\n"
                    f"Corrección sugerida: {corregido}\n"
                    f"Detalle: {explicacion}"
                )
                
                # Actualizar metadatos del comentario usando set_info de PyMuPDF
                highlight.set_info(
                    title="Quirón",
                    subject=f"Error de {tipo}",
                    content=contenido_comentario
                )
                highlight.set_colors(stroke=(1.0, 0.8, 0.0))  # Color amarillo brillante para resaltar
                highlight.update()
                total_anotaciones_creadas += 1
                
    # --- REVISIÓN DE CONTENIDO (DOCTOR EN MECATRÓNICA) ---
    print("\n--- Iniciando revisión de contenido técnico (Doctor en Mecatrónica) ---")
    all_text_with_pages = []
    for page_num in range(total_paginas):
        text_content = doc[page_num].get_text("text").strip()
        if text_content:
            all_text_with_pages.append(f"--- PÁGINA {page_num + 1} ---\n{text_content}")
            
    full_text = "\n\n".join(all_text_with_pages)
    
    print("Enviando el documento completo para revisión de contenido (esto puede tardar unos momentos)...")
    revision_contenido = run_gemini_content_review(full_text)
    
    txt_output_path = ""
    if revision_contenido:
        base, _ = os.path.splitext(input_path)
        txt_output_path = f"{base}_revision_contenido.txt"
        with open(txt_output_path, "w", encoding="utf-8") as f:
            f.write(revision_contenido)
        print(f"Revisión de contenido guardada exitosamente en: {txt_output_path}")
    else:
        print("No se pudo obtener la revisión de contenido.")

    # Guardar el PDF copia con las anotaciones
    print(f"\nGuardando PDF corregido en: {output_path}...")
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
        description="Corrige errores ortográficos y gramaticales en reportes PDF usando gemini-cli y crea un PDF copia anotado."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Ruta al archivo PDF original (reporte de estadía)."
    )
    parser.add_argument(
        "-o", "--output",
        help="Ruta donde se guardará el PDF corregido. Por defecto se añade '_corregido' al nombre original."
    )
    
    args = parser.parse_args()
    
    input_path = os.path.abspath(args.input)
    
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        # Generar nombre automático
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_corregido{ext}"
        
    corregir_reporte_pdf(input_path, output_path)

if __name__ == "__main__":
    main()
