import json

with open("temp_page_75.txt", "r", encoding="utf-8") as f:
    text = f.read()

errors = [
  {
    "original": "especícos",
    "corregido": "específicos",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura interna 'fi'; la forma correcta es 'específicos'."
  },
  {
    "original": "exión-extensión",
    "corregido": "flexión-extensión",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por omisión de la ligadura 'fl'; la forma compuesta correcta es 'flexión-extensión'."
  },
  {
    "original": "antropomØtricos",
    "corregido": "antropométricos",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la grafía correcta es 'antropométricos', con tilde en la 'e' por ser palabra esdrújula."
  },
  {
    "original": "inuir",
    "corregido": "influir",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fl'; el verbo correcto es 'influir'."
  },
  {
    "original": "TambiØn",
    "corregido": "También",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la palabra correcta es 'También', con tilde en la 'e' por ser aguda terminada en 'n'."
  },
  {
    "original": "denieron",
    "corregido": "definieron",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; la conjugación verbal correcta es 'definieron'."
  },
  {
    "original": "antropomórcas",
    "corregido": "antropomórficas",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; el adjetivo correcto es 'antropomórficas'."
  },
  {
    "original": "bÆsicos",
    "corregido": "básicos",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; debe escribirse 'básicos', con tilde en la 'a' por ser palabra esdrújula."
  },
  {
    "original": "elØctrica",
    "corregido": "eléctrica",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la grafía correcta es 'eléctrica', con tilde en la primera 'e' por ser esdrújula."
  },
  {
    "original": "especicaciones",
    "corregido": "especificaciones",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; el sustantivo correcto es 'especificaciones'."
  },
  {
    "original": "diseæo",
    "corregido": "diseño",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'ñ'; la palabra correcta es 'diseño'."
  },
  {
    "original": "perl",
    "corregido": "perfil",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; en este contexto técnico corresponde a 'perfil' ('perfil PTR')."
  },
  {
    "original": "Ængulos",
    "corregido": "ángulos",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la forma correcta es 'ángulos', con tilde en la 'a' por ser palabra esdrújula."
  },
  {
    "original": "mecÆnico",
    "corregido": "mecánico",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; debe escribirse 'mecánico', con tilde en la 'a' por ser palabra esdrújula."
  },
  {
    "original": "nœmero",
    "corregido": "número",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la palabra correcta es 'número', con tilde en la 'u' por ser palabra esdrújula."
  },
  {
    "original": "diseæada",
    "corregido": "diseñada",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'ñ'; la forma correcta es 'diseñada'."
  },
  {
    "original": "n",
    "corregido": "fin",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura inicial 'fi'; en la locución 'con el fin de' debe escribirse 'fin'."
  },
  {
    "original": "antropomØtricas",
    "corregido": "antropométricas",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la forma correcta es 'antropométricas', con tilde en la 'e' por ser palabra esdrújula."
  },
  {
    "original": "aœn",
    "corregido": "aún",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; el adverbio correcto es 'aún', con tilde diacrítica por hiato."
  },
  {
    "original": "especíco",
    "corregido": "específico",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; el adjetivo correcto es 'específico'."
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
