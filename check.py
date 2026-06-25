# -*- coding: utf-8 -*-
import json

file_path = r"C:\Users\artzm\OneDrive\Documentos\GitHub\quiron\temp_page_12.txt"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

errors = [
    u"“VFD”\u037e",
    u"”Variador de Frecuencia o Velocidad”",
    u"utilidad lo que",
    u"dando como resultado",
    u"suave. (Figura 2.4)"
]

for err in errors:
    print(repr(err), "in text:", err in text)
