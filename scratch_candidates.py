import glob, re, sys

sys.stdout.reconfigure(encoding='utf-8')
for f in glob.glob('scratch/test_*.py') + glob.glob('test_*.py'):
    with open(f, 'r', encoding='utf-8') as fp:
        c = fp.read()
        print(f'=== {f} ===')
        for m in re.finditer(r'{\s*"original":\s*"([^"]+)",\s*"corregido":\s*"([^"]+)",\s*"tipo":\s*"([^"]+)"', c):
            print(f'  {m.group(1)} -> {m.group(2)} ({m.group(3)})')
