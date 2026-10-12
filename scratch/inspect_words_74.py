with open('temp_page_74.txt', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()
for i, line in enumerate(lines, 1):
    print(f"Line {i}:")
    for word in line.split():
        non_ascii = [f"{c} (U+{ord(c):04X})" for c in word if ord(c) > 127]
        if non_ascii:
            print(f"  {word} -> {non_ascii}")
