import re

with open('temp_page_74.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect tokens
tokens = re.findall(r'[^\s.,;:()]+', text)
print(f"Total tokens: {len(tokens)}")

# Find all tokens with characters not in standard ASCII letters/digits/standard Spanish (á, é, í, ó, ú, ü, ñ)
standard_spanish = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789áéíóúüñÁÉÍÓÚÜÑ-")

corrupt_tokens = []
for t in tokens:
    if not all(c in standard_spanish for c in t):
        corrupt_tokens.append(t)

print("Corrupt tokens:", set(corrupt_tokens))
