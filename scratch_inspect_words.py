import sys
import re
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
with open('temp_page_68.txt', 'r', encoding='utf-8') as f:
    text = f.read()

words = re.findall(r'[^\s.,;:()↑↓·=°/]+', text)
print("Word counts:")
counts = Counter(words)
for w, c in counts.items():
    if c > 1:
        print(f"  {w}: {c}")
