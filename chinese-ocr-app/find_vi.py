import re
with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()
lines = text.split('\n')
with open('vi_lines.txt', 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        if re.search(r'[áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ]', line):
            out.write(f"{line.strip()[:100]}\n")
