import re
import unicodedata

with open("temp_page_76.txt", "r", encoding="utf-8") as f:
    text = f.read()

lines = text.splitlines()

allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789áéíóúÁÉÍÓÚñÑüÜ.,;:()-\"'/ \t\n")
non_std = set()
for c in text:
    if c not in allowed:
        non_std.add(c)

print("Non-standard characters:", [f"{c} (U+{ord(c):04X}, {unicodedata.name(c, 'UNKNOWN')})" for c in non_std])

print("\nLines and words containing non-standard chars:")
for i, line in enumerate(lines, 1):
    for token in re.findall(r'\S+', line):
        if any(c in non_std for c in token):
            print(f"L{i}: {token}")

for i, line in enumerate(lines, 1):
    print(f"{i}: {line}")

print("\n--- TOKEN CHECK ---")
import spacy
# check if spacy or enchant or any spell checker is available
for i, line in enumerate(lines, 1):
    tokens = re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑüÜÆæ]+|[0-9]+|[^\s\w]', line)
    print(f"Line {i} tokens:", tokens)

