with open("temp_page_70.txt", "r", encoding="utf-8") as f:
    text = f.read()

import re

# 1. Search for corrupted characters in text
corrupted_tokens = set(re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]*[ØÆæœ][a-zA-ZáéíóúÁÉÍÓÚñÑ]*', text))
print("Corrupted tokens with Ø, Æ, æ, œ:")
for tok in sorted(corrupted_tokens):
    print(" ", tok)

# 2. Search for words missing 'fi' or 'fl'
# Let's inspect all words against Spanish wordlist or common patterns
print("\nChecking all lines:")
for line_idx, line in enumerate(text.splitlines(), 1):
    print(f"Line {line_idx}: {line}")
