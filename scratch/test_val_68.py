import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
with open('temp_page_68.txt', 'r', encoding='utf-8') as f:
    text = f.read()

errors = [
  {
    "original": "especicaciones",
    "corregido": "especificaciones",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura tipográfica 'fi'; la grafía correcta es 'especificaciones'."
  },
  {
    "original": "servirÆn",
    "corregido": "servirán",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres donde 'Æ' sustituye a la vocal acentuada 'á'; debe escribirse 'servirán', con tilde por ser palabra aguda terminada en 'n'."
  },
  {
    "original": "diseæo",
    "corregido": "diseño",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'ñ'; la palabra correcta es 'diseño'."
  },
  {
    "original": "especicación",
    "corregido": "especificación",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura tipográfica 'fi'; el término correcto es 'especificación'."
  },
  {
    "original": "echas",
    "corregido": "flechas",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura inicial 'fl'; en este contexto corresponde al sustantivo 'flechas' (indicadores de dirección mediante flechas)."
  },
  {
    "original": "seæalan",
    "corregido": "señalan",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'ñ'; la forma verbal correcta es 'señalan'."
  },
  {
    "original": "nalidad",
    "corregido": "finalidad",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura inicial 'fi'; el término correcto es 'finalidad'."
  },
  {
    "original": "desempeæo",
    "corregido": "desempeño",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'ñ'; debe escribirse 'desempeño'."
  },
  {
    "original": "3⁄4QuØ?",
    "corregido": "¿Qué?",
    "tipo": "ortografía",
    "explicacion": "Fallo de codificación y omisión del signo de interrogación de apertura; la secuencia '3⁄4QuØ?' debe sustituirse por '¿Qué?', con tilde enfática."
  },
  {
    "original": "3⁄4Como?",
    "corregido": "¿Cómo?",
    "tipo": "ortografía",
    "explicacion": "Fallo de codificación, omisión del signo de interrogación de apertura y falta de tilde diacrítica enfática; debe escribirse '¿Cómo?'."
  },
  {
    "original": "DØbil",
    "corregido": "Débil",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres donde 'Ø' sustituye a la vocal acentuada 'é'; debe escribirse 'Débil', con tilde por ser palabra llana terminada en 'l'."
  },
  {
    "original": "tØcnica",
    "corregido": "técnica",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la vocal acentuada; debe escribirse 'técnica', con tilde en la 'e' por ser palabra esdrújula."
  },
  {
    "original": "mÆximo",
    "corregido": "máximo",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres donde 'Æ' sustituye a la vocal acentuada 'á'; debe escribirse 'máximo', con tilde por ser palabra esdrújula."
  },
  {
    "original": "mÆxima",
    "corregido": "máxima",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres donde 'Æ' sustituye a la vocal acentuada 'á'; debe escribirse 'máxima', con tilde por ser palabra esdrújula."
  },
  {
    "original": "cÆ-",
    "corregido": "cá-",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en el carácter 'Æ'; la partición silábica correcta es 'cá-' (de la palabra 'cáliper')."
  },
  {
    "original": "terapØutico",
    "corregido": "terapéutico",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; debe escribirse 'terapéutico', con tilde en la 'e' por ser palabra esdrújula."
  },
  {
    "original": "VelocidadangularmÆximasegura",
    "corregido": "Velocidad angular máxima segura",
    "tipo": "ortografía",
    "explicacion": "Error de segmentación léxica por ausencia de espacios intervocálicos y fallo de codificación en 'mÆxima'; debe escribirse 'Velocidad angular máxima segura'."
  },
  {
    "original": "energØtico",
    "corregido": "energético",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres donde 'Ø' sustituye a la vocal acentuada 'é'; debe escribirse 'energético', con tilde por ser palabra esdrújula."
  }
]

valid_types = {'ortografía', 'gramática', 'acentuación', 'concordancia', 'puntuación', 'redacción'}

for e in errors:
    orig = e['original']
    corr = e['corregido']
    assert orig in text, f"Missing in text: {orig!r}"
    assert orig != corr, f"Original equals corregido: {orig!r}"
    assert e['tipo'] in valid_types, f"Invalid tipo: {e['tipo']}"
    print(f"OK: {orig!r} -> {corr!r} ({e['tipo']})")

print(f"\nAll {len(errors)} errors verified successfully!")
out = json.dumps(errors, ensure_ascii=False, indent=2)
print("JSON Output length:", len(out))
