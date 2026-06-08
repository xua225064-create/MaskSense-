import re
import codecs

def run():
    with open('index.html', 'r', encoding='utf-8') as f:
        text = f.read()

    # Extract viToEn dictionary
    match = re.search(r'var viToEn = (\{.*?\});\s*var enToVi', text, re.DOTALL)
    if not match:
        print("Could not find viToEn")
        return
        
    dict_str = match.group(1)
    # Extract all key-value pairs
    # They look like: 'Trang chủ': 'Home',
    items = re.findall(r"'([^']+)':\s*'([^']+)'", dict_str)
    
    print(f"Found {len(items)} translation pairs")
    
    # Sort by length descending
    items.sort(key=lambda x: len(x[0]), reverse=True)
    
    # Replace in the HTML portion. Let's do a simple replace since Vietnamese strings are unique.
    # We should replace >Text< and placeholder="Text"
    for vi, en in items:
        # replace inner text
        text = text.replace(f">{vi}<", f">{en}<")
        text = text.replace(f">{vi}\n", f">{en}\n")
        text = text.replace(f">\n{vi}<", f">\n{en}<")
        # replace placeholders
        text = text.replace(f'placeholder="{vi}"', f'placeholder="{en}"')
        # replace title
        text = text.replace(f'title="{vi}"', f'title="{en}"')
        # replace raw text (with caution, but since they are Vietnamese phrases, it's safe)
        text = text.replace(f"'{vi}'", f"'{en}'")
        text = text.replace(f'"{vi}"', f'"{en}"')

    # Remove the language toggle button
    text = re.sub(r'<button id="langToggle".*?</button>', '', text, flags=re.DOTALL)
    
    # We should also update the HTML lang attribute
    text = text.replace('<html lang="vi">', '<html lang="en">')
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(text)
        
    print("Translation applied permanently to index.html")

if __name__ == '__main__':
    run()
