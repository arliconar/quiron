import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('temp_page_15.txt', 'r', encoding='utf-8') as f:
    text = f.read()

errors = [
  {
    "original": "mecÆnica",
    "corregido": "mecánica",
    "tipo": "ortografía",
    "explicacion": "Error tipográfico por carácter mal codificado; debe escribirse 'mecánica' con tilde en la 'a' por ser palabra esdrújula."
  },
  {
    "original": "recongurable",
    "corregido": "reconfigurable",
    "tipo": "ortografía",
    "explicacion": "Error léxico y tipográfico; el término técnico correcto es 'reconfigurable'."
  },
  {
    "original": "anÆlisis",
    "corregido": "análisis",
    "tipo": "ortografía",
    "explicacion": "Error por carácter mal codificado; la palabra correcta es 'análisis' con tilde en la primera 'a' por ser esdrújula."
  },
  {
    "original": "nito",
    "corregido": "finito",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; en este contexto técnico (asociado a la sigla FEA) corresponde a 'finito' ('elemento finito')."
  },
  {
    "original": "permitirÆ",
    "corregido": "permitirá",
    "tipo": "ortografía",
    "explicacion": "Error de codificación en la forma verbal; debe escribirse 'permitirá' con tilde en la 'a' final por ser aguda terminada en vocal."
  },
  {
    "original": "siológico",
    "corregido": "fisiológico",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura inicial 'fi'; la grafía correcta es 'fisiológico'."
  },
  {
    "original": "exión-extensión",
    "corregido": "flexión-extensión",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por omisión de la ligadura 'fl'; la forma compuesta correcta es 'flexión-extensión'."
  },
  {
    "original": "soportarÆ",
    "corregido": "soportará",
    "tipo": "ortografía",
    "explicacion": "Error por carácter mal codificado; la conjugación verbal correcta es 'soportará' con tilde en la 'a'."
  },
  {
    "original": "podrÆ",
    "corregido": "podrá",
    "tipo": "ortografía",
    "explicacion": "Error por carácter mal codificado; debe escribirse 'podrá' con tilde en la 'a' por ser palabra aguda terminada en vocal."
  },
  {
    "original": "tØcnica",
    "corregido": "técnica",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la palabra correcta es 'técnica' con tilde en la 'e' por ser esdrújula."
  }
]

valid_types = {'ortografía', 'gramática', 'acentuación', 'concordancia', 'puntuación', 'redacción'}

for e in errors:
    orig = e['original']
    corr = e['corregido']
    assert orig in text, f"Missing in text: {orig}"
    assert orig != corr, f"Original equals corregido: {orig}"
    assert e['tipo'] in valid_types, f"Invalid tipo: {e['tipo']}"

print("All 10 errors validated successfully!")
print(json.dumps(errors, ensure_ascii=False, indent=2))
