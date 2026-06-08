import json

d = json.load(open('data/hieu_de_database.json', encoding='utf-8'))
neifu = [x for x in d if '內府' in x.get('chu_han','') or '内府' in x.get('chu_han','')]
print(f'✓ Nội Phủ marks found: {len(neifu)}\n')
for x in neifu[:12]:
    print(f'  {x.get("chu_han", "?")} → {x.get("hien_thi_chinh", "?")}')

# Specifically check for 內府侍北
has_correct = any('侍北' in x.get('chu_han','') for x in neifu)
has_wrong = any('侍石' in x.get('chu_han','') for x in neifu)
print(f'\n✓ 內府侍北 exists: {has_correct}')
print(f'✓ 內府侍石 exists: {has_wrong}')
