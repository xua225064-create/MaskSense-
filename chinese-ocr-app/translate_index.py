import os
import re

def translate_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    for vi, en in replacements.items():
        text = text.replace(vi, en)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)

index_replacements = {
    "'Phân tích 4-Pipeline'": "'4-Pipeline Analysis'",
    "'<b>📊 Chi tiết xử lý:</b>'": "'<b>📊 Processing Details:</b>'",
    "'LLM đọc ảnh'": "'LLM vision read'",
    "'Selenium tìm ảnh'": "'Selenium image search'",
    "'🗳 Kết luận: <b>'": "'🗳 Conclusion: <b>'",
    "'✅ <b>Đã kiểm chứng bằng nguồn web</b>'": "'✅ <b>Verified by web sources</b>'",
    "'⚠ <b>Có nguồn tham khảo, cần đối chiếu thêm</b>'": "'⚠ <b>Has reference sources, needs further comparison</b>'",
    "'⚠ <b>Chưa tìm được link nguồn web đủ rõ</b>'": "'⚠ <b>Clear web source link not found yet</b>'",
    "'<br><b>Nguồn ủng hộ:</b>'": "'<br><b>Supporting sources:</b>'",
    "'<br><b>Link minh chứng / nguồn đã tra cứu:</b>'": "'<br><b>Evidence link / searched sources:</b>'",
    "'Nguồn '": "'Source '",
    "'1️⃣ Tiền xử lý ảnh...'": "'1️⃣ Image Pre-processing...'",
    "'2️⃣ Luồng A: OCR + LLM kiểm tra...'": "'2️⃣ Pipeline A: OCR + LLM check...'",
    "'3️⃣ Luồng B: LLM đọc ảnh...'": "'3️⃣ Pipeline B: LLM vision read...'",
    "'4️⃣ Luồng C: Selenium tìm ảnh...'": "'4️⃣ Pipeline C: Selenium image search...'",
    "'5️⃣ Luồng D: Feature matching...'": "'5️⃣ Pipeline D: Feature matching...'",
    "'6️⃣ Tổng hợp & hợp nhất...'": "'6️⃣ Aggregation & consolidation...'",
    "'7️⃣ Tạo báo cáo chi tiết...'": "'7️⃣ Generating detailed report...'",
    "'Hoàn tất!'": "'Completed!'",
    "'⏳ Đang lưu...'": "'⏳ Saving...'",
    "'✅ Đã ghi nhớ thành công!'": "'✅ Remembered successfully!'",
    "'❌ Lỗi: '": "'❌ Error: '",
    "'❌ Lỗi kết nối'": "'❌ Connection error'",
    "'Mã GD'": "'Txn Code'",
    "'Không rõ'": "'Unknown'",
    "'Không có chữ'": "'No text'",
    "'Gói Cơ bản'": "'Basic Package'",
    "'Gói Phổ biến'": "'Popular Package'",
    "'Gói Chuyên nghiệp'": "'Professional Package'",
    "'Trọn gói '": "'Total '",
    "' lượt quét'": "' scans'",
    "'Quét vô hạn'": "'Unlimited scans'",
    "'ĐANG XỬ LÝ...'": "'PROCESSING...'",
    "'Lỗi'": "'Error'",
    "'Thanh toán thất bại.'": "'Payment failed.'",
    "'Không thể kết nối đến máy chủ.'": "'Cannot connect to server.'",
    "'TIẾP TỤC'": "'CONTINUE'",
    "'Thanh toán thành công! 🎉'": "'Payment successful! 🎉'",
    "'ĐANG KIỂM TRA...'": "'CHECKING...'",
    "'Chưa nhận được thanh toán'": "'Payment not received yet'",
    "'Hệ thống vẫn đang chờ xác nhận từ ngân hàng. Quá trình này có thể mất 1-3 phút.'": "'System is waiting for bank confirmation. This process may take 1-3 minutes.'",
    "'Lỗi kết nối khi kiểm tra trạng thái.'": "'Connection error when checking status.'",
    "'Chào mừng '": "'Welcome '",
    "'Facebook SDK chưa được tải. Vui lòng tải lại trang.'": "'Facebook SDK not loaded. Please reload the page.'",
    "'Đăng nhập Facebook thành công!'": "'Facebook login successful!'",
    "'Đăng nhập Facebook bị hủy hoặc bị chặn.'": "'Facebook login cancelled or blocked.'",
    "'Không thể gọi Facebook Login: '": "'Cannot call Facebook Login: '",
    "'Đăng nhập bằng '": "'Sign in with '",
    "' thành công!'": "' successful!'",
    "'Đăng nhập thành công! Xin chào '": "'Login successful! Hello '",
    "'Google SDK chưa được tải. Vui lòng tải lại trang.'": "'Google SDK not loaded. Please reload the page.'",
    "'Hồ sơ của tôi'": "'My Profile'",
    "'Lịch sử giao dịch'": "'Transaction History'",
    "'Đã đăng xuất'": "'Signed out'",
    "'Thông báo'": "'Notification'",
    "'Trợ lý MarkSense'": "'MarkSense Assistant'",
    "'Nhập câu trả lời...'": "'Enter reply...'"
}

if __name__ == '__main__':
    translate_file('index.html', index_replacements)
    print("index.html js strings translated.")
