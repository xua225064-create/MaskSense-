import re

def run():
    with open('index.html', 'r', encoding='utf-8') as f:
        text = f.read()

    match = re.search(r'var viToEn = (\{.*?\});\s*var enToVi', text, re.DOTALL)
    if not match:
        return
        
    dict_str = match.group(1)
    items = re.findall(r"'([^']+)':\s*'([^']+)'", dict_str)
    items.sort(key=lambda x: len(x[0]), reverse=True)
    
    for vi, en in items:
        # replace > vi < with >en< ignoring surrounding whitespace
        pattern = r'>\s*' + re.escape(vi) + r'\s*<'
        text = re.sub(pattern, f'>{en}<', text)

    # Some things are still in string literals in JS, like "Lỗi" -> "Error"
    # The previous script caught most, but let's do a more robust one for JS alerts
    for vi, en in items:
        # alert/toast texts that are like 'Lỗi' or "Lỗi"
        text = re.sub(r"'" + re.escape(vi) + r"'", f"'{en}'", text)
        text = re.sub(r'"' + re.escape(vi) + r'"', f'"{en}"', text)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(text)
        
if __name__ == '__main__':
    run()
