import re

file_path = r'd:\HieuDe_AI\chinese-ocr-app\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove Facebook SDK Boilerplate
sdk_regex = re.compile(r'<!-- Facebook SDK Boilerplate -->.*?<script async defer crossorigin="anonymous" src="https://connect\.facebook\.net/vi_VN/sdk\.js"></script>', re.DOTALL)
content = sdk_regex.sub('', content)

# 2. Remove .fb-btn CSS
css_regex = re.compile(r'\s*\.fb-btn\s*\{.*?\}\s*\.fb-btn:hover\s*\{.*?\}', re.DOTALL)
content = css_regex.sub('', content)

css_regex_custom = re.compile(r'\s*\.social-btn-custom\.fb-btn\s*\{.*?\}\s*\.social-btn-custom\.fb-btn:hover\s*\{.*?\}', re.DOTALL)
content = css_regex_custom.sub('', content)

# 3. Remove Facebook Buttons
btn_regex = re.compile(r'<button class="social-btn-custom fb-btn" onclick="doSocialLogin\(\'Facebook\'\)">(?:(?!</button>).)*?</button>', re.DOTALL)
content = btn_regex.sub('', content)

# 4. Remove Facebook Provider logic in JS
js_regex = re.compile(r'if \(provider === \'Facebook\'\)\s*\{.*?(?:(?!\n      \}\n).)*\n      \}\n', re.DOTALL)
content = js_regex.sub('', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Facebook login removed!')
