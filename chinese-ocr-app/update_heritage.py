import sys

file_path = r'd:\HieuDe_AI\chinese-ocr-app\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if '<!-- Vietnam Heritage Section -->' in line and start_idx == -1:
        start_idx = i
    if start_idx != -1 and '<!-- HISTORY -->' in line:
        end_idx = i - 1
        break

if start_idx != -1 and end_idx != -1:
    heritage_html = '''    <!-- Vietnam Heritage Section -->
    <div style="max-width: 1200px; margin: 40px auto 80px; padding: 0 20px;">
      <div style="text-align: center; margin-bottom: 56px;">
        <div style="display: inline-block; font-size: 0.75rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #60a5fa; margin-bottom: 16px; background: rgba(96, 165, 250, 0.1); padding: 6px 16px; border-radius: 99px; border: 1px solid rgba(96,165,250,0.2);">Vietnamese Heritage</div>
        <h2 style="color: #fff; font-size: 2.75rem; letter-spacing: -0.5px; margin-bottom: 20px; font-family: 'Merriweather', serif;">Vietnamese Reign Marks</h2>
        <p style="color: #94a3b8; max-width: 600px; margin: 0 auto; line-height: 1.6; font-size: 1.05rem;">Explore the collection of commissioned ceramics from the Le-Trinh and Nguyen dynasties.</p>
      </div>
      
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 32px;">
        <!-- Card 1 -->
        <div style="background: linear-gradient(160deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.4) 100%); border: 1px solid rgba(255, 255, 255, 0.08); border-top: 1px solid rgba(255,255,255,0.15); border-radius: 20px; overflow: hidden; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='translateY(-12px)'; this.style.borderColor='rgba(96, 165, 250, 0.4)'; this.style.boxShadow='0 24px 48px rgba(0,0,0,0.5), 0 0 20px rgba(96,165,250,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.borderColor='rgba(255, 255, 255, 0.08)'; this.style.boxShadow='0 8px 24px rgba(0,0,0,0.2)';">
          <div style="height: 240px; overflow: hidden; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.2);">
            <img src="/uploads/1_14315c80_scan.jpg" alt="Noi Phu Thi Trung" style="max-width: 90%; max-height: 90%; object-fit: contain; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1)); transition: transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'">
          </div>
          <div style="padding: 32px;">
            <div style="font-size: 0.8rem; color: #60a5fa; font-weight: 700; margin-bottom: 12px; letter-spacing: 1px;">LE - TRINH PERIOD (18TH CENTURY)</div>
            <h3 style="color: #fff; font-size: 1.35rem; margin-bottom: 16px; font-weight: 700; letter-spacing: -0.01em;">Noi Phu Thi Trung</h3>
            <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.6;">Exclusive commissioned ceramics for the Trinh Lords, characterized by sharp blue underglaze and premium Jingdezhen porcelain.</p>
          </div>
        </div>
        
        <!-- Card 2 -->
        <div style="background: linear-gradient(160deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.4) 100%); border: 1px solid rgba(255, 255, 255, 0.08); border-top: 1px solid rgba(255,255,255,0.15); border-radius: 20px; overflow: hidden; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='translateY(-12px)'; this.style.borderColor='rgba(96, 165, 250, 0.4)'; this.style.boxShadow='0 24px 48px rgba(0,0,0,0.5), 0 0 20px rgba(96,165,250,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.borderColor='rgba(255, 255, 255, 0.08)'; this.style.boxShadow='0 8px 24px rgba(0,0,0,0.2)';">
          <div style="height: 240px; overflow: hidden; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.2);">
            <img src="/uploads/1_1bd092c1_scan.jpg" alt="Minh Mang Nien Tao" style="max-width: 90%; max-height: 90%; object-fit: contain; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1)); transition: transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'">
          </div>
          <div style="padding: 32px;">
            <div style="font-size: 0.8rem; color: #60a5fa; font-weight: 700; margin-bottom: 12px; letter-spacing: 1px;">NGUYEN DYNASTY (1820 - 1841)</div>
            <h3 style="color: #fff; font-size: 1.35rem; margin-bottom: 16px; font-weight: 700; letter-spacing: -0.01em;">Minh Mang Nien Tao</h3>
            <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.6;">Early Nguyen dynasty royal mark. Ceramics of this era often feature majestic dragon motifs, setting the royal standard.</p>
          </div>
        </div>
        
        <!-- Card 3 -->
        <div style="background: linear-gradient(160deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.4) 100%); border: 1px solid rgba(255, 255, 255, 0.08); border-top: 1px solid rgba(255,255,255,0.15); border-radius: 20px; overflow: hidden; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='translateY(-12px)'; this.style.borderColor='rgba(96, 165, 250, 0.4)'; this.style.boxShadow='0 24px 48px rgba(0,0,0,0.5), 0 0 20px rgba(96,165,250,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.borderColor='rgba(255, 255, 255, 0.08)'; this.style.boxShadow='0 8px 24px rgba(0,0,0,0.2)';">
          <div style="height: 240px; overflow: hidden; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.2);">
            <img src="/uploads/1_b1724075_scan.jpg" alt="Thieu Tri Nien Tao" style="max-width: 90%; max-height: 90%; object-fit: contain; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1)); transition: transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);" onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'">
          </div>
          <div style="padding: 32px;">
            <div style="font-size: 0.8rem; color: #60a5fa; font-weight: 700; margin-bottom: 12px; letter-spacing: 1px;">NGUYEN DYNASTY (1841 - 1847)</div>
            <h3 style="color: #fff; font-size: 1.35rem; margin-bottom: 16px; font-weight: 700; letter-spacing: -0.01em;">Thieu Tri Nien Tao</h3>
            <p style="color: #94a3b8; font-size: 0.95rem; line-height: 1.6;">The pinnacle of falangcai and underglaze blue commissioned ceramics, bearing the poetic and refined artistic taste of Emperor Thieu Tri.</p>
          </div>
        </div>
      </div>
    </div>

'''
    
    new_lines = lines[:start_idx] + [heritage_html] + lines[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print('Done!')
else:
    print('Failed. start_idx:', start_idx, 'end_idx:', end_idx)
