import re

file_path = r'd:\HieuDe_AI\chinese-ocr-app\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the Grainient CSS block
css_regex = re.compile(r'\s*/\* Grainient Background \*/.*?@keyframes float4 \{.*?\}\s*', re.DOTALL)

# In case the previous regex fails (if they were named moveBlob), let's use a broader regex or run it twice.
css_regex_fallback = re.compile(r'\s*/\* Grainient Background \*/.*?</div>\s*</div>', re.DOTALL) # wait no

# Let's read the file and replace everything between /* Grainient Background */ and </style>
css_start = content.find('/* Grainient Background */')
css_end = content.find('</style>', css_start)

if css_start != -1 and css_end != -1:
    new_css = """/* Grainient Background */
    #grainient-bg {
      position: fixed;
      inset: 0; /* Ensures it covers the entire screen, fixing the "only at top" issue */
      z-index: 0;
      overflow: hidden;
      pointer-events: none;
      background-color: transparent; /* Let the body's #020617 show through */
    }

    #grainient-bg::after {
      content: "";
      position: absolute;
      inset: 0;
      /* Very lightweight static base64 noise - NO LAG */
      background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyBAMAAADsEZWCAAAAGFBMVEUAAAAAAAChoaGNjY2SkpKWlpaRkZGdnZ30Y6OIAAAACXRSTlMAMyA1QDIzJzE7B/zJAAAAKElEQVQ4y2NgwASMCgwI0KxMTAzKqGIRV0wIYCxWRC1RRG9RRE9RxABn4S0J3z3W5wAAAABJRU5ErkJggg==');
      background-repeat: repeat;
      opacity: 0.05;
      z-index: 10;
      pointer-events: none;
    }

    .grain-blob {
      position: absolute;
      border-radius: 50%;
      will-change: opacity;
      /* We use Opacity animation instead of Transform to guarantee 0% LAG on all devices */
    }

    /* Colors synced with web: Deep Navy and Primary Blue */
    .blob-1 {
      width: 120vw;
      height: 120vw;
      background: radial-gradient(circle, rgba(30, 58, 138, 0.25) 0%, rgba(30, 58, 138, 0) 60%); /* Deep Blue */
      top: -40%;
      left: -30%;
      animation: pulseBlob 12s infinite alternate ease-in-out;
    }

    .blob-2 {
      width: 100vw;
      height: 100vw;
      background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, rgba(59, 130, 246, 0) 60%); /* Primary Blue */
      bottom: -30%;
      right: -20%;
      animation: pulseBlob 16s infinite alternate-reverse ease-in-out;
    }

    .blob-3 {
      width: 140vw;
      height: 140vw;
      background: radial-gradient(circle, rgba(96, 165, 250, 0.1) 0%, rgba(96, 165, 250, 0) 60%); /* Accent Blue */
      top: 20%;
      left: 10%;
      animation: pulseBlob 20s infinite alternate ease-in-out;
    }

    @keyframes pulseBlob {
      0% { opacity: 0.3; }
      100% { opacity: 1; }
    }
    """
    content = content[:css_start] + new_css + content[css_end:]

# Update the HTML to have 3 blobs
html_regex = re.compile(r'<div id="grainient-bg">.*?</div>', re.DOTALL)
new_html = '''<div id="grainient-bg">
    <div class="grain-blob blob-1"></div>
    <div class="grain-blob blob-2"></div>
    <div class="grain-blob blob-3"></div>
  </div>'''
content = html_regex.sub(new_html, content)

# Ensure body has the dark background to prevent any white canvas issues
content = content.replace('body {\n      font-family: \'Inter\', sans-serif;\n      background: transparent;', 'body {\n      font-family: \'Inter\', sans-serif;\n      background: var(--paper);')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('V3 applied!')
