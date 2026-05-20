# Corrector de Reportes PDF con `gemini-cli`

Este proyecto es una herramienta profesional en Python que analiza archivos PDF (típicamente reportes de estadía o tesis académicas) en busca de errores ortográficos, gramaticales, de puntuación, acentuación y concordancia utilizando **`gemini-cli`**. 

El script genera de manera automática un PDF copia anotado con todos los errores resaltados y comentados mediante notas flotantes explicativas en español.

## Características Clave

* **Integración Nativa con `gemini-cli`:** El script localiza la instalación global de `gemini-cli` en npm y ejecuta directamente el bundle de JavaScript en Node.js. Esto evita limitaciones del intérprete de comandos `cmd.exe` o de la política de ejecución de PowerShell en Windows, logrando un procesamiento de páginas rápido y robusto.
* **Deduplicación Global Inteligente:** Para cumplir con la restricción de **no repetir errores**, el script lleva un registro global en memoria de todas las palabras o frases incorrectas encontradas. Si un error (por ejemplo, escribir *"desarollo"* o *"aplicacion"* sin acento) se repite a lo largo del documento, el script **solo lo marcará y comentará la primera vez**, evitando saturar visualmente el PDF copia.
* **Búsqueda Avanzada de Coordenadas:** Utiliza el motor de extracción de palabras de `pymupdf` para realizar coincidencias exactas por palabra completa, previniendo falsos positivos (por ejemplo, evitar resaltar la palabra *"sol"* dentro de *"soldado"*). Si el error es una frase (como *"la base de datos fueron actualizadas"*), realiza una búsqueda de concordancia de múltiples palabras.
* **Comentarios Académicos de Alta Calidad:** Cada error marcado en amarillo en el PDF incluye una ventana emergente de comentario detallado con:
  * El **Tipo de error** (ej. Ortografía, Acentuación, Gramática, Concordancia).
  * La **Corrección sugerida**.
  * Una **Explicación profesional** y clara de por qué es un error y cómo evitarlo.

## Requisitos Previos

1. **Python 3.10 o superior** (probado en Python 3.13).
2. **Node.js** y **`gemini-cli`** instalados globalmente:
   ```bash
   npm install -g @google/gemini-cli
   ```
   *Nota: Asegúrate de estar autenticado en la CLI ejecutando por primera vez el comando `gemini` en tu terminal.*

## Instalación

1. Te recomendamos encarecidamente **establecer este directorio como tu área de trabajo activa** en tu IDE para facilitar el acceso y la ejecución de comandos.
2. Abre tu terminal en este directorio e instala las dependencias de Python necesarias:
   ```bash
   pip install -r requirements.txt
   ```

## Archivos del Proyecto

El proyecto está estructurado con los siguientes archivos principales:

* [corrector.py](file:///C:/Users/artzm/.gemini/antigravity/scratch/corrector_ortografico/corrector.py): El código fuente principal que realiza el análisis, las llamadas a Gemini y las anotaciones en el PDF.
* [generar_test_pdf.py](file:///C:/Users/artzm/.gemini/antigravity/scratch/corrector_ortografico/generar_test_pdf.py): Un script auxiliar que genera un reporte de estadía ficticio (`reporte_prueba.pdf`) con errores ortográficos y gramaticales comunes e intencionales para probar el corrector de inmediato.
* [requirements.txt](file:///C:/Users/artzm/.gemini/antigravity/scratch/corrector_ortografico/requirements.txt): Las librerías de Python requeridas (`pymupdf` y `reportlab`).

## Cómo Probar el Proyecto de Inmediato

Sigue estos sencillos pasos para ver el corrector en acción:

### Paso 1: Generar el PDF de Prueba con Errores
Ejecuta el script auxiliar para crear un PDF ficticio que contiene errores ortográficos y de concordancia:
```bash
python generar_test_pdf.py
```
*Esto generará el archivo `reporte_prueba.pdf` en este directorio.*

### Paso 2: Ejecutar el Corrector Ortográfico
Ejecuta el script principal pasándole el PDF de entrada. Opcionalmente puedes definir la ruta de salida con `-o` o dejar que genere una automáticamente agregando `_corregido` al nombre original:
```bash
python corrector.py -i reporte_prueba.pdf -o reporte_prueba_corregido.pdf
```

Durante el proceso verás la salida detallada en tu consola:
```text
Abriendo PDF: C:\...\reporte_prueba.pdf
Total de páginas a procesar: 2

--- Procesando Página 1/2 ---
Enviando texto a Gemini...
Gemini reportó 6 posibles errores.
  [ERROR] 'Desarollo' -> 'Desarrollo' (ortografía)
  [ERROR] 'Implementacion' -> 'Implementación' (acentuación)
  ...

--- Procesando Página 2/2 ---
Enviando texto a Gemini...
Gemini reportó 20 posibles errores.
  [DEDUPLICADO] Se omitió el error 'desarollo' porque ya fue marcado anteriormente.
  [ERROR] 'aplicacion' -> 'aplicación' (acentuación)
  [ERROR] 'habian' -> 'había' (gramática)
  ...

Guardando PDF corregido en: C:\...\reporte_prueba_corregido.pdf...
==================================================
PROCESO TERMINADO EXITOSAMENTE
==================================================
```

### Paso 3: Visualizar los Resultados
Abre el archivo `reporte_prueba_corregido.pdf` con cualquier visor de PDF estándar (como Adobe Acrobat, Google Chrome, Microsoft Edge, etc.). Verás todas las palabras erróneas resaltadas en amarillo y, al pasar el cursor o hacer clic sobre ellas, se mostrará el panel con la corrección y explicación generada por Gemini.

## Uso del Script Principal

Puedes usar `corrector.py` con cualquier reporte de estadía o documento PDF propio:

```bash
python corrector.py -i <ruta_al_pdf_original> [-o <ruta_al_pdf_corregido>]
```

### Argumentos de Línea de Comandos:
* `-i`, `--input` (Obligatorio): Ruta del archivo PDF original a analizar.
* `-o`, `--output` (Opcional): Ruta donde se guardará el PDF copia comentado. Si no se proporciona, se guardará en la misma carpeta que el original, añadiendo `_corregido` al nombre del archivo.
