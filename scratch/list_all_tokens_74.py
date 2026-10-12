with open('temp_page_74.txt', 'r', encoding='utf-8') as f:
    text = f.read()

import re
# Clean tokens
tokens = re.findall(r'[^\s.,;:()]+', text)
unique_tokens = sorted(set(tokens), key=lambda s: s.lower())

for t in unique_tokens:
    print(t)
