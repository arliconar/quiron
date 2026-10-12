import glob
import re

for fpath in sorted(glob.glob("temp_page_*.txt")):
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    long_no_space = re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑÆæØœ,]{35,}', content)
    if long_no_space:
        print(f"{fpath}: {len(long_no_space)} occurrences")
        for occ in long_no_space[:3]:
            print(f"   {occ[:60]}...")
