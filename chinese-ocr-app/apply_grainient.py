import re

file_path = r'd:\HieuDe_AI\chinese-ocr-app\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the Grainient CSS block
css_regex = re.compile(r'\s*/\* Grainient Background \*/.*?@keyframes moveBlob \{.*?\}\s*', re.DOTALL)

new_css = """
    /* Grainient Background */
    #grainient-bg {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      z-index: 0;
      overflow: hidden;
      pointer-events: none;
      background-color: #0f0c29; /* Deep dark purple base */
    }

    #grainient-bg::after {
      content: "";
      position: absolute;
      inset: 0;
      /* Heavy grain/noise overlay using SVG data URI */
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
      opacity: 0.25;
      mix-blend-mode: overlay;
      z-index: 10;
      pointer-events: none;
    }

    .grain-blob {
      position: absolute;
      border-radius: 50%;
      will-change: transform;
      mix-blend-mode: screen;
      filter: blur(60px);
    }

    .blob-1 {
      width: 70vw;
      height: 70vw;
      background: radial-gradient(circle, rgba(219, 39, 119, 0.7) 0%, rgba(219, 39, 119, 0) 70%); /* Pink */
      top: -20%;
      left: -10%;
      animation: float1 20s infinite alternate ease-in-out;
    }

    .blob-2 {
      width: 80vw;
      height: 80vw;
      background: radial-gradient(circle, rgba(67, 56, 202, 0.8) 0%, rgba(67, 56, 202, 0) 70%); /* Indigo */
      bottom: -30%;
      right: -20%;
      animation: float2 24s infinite alternate ease-in-out;
    }

    .blob-3 {
      width: 60vw;
      height: 60vw;
      background: radial-gradient(circle, rgba(6, 182, 212, 0.6) 0%, rgba(6, 182, 212, 0) 70%); /* Cyan */
      top: 40%;
      left: 60%;
      animation: float3 22s infinite alternate ease-in-out;
    }

    .blob-4 {
      width: 75vw;
      height: 75vw;
      background: radial-gradient(circle, rgba(245, 158, 11, 0.5) 0%, rgba(245, 158, 11, 0) 70%); /* Amber */
      top: 10%;
      left: 30%;
      animation: float4 26s infinite alternate ease-in-out;
    }

    @keyframes float1 {
      0% { transform: translate(0, 0) scale(1) rotate(0deg); }
      50% { transform: translate(15vw, 15vh) scale(1.2) rotate(90deg); }
      100% { transform: translate(-5vw, 25vh) scale(0.9) rotate(180deg); }
    }

    @keyframes float2 {
      0% { transform: translate(0, 0) scale(1) rotate(0deg); }
      50% { transform: translate(-20vw, -15vh) scale(1.1) rotate(-90deg); }
      100% { transform: translate(10vw, -25vh) scale(1.05) rotate(-180deg); }
    }

    @keyframes float3 {
      0% { transform: translate(0, 0) scale(1) rotate(0deg); }
      50% { transform: translate(-25vw, 10vh) scale(1.3) rotate(120deg); }
      100% { transform: translate(-10vw, -10vh) scale(0.95) rotate(240deg); }
    }

    @keyframes float4 {
      0% { transform: translate(0, 0) scale(1) rotate(0deg); }
      50% { transform: translate(20vw, -20vh) scale(1.15) rotate(-120deg); }
      100% { transform: translate(5vw, 15vh) scale(1.05) rotate(-240deg); }
    }
"""

content = css_regex.sub(new_css, content)

# Check if there are only 3 blobs in HTML, and add the 4th
html_regex = re.compile(r'<div id="grainient-bg">.*?</div>', re.DOTALL)
new_html = '''<div id="grainient-bg">
    <div class="grain-blob blob-1"></div>
    <div class="grain-blob blob-2"></div>
    <div class="grain-blob blob-3"></div>
    <div class="grain-blob blob-4"></div>
  </div>'''
content = html_regex.sub(new_html, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Grainient applied!')
