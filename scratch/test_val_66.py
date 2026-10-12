import json

with open("temp_page_66.txt", "r", encoding="utf-8") as f:
    text = f.read()

errors = [
  {
    "original": "tØcnicos",
    "corregido": "técnicos",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la grafía correcta es 'técnicos', con tilde en la 'e' por ser palabra esdrújula."
  },
  {
    "original": "denió",
    "corregido": "definió",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; la forma verbal correcta es 'definió', con tilde en la 'o' por ser aguda terminada en vocal."
  },
  {
    "original": "terapØutico",
    "corregido": "terapéutico",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; debe escribirse 'terapéutico', con tilde en la 'e' por ser palabra esdrújula."
  },
  {
    "original": "œtil",
    "corregido": "útil",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la grafía correcta es 'útil', con tilde en la 'u' por ser palabra llana terminada en 'l'."
  },
  {
    "original": "dinÆmica",
    "corregido": "dinámica",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; debe escribirse 'dinámica', con tilde en la 'a' por ser palabra esdrújula."
  },
  {
    "original": "cÆliper",
    "corregido": "cáliper",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la adaptación correcta es 'cáliper', con tilde en la 'a' por ser palabra llana terminada en 'r'."
  },
  {
    "original": "ltrar",
    "corregido": "filtrar",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura inicial 'fi'; el término correcto es el verbo 'filtrar'."
  },
  {
    "original": "perles",
    "corregido": "perfiles",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura interna 'fi'; en este contexto corresponde al sustantivo 'perfiles'."
  },
  {
    "original": "mÆs",
    "corregido": "más",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; el adverbio comparativo correcto es 'más', con tilde diacrítica."
  },
  {
    "original": "vØase",
    "corregido": "véase",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la forma verbal correcta es 'véase', con tilde en la 'e' por ser palabra esdrújula."
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
