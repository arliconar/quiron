import pymupdf

doc = pymupdf.open("Memoria_Tecnica.pdf")
print("Total pages:", len(doc))

# Let's find which page has this text
with open("temp_page_70.txt", "r", encoding="utf-8") as f:
    target_sample = "despliegue de la función de calidad"

for page_num in range(len(doc)):
    txt = doc[page_num].get_text()
    if target_sample in txt or "Tabla 12" in txt:
        print(f"Found in page index {page_num} (1-based: {page_num+1})")
        print("Raw text snippet:")
        print(txt[:500])
        break
