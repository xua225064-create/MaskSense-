import db
import json

marks = db.fetch_all_marks()
data = []
for m in marks:
    data.append({
        'id': m['id'],
        'chu_han': m.get('chu_han'),
        'trieu_dai': m.get('trieu_dai'),
        'hoang_de': m.get('hoang_de'),
        'nien_dai': m.get('nien_dai')
    })

with open('marks_dump.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
