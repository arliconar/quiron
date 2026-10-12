import re

with open('temp_page_77.txt', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()
for i, line in enumerate(lines, 1):
    print(f"L{i}: {line}")
