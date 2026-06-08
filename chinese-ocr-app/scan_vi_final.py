import os
import re

def find_vietnamese(directory):
    vietnamese_pattern = re.compile(r'[áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ]')
    
    with open('vi_scan_results_final.txt', 'w', encoding='utf-8') as out_f:
        for root, _, files in os.walk(directory):
            # exclude some directories like env, __pycache__
            if any(ignored in root for ignored in ['.git', '__pycache__', 'env', 'venv', 'debug', 'selenium_python_api', 'selenium_python_api - Copy']):
                continue
                
            for file in files:
                if file.endswith('.py') or file.endswith('.html') or file.endswith('.js'):
                    if file in ['scan_vi.py', 'translate.py', 'translate2.py', 'translate3.py', 'find_vi.py']:
                        continue
                        
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            
                        for i, line in enumerate(lines):
                            if vietnamese_pattern.search(line):
                                out_f.write(f"{path}:{i+1} - {line.strip()[:100]}\n")
                    except Exception as e:
                        pass

if __name__ == '__main__':
    find_vietnamese('.')
