import os, glob

brain = os.path.expanduser('~/.gemini/antigravity-cli/brain')
for t in glob.glob(os.path.join(brain, '*', '.system_generated', 'logs', 'transcript_full.jsonl')):
    with open(t, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'temp_page_7' in content and '"original"' in content:
        lines = [l.strip() for l in content.splitlines() if '"original"' in l or '"corregido"' in l]
        if lines:
            print(t)
            for l in lines[:10]:
                print('  ', l.encode('ascii', 'backslashreplace').decode('ascii'))
            print('='*50)
