with open('temp_page_70.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(4, 10):
    print(f"Line {i+1}: {repr(lines[i])}")

print("---")
for i in range(16, 21):
    print(f"Line {i+1}: {repr(lines[i])}")
