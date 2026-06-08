import sys

file_path = r'd:\HieuDe_AI\chinese-ocr-app\index.html'
js_path = r'd:\HieuDe_AI\chinese-ocr-app\floating-lines.js'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

new_lines = []
for line in lines:
    if '<script src="floating-lines.js"></script>' in line:
        new_lines.append('<script>\n')
        new_lines.append(js_content)
        new_lines.append('\n</script>\n')
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Inlined floating-lines.js into index.html!')
