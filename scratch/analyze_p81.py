import re, unicodedata

with open('temp_page_81.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print("Length of text:", len(text))
print("Lines count:", len(text.splitlines()))

# Find non-ascii characters
non_ascii = set()
for c in text:
    if ord(c) > 127:
        non_ascii.add((c, f"U+{ord(c):04X}", unicodedata.name(c, 'UNKNOWN')))

print("Non-ASCII chars found:")
for item in non_ascii:
    print(" ", item)

# Let's inspect tokens
tokens = re.findall(r'\b\w+\b', text)
print(f"Total tokens: {len(tokens)}")

# Words with non-ascii
weird_words = []
for line in text.splitlines():
    for w in line.split():
        if any(ord(c) > 127 for c in w):
            weird_words.append(w)

print("Words with non-ASCII or corrupt chars:")
for w in weird_words:
    print(" ", w)
