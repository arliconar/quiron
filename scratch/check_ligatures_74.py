import re

with open('temp_page_74.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Split by whitespace
words = [w.strip('.,;:()[]"\'') for w in text.split()]
words = [w for w in words if w]

# Look for words that might have lost 'fi' or 'fl' or other letters
for w in set(words):
    # Check if inserting 'fi' or 'fl' makes a valid word
    # or print words with uncommon substrings
    if any(pattern in w for pattern in ['ica', 'icie', 'ici', 'caz']):
        print(f"Check: {w}")
