import re

def translate_final(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    replacements = [
        # Features section
        (r'Ứng dụng công nghệ thị giác máy\s*tính và học sâu tối tân để nhận diện với độ chính xác cao\.',
         'Applying advanced computer vision and deep learning technology for high accuracy recognition.'),
        (r'Hàng ngàn mẫu hiệu đề được thu\s*thập và số hóa từ nhiều triều đại khác nhau\.',
         'Thousands of mark samples have been collected and digitized from various dynasties.'),
        (r'Kết quả được trả về chỉ trong\s*vài giây\. Tiết kiệm thời gian so với tra cứu thủ công\.',
         'Results returned in just a few seconds. Save time compared to manual research.'),
        
        # FAQ section
        (r'Hệ thống hiện cung cấp tính năng tra cứu cơ sở dữ liệu và 5 lượt analyze đầu\s*tiên miễn phí cho tất cả tài khoản\. Với nhu cầu lưu trữ và nhận dạng khối lượng lớn, người dùng có thể tham\s*khảo bảng giá dịch vụ cao cấp\.',
         'The system provides database lookup and 5 free initial analysis credits for all accounts. For high-volume storage and recognition needs, users can refer to the premium pricing.'),
        (r'Lõi OCR của hệ thống có khả năng khôi phục một phần nét mờ dựa trên ngữ cảnh cấu\s*trúc chữ Hán\. Tuy nhiên, hình ảnh cần được chụp rõ ràng, đủ ánh sáng, góc chụp vuông góc để tối đa hóa xác\s*suất trùng khớp\.',
         'The system\'s OCR core can partially restore blurred strokes based on Chinese character context. However, images need to be clear, well-lit, and captured perpendicularly to maximize matching probability.'),
        (r'Toàn bộ tác vụ nhận dạng được ghi nhận và lưu trong bộ nhớ tạm theo phiên làm\s*việc\. Chúng tôi đang hoàn thiện cơ sở dữ liệu vĩnh viễn \(cùng chức năng xóa thủ công\) ở bản cập nhật tiếp',
         'All recognition tasks are recorded in temporary session memory. We are finalizing the permanent database (along with manual deletion functionality) in the next update'),
        (r'Bộ dữ liệu tập trung mạnh nhất vào các mẫu gốm sứ thuộc đại triều nhà Thanh, nhà\s*Minh và nhà Nguyễn\. Các niên đại khác \(Tống, Nguyên\) đang trong quá trình số hóa và credits hợp dần\.',
         'The dataset focuses strongly on ceramics from the great Qing, Ming, and Nguyen dynasties. Other periods (Song, Yuan) are being digitized and integrated gradually.'),
        
        # Chatbot
        (r'Xin chào! 👋 Mình là trợ lý AI của MarkSense\. Bạn cần giúp đỡ về cách dùng quét hiệu đề\s*hay thông tin nâng cấp tài khoản\?',
         'Hello! 👋 I am the MarkSense AI assistant. Do you need help using the mark scanner or account upgrade info?'),
         
        # Other string values
        (r'Đang chuyển hướng sang ứng dụng Email\.\.\.', 'Redirecting to Email app...'),
        (r'Ngân hàng TMCP\s*Phương Đông \(OCB\)', 'Orient Commercial Joint Stock Bank (OCB)'),
        (r'Bạn cần hỗ trợ gì\?', 'How can we help you?'),
        (r'return n\.toLocaleString\(\'vi-VN\'\) \+ \'đ\';', "return n.toLocaleString('en-US') + ' VND';"),
        (r"Lỗi khi tải thư viện:", "Error loading library:"),
        (r"Chạy toàn bộ 4 pipeline", "Run all 4 pipelines")
    ]

    for pattern, eng in replacements:
        text = re.sub(pattern, eng, text)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)

if __name__ == '__main__':
    translate_final('index.html')
    print("Done applying final regex replacements.")
