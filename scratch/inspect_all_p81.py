import re

with open('temp_page_81.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect all words line by line
lines = text.splitlines()

for i, line in enumerate(lines, 1):
    print(f"--- Line {i} ---")
    words = line.split()
    for w in words:
        clean_w = re.sub(r'^[^\w]+|[^\w]+$', '', w)
        # Check if clean_w exists in Spanish or if adding 'fi' or 'fl' makes a valid word
        # Also check characters Æ, Ø, æ
        print(f"  {w:30} -> clean: {clean_w}")
