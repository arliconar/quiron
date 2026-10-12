import os, json, glob

brain = os.path.expanduser('~/.gemini/antigravity-cli/brain')
for f in glob.glob(os.path.join(brain, '*', '.system_generated', 'logs', 'transcript.jsonl')):
    with open(f, 'r', encoding='utf-8') as fl:
        for line in fl:
            if 'USER_INPUT' in line and 'temp_page_' in line:
                obj = json.loads(line)
                print("USER PROMPT:", obj.get('content', '')[:120])
            if 'PLANNER_RESPONSE' in line:
                obj = json.loads(line)
                txt = obj.get('content', '')
                if txt and txt.strip().startswith('[') and 'original' in txt:
                    print("ASSISTANT RESPONSE:")
                    try:
                        parsed = json.loads(txt.strip())
                        print(json.dumps(parsed, indent=2, ensure_ascii=False))
                    except Exception as e:
                        print("Parse error:", e)
                        print(txt[:500])
                    print("="*60)
