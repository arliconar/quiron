import re

with open("temp_page_70.txt", "r", encoding="utf-8") as f:
    text = f.read()

our_originals = [
    "tØcnicas",
    "anÆlisis",
    "identicaron",
    "diseæo",
    "inuencia",
    "signicativa",
    "mœltiples",
    "desempeæo",
    "identicación",
    "conictos",
    "parÆmetros",
    "tØcnicos",
    "mecÆnicos",
    "mÆs",
    "denidos",
    "nalidad",
    "denir",
    "quØ",
    "especicar",
    "lograrÆ",
    "compondrÆn",
    "identican",
    "seæales",
    "especíca",
    "nal",
    "estØn",
    "AdemÆs"
]

# Mask all our originals in text and see if any non-standard chars remain
masked_text = text
for o in our_originals:
    masked_text = masked_text.replace(o, "---")

non_std = re.findall(r'[ØÆæœ]', masked_text)
print("Remaining non-standard characters after masking:", non_std)
