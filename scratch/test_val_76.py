import json
import sys

with open("temp_page_76.txt", "r", encoding="utf-8") as f:
    text = f.read()

errors = [
  {
    "original": "diseæo",
    "corregido": "diseño",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'ñ'; la palabra correcta es 'diseño'."
  },
  {
    "original": "mÆs",
    "corregido": "más",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; el adverbio comparativo correcto es 'más', con tilde diacrítica."
  },
  {
    "original": "uido",
    "corregido": "fluido",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura inicial 'fl'; en este contexto corresponde al adjetivo 'fluido'."
  },
  {
    "original": "identicó",
    "corregido": "identificó",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura interna 'fi'; la forma verbal correcta es 'identificó', con tilde en la 'o' por ser palabra aguda terminada en vocal."
  },
  {
    "original": "AdemÆs",
    "corregido": "Además",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la grafía correcta es 'Además', con tilde en la 'a' por ser palabra aguda terminada en 's'."
  },
  {
    "original": "dicultaría",
    "corregido": "dificultaría",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura interna 'fi'; la forma verbal correcta es 'dificultaría', con tilde en la 'i' por presentar hiato acentual."
  },
  {
    "original": "jación",
    "corregido": "fijación",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura inicial 'fi'; el término correcto es el sustantivo 'fijación', con tilde en la 'o' por ser palabra aguda terminada en 'n'."
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
print("JSON Output length:", len(out))
