import os, json

brain_dir = r'C:\Users\artzm\.gemini\antigravity-cli\brain'
for cid in os.listdir(brain_dir):
    tpath = os.path.join(brain_dir, cid, '.system_generated', 'logs', 'transcript_full.jsonl')
    if not os.path.exists(tpath):
        tpath = os.path.join(brain_dir, cid, '.system_generated', 'logs', 'transcript.jsonl')
    if os.path.exists(tpath):
        with open(tpath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get('source') == 'MODEL' and not d.get('tool_calls'):
                        c = d.get('content', '')
                        if c.startswith('['):
                            errs = json.loads(c)
                            origs = [e['original'] for e in errs]
                            has_dups = len(origs) != len(set(origs))
                            print(f"CID {cid[:8]}: total {len(origs)}, unique {len(set(origs))}, dups={has_dups}")
                            if has_dups:
                                from collections import Counter
                                counts = Counter(origs)
                                print("   Dups:", [k for k, v in counts.items() if v > 1])
                except Exception as ex:
                    pass
