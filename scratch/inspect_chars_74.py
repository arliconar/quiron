import unicodedata

with open('temp_page_74.txt', 'r', encoding='utf-8') as f:
    text = f.read()

chars = set(text)
for c in sorted(chars):
    if ord(c) > 127:
        print(f"{repr(c)} U+{ord(c):04X} ({unicodedata.name(c, 'UNKNOWN')})")
