import unicodedata

with open('temp_page_80.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    print(f"--- Line {i} ---")
    print(line.strip())
    non_ascii = [(c, f"U+{ord(c):04X}", unicodedata.name(c, 'UNKNOWN')) for c in line if ord(c) > 127]
    if non_ascii:
        print("  Non-ASCII:", non_ascii)
