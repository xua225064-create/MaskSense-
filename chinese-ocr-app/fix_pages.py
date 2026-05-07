import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

corrupt_start = None
pricing_start = None
for i, line in enumerate(lines):
    if 'sp-contact-icon' in line and 'GUIDE PAGE' in line:
        corrupt_start = i
    if '<!-- PRICING PAGE -->' in line:
        pricing_start = i
        break

print(f"Corrupt line: {corrupt_start}")
print(f"Pricing page starts at: {pricing_start}")

if corrupt_start is not None and pricing_start is not None:
    replacement = '''              <div class="sp-contact-icon" style="background:rgba(74,222,128,0.1)"><div class="sp-dot" style="background:#4ade80;width:12px;height:12px"></div></div>
              <div><div class="sp-contact-label">Email Hợp Tác</div><div class="sp-contact-value">xuatruong30@gmail.com</div></div>
            </div>
            <div class="sp-contact-item" style="padding-bottom:0">
              <div class="sp-contact-icon" style="background:rgba(192,132,252,0.1)"><div class="sp-dot" style="background:#c084fc;width:12px;height:12px"></div></div>
              <div><div class="sp-contact-label">Văn Phòng</div><div class="sp-contact-value">Đường 3/2, Phường Tân An,<br>Ninh Kiều, Cần Thơ</div></div>
            </div>
          </div>
        </div>
        <div>
          <div class="sp-section-label">Gửi tin nhắn</div>
          <div class="sp-card">
            <form onsubmit="event.preventDefault(); showToast('Tin nhắn đã được gửi!'); this.reset();">
              <div class="sp-form-group"><label class="sp-form-label">Họ và Tên</label><input class="sp-form-input" type="text" required placeholder="Nhập tên..."></div>
              <div class="sp-form-group"><label class="sp-form-label">Nội dung</label><textarea class="sp-form-textarea" required placeholder="Bạn cần hỗ trợ gì?"></textarea></div>
              <button type="submit" class="sp-form-btn" data-i18n="contact-send">Gửi Tin Nhắn</button>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- GUIDE PAGE -->
  <div class="pg" id="pg-guide">
    <div class="sp-page">
      <div class="sp-hero">
        <div class="sp-pill sp-pill-blue">HƯỚNG DẪN</div>
        <h1 class="sp-h1">Hướng dẫn <span>sử dụng</span></h1>
        <p class="sp-sub">Bắt đầu sử dụng MarkSense AI chỉ với 3 bước đơn giản.</p>
      </div>
      <div class="sp-card">
        <div class="sp-timeline">
          <div class="sp-step">
            <div class="sp-step-dot" style="border-color:#60a5fa"></div>
            <div class="sp-step-num" style="color:#60a5fa">Bước 01</div>
            <h3>Đăng ký &amp; Đăng nhập</h3>
            <p>Bấm vào "Đăng nhập" ở góc trên bên phải để tạo tài khoản mới hoặc đăng nhập bằng Google/SSO.</p>
          </div>
          <div class="sp-step">
            <div class="sp-step-dot" style="border-color:#a78bfa"></div>
            <div class="sp-step-num" style="color:#a78bfa">Bước 02</div>
            <h3>Phân tích hiệu đề</h3>
            <p>Tải lên hình ảnh hoặc kéo thả trực tiếp. Bấm "Bắt đầu phân tích" để hệ thống xử lý bằng AI.</p>
          </div>
          <div class="sp-step">
            <div class="sp-step-dot" style="border-color:#4ade80"></div>
            <div class="sp-step-num" style="color:#4ade80">Bước 03</div>
            <h3>Xem kết quả &amp; lịch sử</h3>
            <p>Kết quả phân tích được lưu tự động trong tab "Lịch sử" để bạn xem lại bất kỳ lúc nào.</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- PRIVACY PAGE -->
  <div class="pg" id="pg-privacy">
    <div class="sp-page">
      <div class="sp-hero">
        <div class="sp-pill sp-pill-green">BẢO MẬT</div>
        <h1 class="sp-h1">Chính sách <span>bảo mật</span></h1>
        <p class="sp-sub">Bảo vệ dữ liệu người dùng là ưu tiên hàng đầu của chúng tôi.</p>
      </div>
      <div class="sp-card">
        <div class="sp-policy-section">
          <h3 style="color:#4ade80">Thu thập thông tin</h3>
          <p>Chúng tôi chỉ thu thập thông tin tối thiểu cần thiết để duy trì tài khoản và phục vụ quá trình phân tích.</p>
        </div>
        <div class="sp-divider" style="margin:24px 0"></div>
        <div class="sp-policy-section">
          <h3 style="color:#60a5fa">Sử dụng dữ liệu</h3>
          <p>Hình ảnh tải lên được bảo mật, mã hóa và có thể được sử dụng ẩn danh để cải thiện mô hình AI.</p>
        </div>
        <div class="sp-divider" style="margin:24px 0"></div>
        <div class="sp-policy-section" style="margin-bottom:0">
          <h3 style="color:#c084fc">Bảo vệ thông tin</h3>
          <p>Chúng tôi sử dụng biện pháp bảo mật tiêu chuẩn ngành để bảo vệ dữ liệu cá nhân của bạn.</p>
        </div>
      </div>
    </div>
  </div>

  <!-- TERMS PAGE -->
  <div class="pg" id="pg-terms">
    <div class="sp-page">
      <div class="sp-hero">
        <div class="sp-pill sp-pill-blue">ĐIỀU KHOẢN</div>
        <h1 class="sp-h1">Điều khoản <span>dịch vụ</span></h1>
        <p class="sp-sub">Khi sử dụng MarkSense AI, bạn đồng ý với các điều khoản sau đây.</p>
      </div>
      <div class="sp-card" style="margin-bottom:16px">
        <div class="sp-card-title"><div class="sp-dot" style="background:#f87171"></div>Quyền rủi ro</div>
        <p class="sp-card-text">Kết quả nhận dạng chỉ mang tính tham khảo. MarkSense AI không chịu trách nhiệm pháp lý đối với quyết định dựa trên kết quả này.</p>
      </div>
      <div class="sp-card" style="margin-bottom:16px">
        <div class="sp-card-title"><div class="sp-dot" style="background:#60a5fa"></div>Bản quyền người dùng</div>
        <p class="sp-card-text">Bạn tự chịu trách nhiệm về bản quyền hình ảnh hiệu đề tải lên hệ thống.</p>
      </div>
      <div class="sp-card">
        <div class="sp-card-title"><div class="sp-dot" style="background:#4ade80"></div>Quyền sở hữu trí tuệ</div>
        <p class="sp-card-text">Toàn bộ hệ thống MarkSense AI thuộc quyền sở hữu trí tuệ của đội ngũ HieuDe Team.</p>
      </div>
    </div>
  </div>

  <!-- FAQ PAGE -->
  <div class="pg" id="pg-faq">
    <div class="sp-page">
      <div class="sp-hero">
        <div class="sp-pill sp-pill-amber">CÂU HỎI</div>
        <h1 class="sp-h1">Câu hỏi <span>thường gặp</span></h1>
        <p class="sp-sub">Tìm câu trả lời nhanh cho những thắc mắc phổ biến nhất.</p>
      </div>
      <div class="sp-faq-item open" onclick="this.classList.toggle('open')">
        <div class="sp-faq-q"><h4>MarkSense AI có miễn phí không?</h4><svg class="sp-faq-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></div>
        <div class="sp-faq-a"><div class="sp-faq-a-inner">Hiện tại hệ thống cung cấp chức năng tra cứu và phân tích cơ bản hoàn toàn miễn phí.</div></div>
      </div>
      <div class="sp-faq-item" onclick="this.classList.toggle('open')">
        <div class="sp-faq-q"><h4>Hệ thống nhận dạng kém chính xác với ảnh mờ?</h4><svg class="sp-faq-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></div>
        <div class="sp-faq-a"><div class="sp-faq-a-inner">Đúng vậy, AI phụ thuộc vào chất lượng ảnh. Vui lòng chụp ảnh đủ sáng và sắc nét.</div></div>
      </div>
      <div class="sp-faq-item" onclick="this.classList.toggle('open')">
        <div class="sp-faq-q"><h4>Làm sao để xóa lịch sử?</h4><svg class="sp-faq-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></div>
        <div class="sp-faq-a"><div class="sp-faq-a-inner">Tính năng xóa lịch sử đang được phát triển và sẽ có ở phiên bản tiếp theo.</div></div>
      </div>
      <div class="sp-faq-item" onclick="this.classList.toggle('open')">
        <div class="sp-faq-q"><h4>Hệ thống hỗ trợ những triều đại nào?</h4><svg class="sp-faq-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></div>
        <div class="sp-faq-a"><div class="sp-faq-a-inner">MarkSense AI hỗ trợ Nhà Thanh, Nhà Minh, Nhà Nguyễn và đang mở rộng thêm.</div></div>
      </div>
    </div>
  </div>'''
    
    new_lines = lines[:corrupt_start] + replacement.split('\n') + lines[pricing_start:]
    new_content = '\n'.join(new_lines)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("File fixed successfully!")
else:
    print("Could not find corruption boundaries")
