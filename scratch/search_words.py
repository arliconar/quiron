import glob, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

brain = os.path.expanduser('~/.gemini/antigravity-cli/brain')
for f in glob.glob(os.path.join(brain, '*', '.system_generated', 'logs', 'transcript_full.jsonl')):
    with open(f, 'r', encoding='utf-8') as fl:
        content = fl.read()
        for word in ['nalidad', 'renamiento', 'denir', 'cÆliper']:
            if f'"original": "{word}"' in content:
                print(f'Found "{word}" in {f}')
                # find the json entry
                for m in content.split('"original": "' + word + '"')[1:2]:
                    snippet = m[:300]
                    print('   Snippet:', snippet.replace('\n', ' '))
