import sys

sys.stdout.reconfigure(encoding='utf-8')
with open('temp_page_68.txt', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('cÆ-')
print("Snippet around cÆ-:")
print(repr(text[idx-10:idx+30]))
