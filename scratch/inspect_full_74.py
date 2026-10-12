with open('temp_page_74.txt', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()
for idx, l in enumerate(lines, 1):
    print(f"L{idx:02d}: {l}")
