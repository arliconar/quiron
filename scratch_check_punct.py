import re

with open('temp_page_68.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Check for suspicious spaces before punctuation
print("Spaces before punctuation:")
for m in re.finditer(r'\s+[,.;:?!)]', text):
    print(repr(m.group(0)), "at pos", m.start(), repr(text[max(0, m.start()-10):m.end()+10]))

# Check for missing space after punctuation
print("\nMissing space after punctuation:")
for m in re.finditer(r'[,.;:?!][a-zA-ZáéíóúÁÉÍÓÚñÑ]', text):
    print(repr(m.group(0)), "at pos", m.start(), repr(text[max(0, m.start()-10):m.end()+10]))

# Check for double spaces
print("\nDouble spaces:")
for m in re.finditer(r'  +', text):
    print(repr(m.group(0)), "at pos", m.start(), repr(text[max(0, m.start()-10):m.end()+10]))
