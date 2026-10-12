import json

with open(r'C:\Users\artzm\.gemini\antigravity-cli\brain\daeae741-827e-4db3-a837-76ac17068907\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        if d.get('source') == 'MODEL' and not d.get('tool_calls') and d.get('content', '').startswith('['):
            errs = json.loads(d['content'])
            for e in errs:
                print(f"{e['original']} -> {e['corregido']} [{e['tipo']}]")
