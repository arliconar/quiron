import re

with open('temp_page_77.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print("Length of text:", len(text))
lines = text.splitlines()

# 1. Non-standard characters
non_std = [c for c in text if c in 'æØÆ']
print("Corrupted characters found:", set(non_std))

# 2. Check tokens containing corrupted characters
for i, l in enumerate(lines, 1):
    for tok in re.findall(r'\S+', l):
        if any(c in 'æØÆ' for c in tok):
            print(f"Line {i} corrupted token: {tok}")

# 3. Check for words missing ligatures (fi, fl)
# Common patterns:
# perles -> perfiles
# identicadas -> identificadas
# con el n -> con el fin
# conguración -> configuración
# nal -> final
