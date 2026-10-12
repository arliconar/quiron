import glob, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

brain = os.path.expanduser('~/.gemini/antigravity-cli/brain')
conversations = sorted(glob.glob(os.path.join(brain, '*', '.system_generated', 'logs', 'transcript_full.jsonl')), key=os.path.getmtime, reverse=True)

count = 0
for f in conversations:
    with open(f, 'r', encoding='utf-8') as fl:
        for line in fl:
            if 'PLANNER_RESPONSE' in line:
                try:
                    obj = json.loads(line)
                    txt = obj.get('content', '')
                    if txt and txt.strip().startswith('[') and '"original"' in txt:
                        print('=== FROM:', f)
                        print(txt.strip())
                        count += 1
                        break
                except Exception:
                    pass
    if count >= 3:
        break
