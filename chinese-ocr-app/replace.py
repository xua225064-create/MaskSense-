import sys

file_path = r'd:\HieuDe_AI\chinese-ocr-app\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if '<!-- Features Section -->' in line and start_idx == -1:
        start_idx = i
    if start_idx != -1 and '<!-- HISTORY -->' in line:
        end_idx = i - 1
        break

if start_idx != -1 and end_idx != -1:
    heritage_html = '''    <!-- Vietnam Heritage Section -->
    <div style="max-width: 1200px; margin: 120px auto 80px; padding: 0 20px;">
      <div style="text-align: center; margin-bottom: 56px;" class="reveal-up">
        <div style="display: inline-block; font-size: 0.75rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #a855f7; margin-bottom: 16px; background: rgba(168, 85, 247, 0.1); padding: 6px 16px; border-radius: 99px; border: 1px solid rgba(168,85,247,0.2);">Vietnamese Heritage</div>
        <h2 style="color: #fff; font-size: 2.75rem; letter-spacing: -0.5px; margin-bottom: 20px; font-family: 'Merriweather', serif;">Hiệu Đề Việt Nam</h2>
        <p style="color: #94a3b8; max-width: 600px; margin: 0 auto; line-height: 1.6; font-size: 1.05rem;">Khám phá bộ sưu tập đồ gốm sứ ký kiểu thời Lê - Trịnh và triều Nguyễn (Nội Phủ, Thiệu Trị Niên Tạo, Tự Đức Niên Tạo).</p>
      </div>
      
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 32px;">
        <!-- Card 1 -->
        <div class="reveal-up" style="background: linear-gradient(160deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.4) 100%); border: 1px solid rgba(255, 255, 255, 0.08); border-top: 1px solid rgba(255,255,255,0.15); border-radius: 20px; overflow: hidden; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='translateY(-12px)'; this.style.borderColor='rgba(168, 85, 247, 0.4)'; this.style.boxShadow='0 24px 48px rgba(0,0,0,0.5), 0 0 20px rgba(168,85,247,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.borderColor='rgba(255, 255, 255, 0.08)'; this.style.boxShadow='0 8px 24px rgba(0,0,0,0.2)';">
          <div style="height: 240px; overflow: hidden; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; background: #f8fafc;">
            <img src="/uploads/1_14315c80_scan.jpg" alt="Nội Phủ Thị Trung" style="max-width: 90%; max-height: 90%; object-fit: contain; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1)); transition: transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'">
          </div>
          <div style="padding: 32px;">
            <div style="font-size: 0.8rem; color: #a855f7; font-weight: 700; margin-bottom: 12px; letter-spacing: 1px;">THỜI LÊ - TRỊNH (THẾ KỶ 18)</div>
            <h3 style="color: #fff; font-size: 1.35rem; margin-bottom: 16px; font-weight: 700; letter-spacing: -0.01em;">Nội Phủ Thị Trung</h3>
            <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.6;">Đồ sứ ký kiểu dành riêng cho phủ chúa Trịnh, đặc trưng bởi nét vẽ lam sắc sảo và cốt gốm Cảnh Đức Trấn thượng hạng.</p>
          </div>
        </div>
        
        <!-- Card 2 -->
        <div class="reveal-up" style="transition-delay: 0.1s; background: linear-gradient(160deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.4) 100%); border: 1px solid rgba(255, 255, 255, 0.08); border-top: 1px solid rgba(255,255,255,0.15); border-radius: 20px; overflow: hidden; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='translateY(-12px)'; this.style.borderColor='rgba(96, 165, 250, 0.4)'; this.style.boxShadow='0 24px 48px rgba(0,0,0,0.5), 0 0 20px rgba(96,165,250,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.borderColor='rgba(255, 255, 255, 0.08)'; this.style.boxShadow='0 8px 24px rgba(0,0,0,0.2)';">
          <div style="height: 240px; overflow: hidden; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; background: #f8fafc;">
            <img src="/uploads/1_1bd092c1_scan.jpg" alt="Minh Mạng Niên Tạo" style="max-width: 90%; max-height: 90%; object-fit: contain; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1)); transition: transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'">
          </div>
          <div style="padding: 32px;">
            <div style="font-size: 0.8rem; color: #60a5fa; font-weight: 700; margin-bottom: 12px; letter-spacing: 1px;">TRIỀU NGUYỄN (1820 - 1841)</div>
            <h3 style="color: #fff; font-size: 1.35rem; margin-bottom: 16px; font-weight: 700; letter-spacing: -0.01em;">Minh Mạng Niên Tạo</h3>
            <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.6;">Hiệu đề hoàng gia triều Nguyễn thời kỳ đầu. Đồ sứ thời này thường mang họa tiết rồng mây uy nghi, chuẩn mực hoàng gia.</p>
          </div>
        </div>
        
        <!-- Card 3 -->
        <div class="reveal-up" style="transition-delay: 0.2s; background: linear-gradient(160deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.4) 100%); border: 1px solid rgba(255, 255, 255, 0.08); border-top: 1px solid rgba(255,255,255,0.15); border-radius: 20px; overflow: hidden; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='translateY(-12px)'; this.style.borderColor='rgba(16, 185, 129, 0.4)'; this.style.boxShadow='0 24px 48px rgba(0,0,0,0.5), 0 0 20px rgba(16,185,129,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.borderColor='rgba(255, 255, 255, 0.08)'; this.style.boxShadow='0 8px 24px rgba(0,0,0,0.2)';">
          <div style="height: 240px; overflow: hidden; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; background: #f8fafc;">
            <img src="/uploads/1_2527f300_scan.jpg" alt="Thiệu Trị Niên Tạo" style="max-width: 90%; max-height: 90%; object-fit: contain; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1)); transition: transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'">
          </div>
          <div style="padding: 32px;">
            <div style="font-size: 0.8rem; color: #10b981; font-weight: 700; margin-bottom: 12px; letter-spacing: 1px;">TRIỀU NGUYỄN (1841 - 1847)</div>
            <h3 style="color: #fff; font-size: 1.35rem; margin-bottom: 16px; font-weight: 700; letter-spacing: -0.01em;">Thiệu Trị Niên Tạo</h3>
            <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.6;">Đỉnh cao của nghệ thuật pháp lam và gốm sứ men lam ký kiểu, mang đậm chất thơ và nghệ thuật tinh tế của vua Thiệu Trị.</p>
          </div>
        </div>
      </div>
    </div>\n\n'''
    
    # We replace from start_idx to end_idx with heritage_html
    new_lines = lines[:start_idx] + [heritage_html] + lines[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f'Successfully replaced lines {start_idx} to {end_idx} with Vietnam Heritage section.')
else:
    print(f'Failed. start_idx: {start_idx}, end_idx: {end_idx}')
