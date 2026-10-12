import os, json

brain_dir = r'C:\Users\artzm\.gemini\antigravity-cli\brain'
for cid in ['028e88d6-99a7-46a0-ac9a-dbc8dbe9e546', '47a40dc0-2194-460b-ad7a-e4eb00d0168d']:
    tpath = os.path.join(brain_dir, cid, '.system_generated', 'logs', 'transcript_full.jsonl')
    if not os.path.exists(tpath):
        tpath = os.path.join(brain_dir, cid, '.system_generated', 'logs', 'transcript.jsonl')
    if os.path.exists(tpath):
        with open(tpath, 'r', encoding='utf-8') as f:
            for line in f:
                d = json.loads(line)
                if d.get('source') == 'MODEL' and not d.get('tool_calls'):
                    c = d.get('content', '')
                    if c.startswith('['):
                        print(f"=== {cid} ===")
                        print(c)
