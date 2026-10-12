import json
import sys

with open("temp_page_78.txt", "r", encoding="utf-8") as f:
    text = f.read()

errors = [
  {
    "original": "identicó",
    "corregido": "identificó",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura interna 'fi'; la forma verbal correcta es 'identificó', con tilde en la 'o' por ser palabra aguda terminada en vocal."
  },
  {
    "original": "denir",
    "corregido": "definir",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; el término correcto es el verbo en infinitivo 'definir'."
  },
  {
    "original": "renamiento",
    "corregido": "refinamiento",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura interna 'fi'; el término correcto es el sustantivo 'refinamiento'."
  },
  {
    "original": "diseæo",
    "corregido": "diseño",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'ñ'; la palabra correcta es 'diseño'."
  },
  {
    "original": "cÆliper",
    "corregido": "cáliper",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en el carácter 'Æ'; la adaptación correcta es 'cáliper', con tilde en la 'a' por ser palabra llana terminada en 'r'."
  },
  {
    "original": "nalidad",
    "corregido": "finalidad",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura inicial 'fi'; el término correcto es el sustantivo 'finalidad'."
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
out = json.dumps(errors, ensure_ascii=False, indent=2)
print("JSON Output:\n", out)
