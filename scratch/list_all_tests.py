import glob, re, json

for f in sorted(glob.glob('scratch/test_*.py')):
    with open(f, 'r', encoding='utf-8') as fp:
        c = fp.read()
    m = re.search(r'errors\s*=\s*(\[[\s\S]*?\])\s*\n\s*(?:valid_types|out)', c)
    if m:
        try:
            errs = json.loads(m.group(1))
            print(f'=== {f} ({len(errs)} errors) ===')
            for e in errs:
                print(f"  {repr(e['original'])} -> {repr(e['corregido'])} [{e['tipo']}]")
        except Exception as ex:
            print(f'{f}: {ex}')
