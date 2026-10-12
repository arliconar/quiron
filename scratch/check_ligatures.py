import re

with open('temp_page_70.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect words without 'f' where 'fi' or 'fl' might belong, e.g., 'identic', 'conic', 'signica', 'deni', etc.
words = re.findall(r'\b[a-zA-ZáéíóúÁÉÍÓÚñÑÆæØœ]+\b', text)
print("Unique words:", len(set(words)))

# Look for patterns like 'identic', 'deni', 'nal', 'conic', 'especic', 'inuencia'
for w in sorted(set(words)):
    for pattern in ['identi', 'deni', 'signi', 'conic', 'espec', 'inuen', 'nal', 'bene', 'dici']:
        if pattern in w.lower():
            print(f"Match '{pattern}': {w}")
