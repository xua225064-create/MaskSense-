import re

file_path = r'd:\HieuDe_AI\chinese-ocr-app\index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove ALL injected Grainient CSS
css_regex = re.compile(r'\s*/\* Grainient Background \*/.*?@keyframes moveBlob \{.*?\}\s*', re.DOTALL)
content = css_regex.sub('\n', content)

# Inject clean, optimized CSS only ONCE before the FIRST </style>
css = """
    /* Grainient Background */
    #grainient-bg {
      position: fixed;
      inset: 0;
      z-index: 0;
      overflow: hidden;
      pointer-events: none;
      background-color: #020617; /* Dark Navy Base */
    }

    #grainient-bg::before {
      content: "";
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      /* Lightweight CSS noise instead of heavy SVG */
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='1.5' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.08'/%3E%3C/svg%3E");
      opacity: 0.8;
      mix-blend-mode: color-dodge;
      z-index: 10;
      pointer-events: none;
    }

    .grain-blob {
      position: absolute;
      border-radius: 50%;
      filter: blur(90px);
      opacity: 0.6;
      animation: moveBlob 20s infinite alternate ease-in-out;
      will-change: transform;
    }

    /* Vibrant but dark-theme compatible colors */
    .blob-1 {
      width: 50vw;
      height: 50vw;
      background: radial-gradient(circle, #3b82f6 0%, rgba(59, 130, 246, 0) 70%); /* Primary Blue */
      top: -10%;
      left: -10%;
      animation-delay: 0s;
      animation-duration: 25s;
    }

    .blob-2 {
      width: 45vw;
      height: 45vw;
      background: radial-gradient(circle, #8b5cf6 0%, rgba(139, 92, 246, 0) 70%); /* Violet */
      bottom: -10%;
      right: -10%;
      animation-delay: -5s;
      animation-duration: 22s;
    }

    .blob-3 {
      width: 60vw;
      height: 60vw;
      background: radial-gradient(circle, #0ea5e9 0%, rgba(14, 165, 233, 0) 70%); /* Sky Blue */
      top: 30%;
      left: 20%;
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

# Insert only at the first </style>
content = content.replace('</style>', css + '\n  </style>', 1)

# Fix .site-footer CSS to ensure it renders on top and transparent
content = content.replace(
    '.site-footer {\n      background: var(--paper);',
    '.site-footer {\n      background: transparent;\n      position: relative;\n      z-index: 10;'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Grainient optimized and footer fixed!')
