import os
import io
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Permisos requeridos para Classroom y Drive
SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.students.readonly',
    'https://www.googleapis.com/auth/classroom.rosters.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

class ClassroomManager:
    def __init__(self, credentials_path=CREDENTIALS_FILE, token_path=TOKEN_FILE):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = None
        self.classroom_service = None
        self.drive_service = None
        self.user_email = None

    def authenticate(self, force_reauth=False):
        """
        Autentica automáticamente al usuario usando token.json existente.
        Si caducó, lo refresca. Si no existe o expiró la sesión de actualización,
        abre el navegador para que el profesor inicie sesión.
        """
        self.creds = None

        if os.path.exists(self.token_path) and not force_reauth:
            try:
                self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                print(f"Error al cargar {self.token_path}: {e}")

        # Si no hay credenciales válidas, renovar o pedir inicio de sesión
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    print(f"No se pudo refrescar el token: {e}. Re-iniciando sesión...")
                    self.creds = None

            if not self.creds:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"No se encontró el archivo de credenciales de Google '{self.credentials_path}'. "
                        "Por favor obtén 'credentials.json' desde la consola de Google Cloud."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)

            # Guardar el token para la siguiente ejecución
            with open(self.token_path, 'w') as token_file:
                token_file.write(self.creds.to_json())

        # Construir servicios de API
        self.classroom_service = build('classroom', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        
        # Obtener email del usuario logueado
        try:
            profile = self.classroom_service.userProfiles().get(userId='me').execute()
            self.user_email = profile.get('emailAddress', 'Usuario Autenticado')
        except Exception:
            self.user_email = "Usuario Autenticado"

        return self.user_email

    def is_authenticated(self):
        """Verifica si existe token válido o refrescable."""
        if not os.path.exists(self.token_path):
            return False
        try:
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            return creds and (creds.valid or creds.refresh_token is not None)
        except Exception:
            return False

    def list_courses(self):
        """Obtiene la lista de clases donde el usuario es profesor o alumno."""
        if not self.classroom_service:
            self.authenticate()

        courses = []
        page_token = None
        while True:
            response = self.classroom_service.courses().list(
                pageSize=50,
                courseStates=['ACTIVE'],
                pageToken=page_token
            ).execute()

            for course in response.get('courses', []):
                courses.append({
                    'id': course['id'],
                    'name': course.get('name', 'Sin nombre'),
                    'section': course.get('section', '')
                })

            page_token = response.get('nextPageToken')
            if not page_token:
                break
                
        return courses

    def list_assignments(self, course_id):
        """Obtiene la lista de tareas (courseWork) para una clase dada."""
        if not self.classroom_service:
            self.authenticate()

        assignments = []
        page_token = None
        while True:
            response = self.classroom_service.courses().courseWork().list(
                courseId=course_id,
                pageSize=50,
                pageToken=page_token
            ).execute()

            for work in response.get('courseWork', []):
                assignments.append({
                    'id': work['id'],
                    'title': work.get('title', 'Sin título'),
                    'creationTime': work.get('creationTime', '')
                })

            page_token = response.get('nextPageToken')
            if not page_token:
                break

        return assignments

    def get_students_map(self, course_id):
        """Crea un mapa de ID de usuario -> Nombre del estudiante."""
        students_map = {}
        try:
            request = self.classroom_service.courses().students().list(courseId=course_id)
            while request is not None:
                response = request.execute()
                for student in response.get('students', []):
                    user_id = student.get('userId')
                    profile = student.get('profile', {})
                    name = profile.get('name', {}).get('fullName', 'Desconocido')
                    email = profile.get('emailAddress', '')
                    students_map[user_id] = {
                        'name': name,
                        'email': email
                    }
                request = self.classroom_service.courses().students().list_next(previous_request=request, previous_response=response)
        except Exception as e:
            print(f"Advertencia al listar estudiantes: {e}")
        return students_map

    def download_submissions_files(self, course_id, coursework_id, dest_dir, progress_callback=None):
        """
        Descarga todos los archivos adjuntos (SolidWorks o ZIP) de las entregas de una tarea.
        Returns: lista de tuplas/dicts: [{'student_name': ..., 'student_email': ..., 'file_name': ..., 'local_path': ...}]
        """
        if not self.classroom_service or not self.drive_service:
            self.authenticate()

        students = self.get_students_map(course_id)
        downloaded_items = []

        # Obtener entregas
        submissions_res = self.classroom_service.courses().courseWork().studentSubmissions().list(
            courseId=course_id,
            courseWorkId=coursework_id
        ).execute()

        submissions = submissions_res.get('studentSubmissions', [])
        total_subs = len(submissions)

        for idx, sub in enumerate(submissions):
            user_id = sub.get('userId')
            student_info = students.get(user_id, {'name': f'Usuario {user_id}', 'email': ''})
            student_name = student_info['name']
            student_email = student_info['email']

            if progress_callback:
                progress_callback(f"Procesando entrega {idx+1}/{total_subs}: {student_name}", (idx + 1) / max(total_subs, 1))

            assignment_sub = sub.get('assignmentSubmission', {})
            attachments = assignment_sub.get('attachments', [])

            for att in attachments:
                if 'driveFile' in att:
                    drive_file = att['driveFile']
                    file_id = drive_file.get('id')
                    title = drive_file.get('title', 'adjunto')
                    
                    # Filtrar por extensiones relevantes
                    lower_title = title.lower()
                    valid_exts = ('.sldprt', '.sldasm', '.slddrw', '.zip', '.rar')
                    if any(lower_title.endswith(ext) for ext in valid_exts):
                        # Crear subcarpeta limpia por alumno
                        student_clean = "".join([c if c.isalnum() or c in (' ', '_', '-') else '_' for c in student_name])
                        student_dir = os.path.join(dest_dir, student_clean)
                        os.makedirs(student_dir, exist_ok=True)

                        local_path = os.path.join(student_dir, title)
                        
                        # Descargar desde Drive API
                        try:
                            request = self.drive_service.files().get_media(fileId=file_id)
                            with io.FileIO(local_path, 'wb') as fh:
                                downloader = MediaIoBaseDownload(fh, request)
                                done = False
                                while not done:
                                    status, done = downloader.next_chunk()

                            downloaded_items.append({
                                'student_name': student_name,
                                'student_email': student_email,
                                'file_name': title,
                                'local_path': local_path
                            })
                        except Exception as download_err:
                            print(f"Error descargando {title} de {student_name}: {download_err}")

        return downloaded_items
