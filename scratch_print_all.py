import sys

sys.stdout.reconfigure(encoding='utf-8')
with open('temp_page_68.txt', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()
for idx, line in enumerate(lines, 1):
    print(f"L{idx:02d}: {line}")
