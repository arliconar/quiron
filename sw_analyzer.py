import os
import zipfile
import olefile

SW_EXTENSIONS = ('.sldprt', '.sldasm', '.slddrw')

def clean_prop_string(val):
    """
    Limpia y decodifica un valor de propiedad devuelto por olefile.
    """
    if val is None:
        return "Desconocido"
    if isinstance(val, bytes):
        try:
            val = val.decode('utf-8')
        except UnicodeDecodeError:
            try:
                val = val.decode('cp1252', errors='ignore')
            except Exception:
                val = val.decode('latin-1', errors='ignore')
    if isinstance(val, str):
        cleaned = val.strip('\x00').strip()
        return cleaned if cleaned else "Desconocido"
    return str(val)

def extract_sw_metadata(file_path):
    """
    Extrae los metadatos internos de SolidWorks (Autor y Último Autor en guardar)
    desde el flujo SummaryInformation del archivo OLE (.sldprt, .sldasm, .slddrw).
    
    Devuelve un diccionario con los metadatos extraídos.
    """
    if not os.path.exists(file_path):
        return {"error": f"El archivo no existe: {file_path}"}
        
    if not olefile.isOleFile(file_path):
        return {"error": "No es un archivo OLE válido de SolidWorks"}

    try:
        with olefile.OleFileIO(file_path) as ole:
            meta = ole.getmetadata()
            
            author = clean_prop_string(meta.author)
            last_saved_by = clean_prop_string(meta.last_saved_by)
            
            create_time = str(meta.create_time) if meta.create_time else "Desconocido"
            last_saved_time = str(meta.last_saved_time) if meta.last_saved_time else "Desconocido"
            
            return {
                "author": author,
                "last_saved_by": last_saved_by,
                "create_time": create_time,
                "last_saved_time": last_saved_time,
                "error": None
            }
    except Exception as e:
        return {
            "author": "Desconocido",
            "last_saved_by": "Desconocido",
            "create_time": "Desconocido",
            "last_saved_time": "Desconocido",
            "error": f"Error al leer OLE: {str(e)}"
        }

def analyze_file_submission(local_file_path, student_name, student_email, extract_dir):
    """
    Procesa un archivo entregado por un alumno. Si es un archivo de SolidWorks, lo analiza directamente.
    Si es un archivo .zip, lo descomprime y analiza todos los archivos SolidWorks encontrados dentro.
    
    Devuelve una lista de diccionarios con el análisis de cada pieza encontrada.
    """
    results = []
    file_name = os.path.basename(local_file_path)
    lower_name = file_name.lower()
    
    # Caso 1: Archivo ejecutable directo de SolidWorks
    if lower_name.endswith(SW_EXTENSIONS):
        meta = extract_sw_metadata(local_file_path)
        results.append({
            "student_name": student_name,
            "student_email": student_email,
            "file_name": file_name,
            "file_path": local_file_path,
            "sw_author": meta["author"],
            "sw_last_author": meta["last_saved_by"],
            "create_time": meta["create_time"],
            "last_saved_time": meta["last_saved_time"],
            "is_from_zip": False,
            "zip_parent": None,
            "error": meta["error"]
        })
        
    # Caso 2: Archivo ZIP que contiene piezas
    elif lower_name.endswith('.zip'):
        try:
            zip_subfolder = os.path.join(extract_dir, f"unzipped_{os.path.splitext(file_name)[0]}")
            os.makedirs(zip_subfolder, exist_ok=True)
            
            with zipfile.ZipFile(local_file_path, 'r') as zip_ref:
                zip_ref.extractall(zip_subfolder)
                
            # Recorrer subcarpeta descomprimida
            for root, _, files in os.walk(zip_subfolder):
                for f in files:
                    if f.lower().endswith(SW_EXTENSIONS):
                        extracted_path = os.path.join(root, f)
                        rel_path = os.path.relpath(extracted_path, zip_subfolder)
                        meta = extract_sw_metadata(extracted_path)
                        results.append({
                            "student_name": student_name,
                            "student_email": student_email,
                            "file_name": f"{file_name} -> {rel_path}",
                            "file_path": extracted_path,
                            "sw_author": meta["author"],
                            "sw_last_author": meta["last_saved_by"],
                            "create_time": meta["create_time"],
                            "last_saved_time": meta["last_saved_time"],
                            "is_from_zip": True,
                            "zip_parent": file_name,
                            "error": meta["error"]
                        })
        except Exception as e:
            results.append({
                "student_name": student_name,
                "student_email": student_email,
                "file_name": file_name,
                "file_path": local_file_path,
                "sw_author": "N/A",
                "sw_last_author": "N/A",
                "create_time": "N/A",
                "last_saved_time": "N/A",
                "is_from_zip": False,
                "zip_parent": None,
                "error": f"Error al extraer ZIP: {str(e)}"
            })
            
    return results
