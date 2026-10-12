with open('temp_page_74.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines, 1):
    line_clean = line.strip()
    print(f"--- Line {idx} ---")
    print(line_clean)
