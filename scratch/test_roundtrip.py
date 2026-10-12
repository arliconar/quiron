import json

from test_val_74 import errors

json_str = json.dumps(errors, ensure_ascii=False, indent=2)
data = json.loads(json_str)

assert len(data) == 17
for item in data:
    for k in ['original', 'corregido', 'tipo', 'explicacion']:
        assert k in item
        assert isinstance(item[k], str)

print("Validation perfectly passed!")
