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
    "5. No corrijas nombres propios de herramientas o tecnologías conocidas (ej. Python, PostgreSQL, Docker, etc.).\n"
)

DOCTOR_PROMPT = (
    "Eres un Doctor en Mecatrónica evaluando una memoria de estadía (reporte de prácticas profesionales). "
    "Tu tarea es revisar rigurosamente el contenido técnico, la estructura, la coherencia y la profundidad del trabajo. "
    "Crea un reporte con correcciones y sugerencias acerca del contenido. "
    "Para cada observación, incluye (si es posible): el capítulo, la hoja/página, el texto original al que haces referencia, y la mejora sugerida. "
    "Tu respuesta debe estar en texto claro, estructurado y profesional."
)

def run_antigravity_cli(text_content: str, page_num: int) -> list:
    """
    Ejecuta agy instruyéndole a leer un archivo de texto y generar un JSON con los errores.
    Devuelve la lista de errores encontrados.
    """
    try:
        text_file_path = os.path.abspath(f"temp_page_{page_num}.txt")
        json_file_path = os.path.abspath(f"temp_errores_{page_num}.json")
        
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(text_content)
            
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"El texto a analizar se encuentra en el archivo: {text_file_path}\n"
            f"Lee ese archivo y GUARDA tu respuesta JSON en el archivo: {json_file_path}\n"
            "Asegúrate de crear el archivo JSON en esa ruta y que su contenido sea únicamente el arreglo JSON."
        )
        
        cmd = ["agy", "-p", prompt]
        
        # Ejecutar el comando
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        # Parsear el archivo JSON generado
        if not os.path.exists(json_file_path):
            print(f"  [ERROR] Antigravity no generó el archivo {json_file_path}", file=sys.stderr)
            return []
            
        with open(json_file_path, "r", encoding="utf-8") as f:
            response_text = f.read().strip()
            
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
            if os.path.exists(json_file_path): os.remove(json_file_path)
        except Exception as e:
            print(f"  [AVISO] No se pudieron borrar archivos temporales: {e}", file=sys.stderr)
            
        if isinstance(parsed, list): return parsed
        if isinstance(parsed, dict): return [parsed]
        
    except Exception as e:
        print(f"Ocurrió un error inesperado al invocar antigravity-cli: {e}", file=sys.stderr)
        
    return []

def run_antigravity_content_review(text_content: str) -> str:
    """
    Ejecuta agy para una revisión de contenido técnico usando el DOCTOR_PROMPT,
    leyendo y escribiendo en archivos para evitar problemas de longitud.
    """
    try:
        text_file_path = os.path.abspath("temp_revision_contenido.txt")
        output_file_path = os.path.abspath("temp_revision_resultado.txt")
        
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(text_content)
            
        prompt = (
            f"{DOCTOR_PROMPT}\n\n"
            f"El documento completo se encuentra en el archivo: {text_file_path}\n"
            f"Lee ese archivo, realiza tu revisión y GUARDA el reporte resultante en el archivo: {output_file_path}\n"
            "Asegúrate de escribir el resultado en esa ruta."
        )
        
        cmd = ["agy", "-p", prompt]
        
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        revision = ""
        if os.path.exists(output_file_path):
            with open(output_file_path, "r", encoding="utf-8") as f:
                revision = f.read().strip()
                
        # Limpiar archivos temporales
        try:
            if os.path.exists(text_file_path): os.remove(text_file_path)
            if os.path.exists(output_file_path): os.remove(output_file_path)
        except Exception as e:
            print(f"  [AVISO] No se pudieron borrar archivos temporales: {e}", file=sys.stderr)
            
        return revision
            
    except Exception as e:
        print(f"Ocurrió un error inesperado al invocar antigravity-cli para revisión: {e}", file=sys.stderr)
        
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
    Abre el PDF de entrada, analiza errores por página usando antigravity-cli (sin repetir errores globales),
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
            
        print("Enviando texto a Antigravity...")
        errors = run_antigravity_cli(text_content, page_num + 1)
        
        if not errors:
            print("No se encontraron errores en esta página (o la respuesta fue vacía).")
            continue
            
        print(f"Antigravity reportó {len(errors)} posibles errores.")
        
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
                # (a veces Antigravity devuelve la palabra con su corrección o sin un acento del original)
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
    revision_contenido = run_antigravity_content_review(full_text)
    
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
    
    args = parser.parse_args()
    
    input_path = os.path.abspath(args.input)
    
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        # Sobrescribir el archivo original
        output_path = input_path
        
    corregir_reporte_pdf(input_path, output_path)

if __name__ == "__main__":
    main()
