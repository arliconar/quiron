import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('temp_page_21.txt', 'r', encoding='utf-8') as f:
    text = f.read()

errors = [
  {
    "original": "espaæol",
    "corregido": "español",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'ñ'; la palabra correcta es 'español'."
  },
  {
    "original": "antropomØtricos",
    "corregido": "antropométricos",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la grafía correcta es 'antropométricos', con tilde por ser palabra esdrújula."
  },
  {
    "original": "especícamente",
    "corregido": "específicamente",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; el término correcto es el adverbio 'específicamente'."
  },
  {
    "original": "diseæo",
    "corregido": "diseño",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'ñ'; debe escribirse 'diseño'."
  },
  {
    "original": "aæos",
    "corregido": "años",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'ñ'; la palabra correcta es 'años'."
  },
  {
    "original": "Segœn",
    "corregido": "Según",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la forma correcta es 'Según', con tilde en la 'u' por ser palabra aguda terminada en 'n'."
  },
  {
    "original": "antropomØtrico",
    "corregido": "antropométrico",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la forma correcta es 'antropométrico', con tilde en la 'e' por ser esdrújula."
  },
  {
    "original": "MØxico",
    "corregido": "México",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; el topónimo correcto es 'México', con tilde en la 'e' por ser palabra esdrújula."
  },
  {
    "original": "mØtrica",
    "corregido": "métrica",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la grafía correcta es 'métrica', con tilde en la 'e' por ser esdrújula."
  },
  {
    "original": "œnicamente",
    "corregido": "únicamente",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; debe escribirse 'únicamente', con tilde en la 'u'."
  },
  {
    "original": "mÆs",
    "corregido": "más",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; el adverbio comparativo correcto es 'más', con tilde diacrítica."
  },
  {
    "original": "gura",
    "corregido": "figura",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura inicial 'fi'; en este contexto corresponde al sustantivo 'figura'."
  }
]

valid_types = {'ortografía', 'gramática', 'acentuación', 'concordancia', 'puntuación', 'redacción'}

for e in errors:
    orig = e['original']
    corr = e['corregido']
    assert orig in text, f"Missing in text: {orig}"
    assert orig != corr, f"Original equals corregido: {orig}"
    assert e['tipo'] in valid_types, f"Invalid tipo: {e['tipo']}"
    print(f"OK: {orig} -> {corr} ({e['tipo']})")

print(f"\nAll {len(errors)} errors verified successfully!")
print(json.dumps(errors, ensure_ascii=False, indent=2))
