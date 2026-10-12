import json

with open('temp_page_74.txt', 'r', encoding='utf-8') as f:
    text = f.read()

errors = [
  {
    "original": "sistemÆtica",
    "corregido": "sistemática",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la vocal acentuada; debe escribirse 'sistemática', con tilde en la 'a' por ser palabra esdrújula."
  },
  {
    "original": "diseæo",
    "corregido": "diseño",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'æ'; la grafía correcta en español es 'diseño'."
  },
  {
    "original": "calica",
    "corregido": "califica",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; la forma verbal correcta es 'califica'."
  },
  {
    "original": "segœn",
    "corregido": "según",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la vocal acentuada; la palabra correcta es 'según', con tilde en la 'u' por ser aguda terminada en 'n'."
  },
  {
    "original": "desempeæo",
    "corregido": "desempeño",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la letra 'æ'; la palabra correcta es 'desempeño'."
  },
  {
    "original": "identicar",
    "corregido": "identificar",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura interna 'fi'; la forma verbal correcta es 'identificar'."
  },
  {
    "original": "mÆs",
    "corregido": "más",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; el adverbio comparativo correcto es 'más', con tilde diacrítica."
  },
  {
    "original": "eciencia",
    "corregido": "eficiencia",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; el término correcto es el sustantivo 'eficiencia'."
  },
  {
    "original": "anÆlisis",
    "corregido": "análisis",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres en la vocal acentuada; debe escribirse 'análisis', con tilde en la primera 'a' por ser palabra esdrújula."
  },
  {
    "original": "comprometersignicativamenteelcosto.Enparticular,seobservaquelasalternativas",
    "corregido": "comprometer significativamente el costo. En particular, se observa que las alternativas",
    "tipo": "redacción",
    "explicacion": "Falta de espacios de separación entre palabras y signos de puntuación, además de la omisión de la ligadura 'fi' en 'significativamente'; debe escribirse 'comprometer significativamente el costo. En particular, se observa que las alternativas'."
  },
  {
    "original": "energØtica",
    "corregido": "energética",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la grafía correcta es 'energética', con tilde en la 'e' por ser palabra esdrújula."
  },
  {
    "original": "precisiónycalidad,loquerespaldasuintegracióndentrodeldiseæoglobaldelsistema.",
    "corregido": "precisión y calidad, lo que respalda su integración dentro del diseño global del sistema.",
    "tipo": "redacción",
    "explicacion": "Falta de espacios de separación entre palabras y tras la coma, además del carácter corrupto 'æ' en 'diseño'; debe escribirse 'precisión y calidad, lo que respalda su integración dentro del diseño global del sistema.'."
  },
  {
    "original": "aunqueviables,presentandesventajasenaspectoscríticos,loquejusticósudescarte.",
    "corregido": "aunque viables, presentan desventajas en aspectos críticos, lo que justificó su descarte.",
    "tipo": "redacción",
    "explicacion": "Falta de espacios de separación entre palabras y tras las comas, además de la omisión de la ligadura 'fi' en 'justificó'; debe escribirse 'aunque viables, presentan desventajas en aspectos críticos, lo que justificó su descarte.'."
  },
  {
    "original": "estØn",
    "corregido": "estén",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la forma verbal correcta es 'estén', con tilde en la 'e' por ser palabra aguda terminada en 'n'."
  },
  {
    "original": "tØcnicos",
    "corregido": "técnicos",
    "tipo": "ortografía",
    "explicacion": "Error de codificación de caracteres; la grafía correcta es 'técnicos', con tilde en la 'e' por ser palabra esdrújula."
  },
  {
    "original": "cuanticables",
    "corregido": "cuantificables",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; el adjetivo correcto es 'cuantificables'."
  },
  {
    "original": "ecaz",
    "corregido": "eficaz",
    "tipo": "ortografía",
    "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; el término correcto es el adjetivo 'eficaz'."
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
