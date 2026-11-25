import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for name in ('domains','municipalities','municipal_categories'):
    records=json.loads((root/'registry'/'seeds'/f'{name}.json').read_text()); print(name,len(records))
print('Verified source records: 0; bulk acquisition: 0; publication withheld')
