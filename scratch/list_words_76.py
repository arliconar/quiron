with open("temp_page_76.txt", "r", encoding="utf-8") as f:
    text = f.read()

import re

# Split by words
words = re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑüÜÆæØøœŒ]+', text)
print("Unique words:", sorted(set(words)))
