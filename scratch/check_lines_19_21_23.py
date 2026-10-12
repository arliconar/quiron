with open('temp_page_74.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for lnum in [19, 21, 23]:
    line = lines[lnum-1].strip()
    print(f"Line {lnum}: length={len(line)}, spaces={line.count(' ')}")
    print(repr(line))
