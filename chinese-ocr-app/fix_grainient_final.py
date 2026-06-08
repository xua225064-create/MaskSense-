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
      z-index: -10;
      overflow: hidden;
      pointer-events: none;
      background-color: #020617; /* Dark Navy Base */
    }

    #grainient-bg::before {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyBAMAAADsEZWCAAAAGFBMVEUAAAAAAAChoaGNjY2SkpKWlpaRkZGdnZ30Y6OIAAAACXRSTlMAMyA1QDIzJzE7B/zJAAAAKElEQVQ4y2NgwASMCgwI0KxMTAzKqGIRV0wIYCxWRC1RRG9RRE9RxABn4S0J3z3W5wAAAABJRU5ErkJggg==');
      background-repeat: repeat;
      opacity: 0.03; /* Very subtle noise */
      z-index: 10;
      pointer-events: none;
    }

    .grain-blob {
      position: absolute;
      border-radius: 50%;
      /* REMOVED filter: blur() TO FIX ALL LAG */
      animation: moveBlob 20s infinite alternate ease-in-out;
      will-change: transform;
    }

    .blob-1 {
      width: 100vw;
      height: 100vw;
      background: radial-gradient(circle, rgba(30, 58, 138, 0.4) 0%, rgba(30, 58, 138, 0) 65%); /* Deep Blue #1e3a8a */
      top: -30%;
      left: -20%;
      animation-delay: 0s;
      animation-duration: 25s;
    }

    .blob-2 {
      width: 80vw;
      height: 80vw;
      background: radial-gradient(circle, rgba(96, 165, 250, 0.15) 0%, rgba(96, 165, 250, 0) 65%); /* Accent Light Blue #60a5fa */
      bottom: -20%;
      right: -10%;
      animation-delay: -5s;
      animation-duration: 22s;
    }

    .blob-3 {
      width: 120vw;
      height: 120vw;
      background: radial-gradient(circle, rgba(37, 99, 235, 0.25) 0%, rgba(37, 99, 235, 0) 65%); /* Primary Blue #2563eb */
      top: 10%;
      left: 10%;
      animation-delay: -10s;
      animation-duration: 28s;
    }

    @keyframes moveBlob {
      0% { transform: translate(0, 0) scale(1); }
      33% { transform: translate(5vw, 8vh) scale(1.05); }
      66% { transform: translate(-6vw, 4vh) scale(0.95); }
      100% { transform: translate(3vw, -5vh) scale(1.02); }
    }
"""

content = css_regex.sub(new_css, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Lag completely fixed and colors updated!')
