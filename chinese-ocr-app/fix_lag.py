import re

file_path = r'd:\HieuDe_AI\chinese-ocr-app\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the CSS
css_regex = re.compile(r'\s*/\* Grainient Background \*/.*?@keyframes moveBlob \{.*?\}\s*', re.DOTALL)

new_css = """
    /* Grainient Background */
    #grainient-bg {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      z-index: -10; /* Behind everything */
      overflow: hidden;
      pointer-events: none;
      background-color: #020617; /* Dark Navy Base */
    }

    #grainient-bg::before {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      /* Tiny base64 noise image - extremely fast, NO LAG */
      background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyBAMAAADsEZWCAAAAGFBMVEUAAAAAAAChoaGNjY2SkpKWlpaRkZGdnZ30Y6OIAAAACXRSTlMAMyA1QDIzJzE7B/zJAAAAKElEQVQ4y2NgwASMCgwI0KxMTAzKqGIRV0wIYCxWRC1RRG9RRE9RxABn4S0J3z3W5wAAAABJRU5ErkJggg==');
      background-repeat: repeat;
      opacity: 0.15;
      z-index: 10;
      pointer-events: none;
    }

    .grain-blob {
      position: absolute;
      border-radius: 50%;
      filter: blur(80px);
      opacity: 0.6;
      animation: moveBlob 20s infinite alternate ease-in-out;
      will-change: transform;
    }

    .blob-1 {
      width: 80vw;
      height: 80vw;
      background: radial-gradient(circle, #3b82f6 0%, rgba(59, 130, 246, 0) 70%); /* Primary Blue */
      top: -20%;
      left: -10%;
      animation-delay: 0s;
      animation-duration: 25s;
    }

    .blob-2 {
      width: 70vw;
      height: 70vw;
      background: radial-gradient(circle, #8b5cf6 0%, rgba(139, 92, 246, 0) 70%); /* Violet */
      bottom: -20%;
      right: -10%;
      animation-delay: -5s;
      animation-duration: 22s;
    }

    .blob-3 {
      width: 90vw;
      height: 90vw;
      background: radial-gradient(circle, #0ea5e9 0%, rgba(14, 165, 233, 0) 70%); /* Sky Blue */
      top: 10%;
      left: 10%;
      animation-delay: -10s;
      animation-duration: 28s;
    }

    @keyframes moveBlob {
      0% { transform: translate(0, 0) scale(1); }
      33% { transform: translate(8vw, 12vh) scale(1.1); }
      66% { transform: translate(-10vw, 5vh) scale(0.9); }
      100% { transform: translate(5vw, -8vh) scale(1.05); }
    }
"""

content = css_regex.sub(new_css, content)

# Make body transparent so z-index -10 shows through
content = content.replace('body {\n      font-family: \'Inter\', sans-serif;\n      background: var(--paper);', 'body {\n      font-family: \'Inter\', sans-serif;\n      background: transparent;')

# Ensure .pg does not have a solid background
content = content.replace('.pg {\n      display: none;\n    }', '.pg {\n      display: none;\n      background: transparent;\n    }')

# Ensure #grainient-bg HTML is correct
grainient_html_regex = re.compile(r'<div id=\"grainient-bg\">.*?</div>\s*<nav>', re.DOTALL)
new_html = '''<div id="grainient-bg">
    <div class="grain-blob blob-1"></div>
    <div class="grain-blob blob-2"></div>
    <div class="grain-blob blob-3"></div>
  </div>

  <nav>'''
content = grainient_html_regex.sub(new_html, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Lag and coverage fixed!')
