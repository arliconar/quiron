import unicodedata, re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('temp_page_78.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print('=== FILE CONTENT ===')
for i, line in enumerate(text.splitlines(), 1):
    print(f'{i}: {line}')

print('\n=== NON-ASCII CHARACTERS ===')
for c in sorted(set(text)):
    if ord(c) > 127:
        print(f'{repr(c)} (U+{ord(c):04X}, {unicodedata.name(c, "UNKNOWN")})')

print('\n=== WORDS WITH NON-ASCII CHARS ===')
for match in re.finditer(r'\S+', text):
    token = match.group(0)
    if any(ord(c) > 127 for c in token):
        print(token)

print('\n=== ALL WORDS/TOKENS ===')
tokens = re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑüÜÆæØøœŒ]+', text)
print(tokens)
