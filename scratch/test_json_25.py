import json

errors = [
  {
    "original": "Pérdidas por Falta de Material",
    "corregido": "Pérdida por Falta de Material",
    "tipo": "concordancia",
    "explicacion": "Falta de concordancia en el número gramatical y de paralelismo sintáctico con el resto de las definiciones de la lista (PCP, PSJ, PEE, PFH), las cuales emplean el sustantivo en singular ('Pérdida'). Además, la sigla PFM corresponde a la forma singular."
  }
]

with open(r"C:\Users\artzm\OneDrive\Documentos\GitHub\quiron\temp_page_25.txt", "r", encoding="utf-8") as f:
    text = f.read()

for e in errors:
    assert e["original"] in text, f"Error: {e['original']} not found in text"
    print("Match OK:", e["original"])

out_json = json.dumps(errors, ensure_ascii=False, indent=2)
print("Output JSON:")
print(out_json)
