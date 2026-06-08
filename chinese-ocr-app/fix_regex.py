import re

def fix_with_regex(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    replacements = [
        (r'Lưu trữ và bảo vệ kiến thức gốm sứ\s*truyền thống', 'Store and protect traditional ceramic knowledge'),
        (r'Kết quả chi tiết chỉ trong vài\s*giây', 'Detailed results in just a few seconds'),
        (r'Quên mật\s*khẩu\?', 'Forgot password?'),
        (r'và\s*<a\s*href="#">Privacy Policy</a> của chúng tôi\.', 'and our <a href="#">Privacy Policy</a>.'),
        (r'và <a href="#">Chính\s*sách bảo mật</a>', 'and <a href="#">Privacy Policy</a>'),
        (r'Hệ thống ứng dụng sức mạnh của mô hình PaddleOCR kết hợp cùng các kỹ thuật tiền xử lý\s*ảnh \(Computer Vision\) để trích xuất ký tự Hán Nôm từ hình ảnh hiệu đề một cách tự động và ổn định\.', 'The system leverages the power of PaddleOCR combined with image pre-processing techniques (Computer Vision) to automatically and stably extract Sino-Nom characters from mark images.'),
        (r'Bên cạnh việc đọc chữ, hệ thống triển khai thuật toán ORB \(Oriented FAST and Rotated\s*BRIEF\) nhằm trích xuất và đối chiếu các điểm đặc trưng hình học, giúp đối soát chéo với cơ sở dữ liệu mẫu\.', 'Besides reading text, the system implements the ORB (Oriented FAST and Rotated BRIEF) algorithm to extract and compare geometric features, enabling cross-checking with the sample database.'),
        (r'Xây dựng kiến trúc lưu trữ có cấu trúc \(MySQL\) quản lý thông tin các mẫu hiệu đề\s*thuộc các đại triều \(Thanh, Minh, Nguyễn\), hỗ trợ trích xuất thông tin niên đại và giải nghĩa nhanh chóng', 'Building a structured storage architecture (MySQL) to manage information of mark samples from major dynasties (Qing, Ming, Nguyen), supporting rapid extraction of dating information and interpretation.'),
        (r'MarkSense AI là một giải pháp phần mềm được thiết kế để hỗ trợ công tác số hóa di\s*sản\. Thay vì tra cứu thủ công qua sách vở, hệ thống cung cấp một công cụ đối chiếu kỹ thuật số trực quan,\s*giúp người dùng dễ dàng tiếp cận và tìm hiểu thông tin lịch sử của gốm sứ cổ truyền\.', 'MarkSense AI is a software solution designed to support heritage digitization. Instead of manual book searching, the system provides an intuitive digital reference tool, making it easy for users to access and explore the historical information of traditional ceramics.'),
        (r'Bạn có câu hỏi hoặc cần hỗ trợ\? Đội ngũ chuyên gia của MarkSense AI\s*luôn sẵn sàng\.', 'Have questions or need help? The MarkSense AI expert team is always ready.'),
        
        # Guide
        (r'Bắt đầu quá trình nhận dạng và giám định hiệu đề gốm sứ với 3 bước cơ bản trên hệ thống', 'Start the mark recognition and authentication process with 3 basic steps on the system'),
        (r'Nhấp vào "Sign In" ở góc trên cùng bên phải\. Tạo tài khoản mới hoặc sử dụng hệ thống đăng nhập một chạm\s*\(Google/SSO\) để cấp quyền truy cập\. Việc định danh là bắt buộc nhằm mục đích store personal analysis history\s*nhân\.', 'Click "Sign In" in the top right corner. Create a new account or use the one-tap login system (Google/SSO) for access. Identification is required to store personal analysis history.'),
        (r'Tại giao diện trung tâm, tải lên hình ảnh chụp hiệu đề hoặc sử dụng thao tác kéo thả\. Nhấp "Bắt đầu phân\s*credits" để activate the computer vision AI core to process the image\.', 'At the main interface, upload a mark image or use drag and drop. Click "Start analysis" to activate the computer vision AI core to process the image.'),
        (r'Hệ thống sẽ trả về kết quả nhận dạng Hán Nôm, phiên âm, triều đại và mẫu tham chiếu từ kho lưu trữ\. Tất cả\s*báo cáo được tự động lưu trong mục "History" để tra cứu sau này\.', 'The system will return Sino-Nom recognition, transcription, dynasty, and reference sample from the repository. All reports are automatically saved in the "History" section for future reference.'),
        
        # Policy
        (r'Chúng tôi chỉ thu thập dữ liệu định danh ở mức tối thiểu \(email\) nhằm duy trì phiên đăng\s*nhập hợp lệ\. Các hình ảnh tải lên được tiếp nhận và xử lý cục bộ trên hệ thống server\.', 'We only collect minimal identification data (email) to maintain valid login sessions. Uploaded images are received and processed locally on the server.'),
        (r'danh hoàn toàn \(anonymized\) nếu được sử dụng như một phần của tập huấn luyện \(training set\) để cải thiện độ\s*chính xác OCR trong tương lai\.', 'fully anonymized if used as part of the training set to improve future OCR accuracy.'),
        (r'Tất cả phiên truyền tải dữ liệu đều được mã hóa theo chuẩn SSL/TLS\. Cơ sở dữ liệu và thư\s*mục hình ảnh của người dùng được Unlimited quyền truy cập bằng kiến trúc bảo mật đa tầng\.', 'All data transmission sessions are encrypted with SSL/TLS standards. The user database and image directories have restricted access using multi-layer security architecture.'),
        (r'Sử dụng hệ thống giải pháp MarkSense AI đồng nghĩa với việc bạn chấp thuận các quy định pháp\s*lý sau\.', 'Using the MarkSense AI solution implies your acceptance of the following legal terms.'),
        (r'tác giám định chuyên môn\. MarkSense AI không chịu trách nhiệm đối với bất kỳ quyết định mua bán, giao dịch hay\s*thẩm định giá trị nào dựa trên hệ thống\.', 'professional authentication. MarkSense AI is not liable for any buying, selling, or valuation decisions based on the system.'),
        (r'Người dùng cam kết sở hữu hợp pháp hình ảnh tải lên hệ thống\. Bất kỳ khiếu nại bản quyền\s*nào phát sinh từ các mẫu cổ vật số hóa do người dùng tải lên sẽ thuộc trách nhiệm của người đó\.', 'Users commit to legally owning the images uploaded to the system. Any copyright claims arising from digitized artifacts uploaded by the user are their sole responsibility.'),
        (r'Cấu trúc hệ thống, trọng số mô hình AI, thuật toán xử lý ảnh \(Computer Vision\), cùng kho\s*dữ liệu tham chiếu là tài sản trí tuệ độc quyền của đội ngũ HieuDe Team\.', 'The system architecture, AI model weights, Computer Vision algorithms, and reference database are the exclusive intellectual property of the HieuDe Team.'),
        
        # JS vars
        (r"'Chưa rõ'", "'Unknown'"),
        (r"'Chưa xác định'", "'Unknown'"),
        (r"'Không có mô tả'", "'No description'"),
        (r"Thời kỳ:", "Period:"),
        (r"Đặc điểm:", "Features:"),
        (r"'Hiệu đề'", "'Mark'"),
        (r"'Gốm sứ'", "'Ceramic'"),
        (r"'Không tìm thấy hiệu đề phù hợp\.'", "'No matching marks found.'"),
        (r"'Không thể truy cập camera\. Vui lòng kiểm tra quyền\.'", "'Cannot access camera. Please check permissions.'"),
        (r"Lỗi kết nối — vui lòng thử lại", "Connection error - please try again"),
        (r"'Thành công'", "'Success'"),
        (r"'Đang chờ'", "'Pending'"),
        (r"'Thất bại'", "'Failed'"),
        (r"Lỗi:", "Error:"),
        (r"Lỗi giả lập thanh toán:", "Payment simulation error:"),
        (r"Lỗi kết nối:", "Connection error:")
    ]

    for pattern, eng in replacements:
        text = re.sub(pattern, eng, text)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)

if __name__ == '__main__':
    fix_with_regex('index.html')
    print("Done applying regex replacements.")
