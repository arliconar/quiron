import glob, re

for f in glob.glob('scratch/test_val_*.py'):
    c = open(f, encoding='utf-8').read()
    origs = re.findall(r'"original":\s*"([^"]+)"', c)
    print(f, f"total: {len(origs)}, unique: {len(set(origs))}")
