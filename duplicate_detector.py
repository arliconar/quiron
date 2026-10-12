import re
from collections import defaultdict

GENERIC_AUTHORS = {
    'desconocido', 'unknown', 'user', 'usuario', 'admin', 'administrador',
    'hp', 'dell', 'lenovo', 'asus', 'acer', 'pc', 'desktop', 'solidworks',
    'student', 'estudiante', 'n/a', ''
}

def normalize_name(name):
    """Normaliza un nombre quitando acentos y espacios adicionales para comparación."""
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r'[áàäâ]', 'a', name)
    name = re.sub(r'[éèëê]', 'e', name)
    name = re.sub(r'[íìïî]', 'i', name)
    name = re.sub(r'[óòöô]', 'o', name)
    name = re.sub(r'[úùüû]', 'u', name)
    name = re.sub(r'\s+', ' ', name)
    return name

def analyze_duplicates(sw_analysis_results):
    """
    Analiza una lista de resultados de piezas de SolidWorks para detectar:
    1. Autores de SolidWorks compartidos por múltiples alumnos (Posible Plagio/Copia).
    2. Incoincidencia entre el nombre del alumno en Classroom y el creador en SolidWorks.
    
    Devuelve: (processed_rows, statistics)
    """
    # Mapa: autor_normalizado -> set(estudiantes)
    author_to_students = defaultdict(set)
    last_author_to_students = defaultdict(set)
    
    for item in sw_analysis_results:
        student = item['student_name']
        sw_author = item.get('sw_author', 'Desconocido')
        sw_last_author = item.get('sw_last_author', 'Desconocido')
        
        norm_author = normalize_name(sw_author)
        norm_last_author = normalize_name(sw_last_author)
        
        if norm_author and norm_author not in GENERIC_AUTHORS:
            author_to_students[norm_author].add(student)
            
        if norm_last_author and norm_last_author not in GENERIC_AUTHORS:
            last_author_to_students[norm_last_author].add(student)

    processed_rows = []
    total_files = len(sw_analysis_results)
    students_set = set()
    suspicious_count = 0
    duplicate_authors_count = 0

    for item in sw_analysis_results:
        student = item['student_name']
        students_set.add(student)
        sw_author = item.get('sw_author', 'Desconocido')
        sw_last_author = item.get('sw_last_author', 'Desconocido')
        
        norm_author = normalize_name(sw_author)
        norm_last_author = normalize_name(sw_last_author)
        
        # Verificar si el autor aparece en entregas de MÁS DE UN alumno
        is_author_duplicated = (
            norm_author in author_to_students and 
            len(author_to_students[norm_author]) > 1
        )
        
        is_last_author_duplicated = (
            norm_last_author in last_author_to_students and 
            len(last_author_to_students[norm_last_author]) > 1
        )
        
        # Determinar nivel de alerta
        status = "NORMAL"
        alert_reason = []
        
        if is_author_duplicated:
            other_students = [s for s in author_to_students[norm_author] if s != student]
            alert_reason.append(f"Autor '{sw_author}' también usado por: {', '.join(other_students)}")
            status = "REPETIDO / SOSPECHOSO"
            
        if is_last_author_duplicated:
            other_students = [s for s in last_author_to_students[norm_last_author] if s != student]
            alert_reason.append(f"Último autor '{sw_last_author}' también en: {', '.join(other_students)}")
            status = "REPETIDO / SOSPECHOSO"

        if status == "REPETIDO / SOSPECHOSO":
            suspicious_count += 1
            
        # Verificar coincidencia directa entre nombre del estudiante y el autor de SW
        norm_student = normalize_name(student)
        matches_student = False
        if norm_author and norm_author not in GENERIC_AUTHORS:
            # Comprobar si parte del nombre del estudiante coincide con el autor
            student_tokens = set(norm_student.split())
            author_tokens = set(norm_author.split())
            if student_tokens.intersection(author_tokens):
                matches_student = True
        
        processed_rows.append({
            "status": status,
            "student_name": student,
            "student_email": item.get('student_email', ''),
            "file_name": item['file_name'],
            "sw_author": sw_author,
            "sw_last_author": sw_last_author,
            "create_time": item.get('create_time', 'N/A'),
            "last_saved_time": item.get('last_saved_time', 'N/A'),
            "is_duplicate": is_author_duplicated or is_last_author_duplicated,
            "matches_student": matches_student,
            "alert_details": " | ".join(alert_reason) if alert_reason else "Ninguna (Autor único o genérico)",
            "error": item.get('error')
        })

    # Contar cuántos nombres de autor fueron compartidos
    shared_author_names = {a for a, st in author_to_students.items() if len(st) > 1}
    duplicate_authors_count = len(shared_author_names)

    stats = {
        "total_files": total_files,
        "total_students": len(students_set),
        "suspicious_files": suspicious_count,
        "duplicate_author_names_count": duplicate_authors_count
    }
    
    return processed_rows, stats
