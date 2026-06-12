import json

errors = [
    {
        "original": "suponiendo que la temperatura de 90°C",
        "corregido": "suponiendo que la temperatura es de 90 °C",
        "tipo": "gramática",
        "explicacion": "La oración subordinada está incompleta (anacoluto) porque carece de un verbo conjugado (como 'es' o 'era') que determine la relación con la temperatura."
    },
    {
        "original": "se llegan a temperaturas",
        "corregido": "se llega a temperaturas",
        "tipo": "gramática",
        "explicacion": "El pronombre 'se' funciona como marca de impersonalidad al ir acompañado de la preposición 'a'. Por ello, el verbo debe conjugarse obligatoriamente en tercera persona del singular ('se llega')."
    },
    {
        "original": "de entre\r\n40°C a 85°C",
        "corregido": "de entre 40 °C y 85 °C",
        "tipo": "gramática",
        "explicacion": "Existe una correlación incorrecta de preposiciones. Cuando se emplea la estructura 'entre', los límites deben unirse mediante la conjunción 'y' ('entre 40 °C y 85 °C'), o bien emplear la fórmula 'de... a...' ('de 40 °C a 85 °C')."
    },
    {
        "original": "calibres mas pequeños",
        "corregido": "calibres más pequeños",
        "tipo": "acentuación",
        "explicacion": "La palabra 'más' requiere tilde diacrítica por funcionar como adverbio de cantidad, diferenciándose de la conjunción adversativa 'mas' (sinónimo de 'pero')."
    },
    {
        "original": "calibres mas pequeños como el 300 Kcmil a unos 90°C\r\nes capaz de soportar",
        "corregido": "calibres más pequeños como el de 300 kcmil a unos 90 °C son capaces de soportar",
        "tipo": "concordancia",
        "explicacion": "Falta de concordancia de número entre el sujeto plural ('calibres más pequeños') y el verbo con el adjetivo en singular ('es capaz'). Debe cambiarse a plural ('son capaces')."
    },
    {
        "original": "ademas",
        "corregido": "además",
        "tipo": "acentuación",
        "explicacion": "La palabra 'además' es aguda y termina en 's', por lo que debe llevar tilde en la última vocal."
    },
    {
        "original": "este disminuye",
        "corregido": "este disminuya",
        "tipo": "gramática",
        "explicacion": "El verbo debe conjugarse en modo subjuntivo ('disminuya') porque la oración está coordinada con 'se emplee' y depende de la construcción de valoración impersonal 'no es recomendable que'."
    },
    {
        "original": "Llegando así a la conclusión",
        "corregido": "Se llega así a la conclusión",
        "tipo": "gramática",
        "explicacion": "Uso incorrecto del gerundio al inicio de una oración independiente para expresar una consecuencia o posterioridad inmediata ('gerundio de posterioridad'). Debe sustituirse por una forma verbal conjugada."
    },
    {
        "original": "nominal. Donde es posible",
        "corregido": "nominal, donde es posible",
        "tipo": "puntuación",
        "explicacion": "Se divide de forma incorrecta una oración principal de su subordinada adjetiva ('donde...') mediante un punto y seguido. Debe emplearse una coma para mantener la continuidad sintáctica."
    },
    {
        "original": "articulo",
        "corregido": "artículo",
        "tipo": "acentuación",
        "explicacion": "La palabra 'artículo' es esdrújula, por lo que requiere tilde en la antepenúltima sílaba."
    },
    {
        "original": "tabla 250-122. Donde el calibre",
        "corregido": "tabla 250-122, donde el calibre",
        "tipo": "puntuación",
        "explicacion": "Se fragmenta la oración al separar la cláusula relativa subordinada mediante un punto y seguido. Se debe usar coma."
    },
    {
        "original": "debe de\r\nexceder",
        "corregido": "debe exceder",
        "tipo": "gramática",
        "explicacion": "La perífrasis 'deber de + infinitivo' denota probabilidad o suposición, mientras que 'deber + infinitivo' expresa obligación. Al tratarse de una normativa (NOM), lo correcto es 'debe exceder'."
    },
    {
        "original": "limite",
        "corregido": "límite",
        "tipo": "acentuación",
        "explicacion": "En este contexto, la palabra funciona como sustantivo común esdrújulo ('límite'), requiriendo tilde en la primera sílaba."
    },
    {
        "original": "conexión.\r\nEl mismo manual",
        "corregido": "conexión, el mismo manual",
        "tipo": "puntuación",
        "explicacion": "Se coloca un punto y seguido que separa de forma incorrecta una prótasis concesiva ('Si bien...') de su apódosis principal ('el mismo manual...'), rompiendo la estructura de la oración compuesta. Deben unirse mediante una coma."
    },
    {
        "original": "(base) ,",
        "corregido": "(base),",
        "tipo": "puntuación",
        "explicacion": "Se ha insertado un espacio en blanco innecesario antes de la coma de puntuación."
    }
]

out_path = r"C:\Users\artzm\OneDrive\Documentos\GitHub\quiron\temp_errores_26.json"
# Ensure the JSON is written with UTF-8 encoding
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(errors, f, ensure_ascii=False, indent=2)

print("JSON file generated successfully at", out_path)
