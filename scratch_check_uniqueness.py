import glob, re, sys

sys.stdout.reconfigure(encoding='utf-8')
for f in glob.glob('scratch/test_val_*.py') + glob.glob('test_val_*.py'):
    with open(f, 'r', encoding='utf-8') as fp:
        c = fp.read()
    origs = re.findall(r'"original":\s*"([^"]+)"', c)
    lowers = [o.lower() for o in origs]
    dups = [l for l in lowers if lowers.count(l) > 1]
    if dups:
        print(f'{f} has duplicate lowers:', set(dups))
    else:
        print(f'{f}: all unique lowers ({len(origs)} items)')
