import json

with open("temp_page_70.txt", "r", encoding="utf-8") as f:
    text = f.read()

candidate_errors = [
    {
        "original": "tØcnicas",
        "corregido": "técnicas",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres en la vocal acentuada; debe escribirse 'técnicas', con tilde en la 'e' por ser palabra esdrújula."
    },
    {
        "original": "anÆlisis",
        "corregido": "análisis",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres; la grafía correcta es 'análisis', con tilde en la primera 'a' por ser palabra esdrújula."
    },
    {
        "original": "identicaron",
        "corregido": "identificaron",
        "tipo": "ortografía",
        "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; la forma verbal correcta es 'identificaron'."
    },
    {
        "original": "diseæo",
        "corregido": "diseño",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres en la letra 'ñ'; la palabra correcta es 'diseño'."
    },
    {
        "original": "desempeæo",
        "corregido": "desempeño",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres en la letra 'ñ'; debe escribirse 'desempeño'."
    },
    {
        "original": "identicación",
        "corregido": "identificación",
        "tipo": "ortografía",
        "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; el sustantivo correcto es 'identificación', con tilde en la 'o'."
    },
    {
        "original": "conictos",
        "corregido": "conflictos",
        "tipo": "ortografía",
        "explicacion": "Palabra incompleta por omisión de la ligadura 'fl'; el término correcto es 'conflictos'."
    },
    {
        "original": "parÆmetros",
        "corregido": "parámetros",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres; debe escribirse 'parámetros', con tilde en la segunda 'a' por ser palabra esdrújula."
    },
    {
        "original": "tØcnicos",
        "corregido": "técnicos",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres; debe escribirse 'técnicos', con tilde en la 'e' por ser palabra esdrújula."
    },
    {
        "original": "mecÆnicos",
        "corregido": "mecánicos",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres; debe escribirse 'mecánicos', con tilde en la 'a' por ser esdrújula."
    },
    {
        "original": "mÆs",
        "corregido": "más",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres; el adverbio comparativo o de cantidad debe escribirse 'más', con tilde diacrítica."
    },
    {
        "original": "denidos",
        "corregido": "definidos",
        "tipo": "ortografía",
        "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; el adjetivo o participio correcto es 'definidos'."
    },
    {
        "original": "nalidad",
        "corregido": "finalidad",
        "tipo": "ortografía",
        "explicacion": "Palabra incompleta por omisión de la ligadura inicial 'fi'; el término correcto es 'finalidad'."
    },
    {
        "original": "denir",
        "corregido": "definir",
        "tipo": "ortografía",
        "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; la forma verbal correcta es 'definir'."
    },
    {
        "original": "quØ",
        "corregido": "qué",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres; debe escribirse 'qué' con tilde diacrítica por cumplir función interrogativa indirecta."
    },
    {
        "original": "especicar",
        "corregido": "especificar",
        "tipo": "ortografía",
        "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; el infinitivo correcto es 'especificar'."
    },
    {
        "original": "lograrÆ",
        "corregido": "logrará",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres en la desinencia verbal de futuro; debe escribirse 'logrará', con tilde por ser aguda terminada en vocal."
    },
    {
        "original": "compondrÆn",
        "corregido": "compondrán",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres en la desinencia verbal de futuro; debe escribirse 'compondrán', con tilde por ser aguda terminada en 'n'."
    },
    {
        "original": "identican",
        "corregido": "identifican",
        "tipo": "ortografía",
        "explicacion": "Palabra incompleta por pérdida de la ligadura 'fi'; la forma verbal correcta es 'identifican'."
    },
    {
        "original": "seæales",
        "corregido": "señales",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres en la letra 'ñ'; el sustantivo correcto es 'señales'."
    },
    {
        "original": "especíca",
        "corregido": "específica",
        "tipo": "ortografía",
        "explicacion": "Palabra incompleta por omisión de la ligadura 'fi'; el adjetivo femenino correcto es 'específica', con tilde en la antepenúltima sílaba por ser esdrújula."
    },
    {
        "original": "nal",
        "corregido": "final",
        "tipo": "ortografía",
        "explicacion": "Palabra incompleta por pérdida de la ligadura inicial 'fi'; la palabra correcta es 'final'."
    },
    {
        "original": "estØn",
        "corregido": "estén",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres; la forma del verbo estar en presente de subjuntivo debe escribirse 'estén', con tilde por ser aguda terminada en 'n'."
    },
    {
        "original": "AdemÆs",
        "corregido": "Además",
        "tipo": "ortografía",
        "explicacion": "Error de codificación de caracteres; debe escribirse 'Además', con tilde en la 'a' por ser palabra aguda terminada en 's'."
    }
]

valid_types = {'ortografía', 'gramática', 'acentuación', 'concordancia', 'puntuación', 'redacción'}

for e in candidate_errors:
    orig = e['original']
    corr = e['corregido']
    assert orig in text, f"Missing in text: {orig}"
    assert orig != corr, f"Original equals corregido: {orig}"
    assert e['tipo'] in valid_types, f"Invalid tipo: {e['tipo']}"
    print(f"OK: {orig} -> {corr} ({e['tipo']})")

print(f"\nAll {len(candidate_errors)} errors validated successfully!")
