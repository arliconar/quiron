import re
import unicodedata

with open('temp_page_70.txt', 'r', encoding='utf-8') as f:
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

print("\nChecking joined words or suspicious words:")
for i, line in enumerate(lines, 1):
    if len(line) > 60 and ' ' not in line:
        print(f"L{i} [no spaces]: {line}")
    elif any(len(word) > 25 for word in line.split()):
        print(f"L{i} [very long word]: {[w for w in line.split() if len(w) > 25]}")
