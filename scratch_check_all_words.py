import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
with open('temp_page_68.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# All tokens
tokens = re.findall(r'\S+', text)
print(f"Total tokens: {len(tokens)}")

# Check each line
lines = text.splitlines()
for i, line in enumerate(lines, 1):
    words = re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑÆæØœ]+', line)
    print(f"Line {i:02d}: {words}")
