import os
import re

def find_vietnamese(directory):
    vietnamese_pattern = re.compile(r'[áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ]')
    
    for root, _, files in os.walk(directory):
        # exclude some directories like env, __pycache__
        if any(ignored in root for ignored in ['.git', '__pycache__', 'env', 'venv']):
            continue
            
        for file in files:
            if file.endswith('.py') or file.endswith('.html') or file.endswith('.js'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                    for i, line in enumerate(lines):
                        if vietnamese_pattern.search(line):
                            # Print only a short snippet to avoid flooding output
                            print(f"{path}:{i+1} - {line.strip()[:60]}")
                except Exception as e:
                    pass

if __name__ == '__main__':
    find_vietnamese('.')
