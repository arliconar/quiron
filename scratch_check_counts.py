import glob, re, sys

sys.stdout.reconfigure(encoding='utf-8')
for test_file in glob.glob('scratch/test_val_*.py'):
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    # Find matching temp_page
    m = re.search(r"temp_page_(\d+)\.txt", content)
    if m:
        page_num = m.group(1)
        txt_path = f"temp_page_{page_num}.txt"
        try:
            with open(txt_path, 'r', encoding='utf-8') as tf:
                page_text = tf.read()
        except FileNotFoundError:
            continue
        
        # Parse errors from test_file
        # Look for "original": "..."
        origs = re.findall(r'"original":\s*"([^"]+)"', content)
        print(f"=== {test_file} (page {page_num}) ===")
        for orig in origs:
            cnt = page_text.count(orig)
            print(f"  '{orig}': count in text = {cnt}")
