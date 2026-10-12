import os, json

brain = os.path.expanduser('~/.gemini/antigravity-cli/brain')
f = os.path.join(brain, '67fabb3f-9371-4896-9a6c-156406899258', '.system_generated', 'logs', 'transcript_full.jsonl')
with open(f, 'r', encoding='utf-8') as fl:
    lines = fl.readlines()

for i, line in enumerate(lines):
    if 'temp_page_80.txt' in line:
        print(f"Line {i}:")
        for j in range(i, min(len(lines), i + 20)):
            o = json.loads(lines[j])
            print(f"  Step {j}: type={o.get('type')} content={bool(o.get('content'))} tool_calls={bool(o.get('tool_calls'))}")
            if o.get('content') and o.get('type') == 'PLANNER_RESPONSE':
                print(f"    RESPONSE: {o.get('content')[:300]}")
