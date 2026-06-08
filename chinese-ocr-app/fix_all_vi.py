import re

def fix_all_vietnamese(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
        
    replacements = {
        # Feature texts
        "cổ vật gốm sứ với độ chính xác cao.": "ceramic artifacts with high accuracy.",
        "và niên đại cổ vật</span>": "and artifact dating</span>",
        "Lưu trữ và bảo vệ kiến thức gốm sứ<br>truyền thống</span>": "Storing and protecting traditional<br>ceramic knowledge</span>",
        "Kết quả chi tiết chỉ trong vài<br>giây</span>": "Detailed results in just a few<br>seconds</span>",
        "Ứng dụng công nghệ thị giác máy<br>tính và học sâu tối tân để nhận diện với độ chính xác cao.": "Applying state-of-the-art computer vision<br>and deep learning technology for highly accurate recognition.",
        "Hàng ngàn mẫu hiệu đề được thu<br>thập và số hóa từ nhiều triều đại khác nhau.": "Thousands of marks have been collected<br>and digitized from various historical dynasties.",
        "Kết quả được trả về chỉ trong<br>vài giây. Tiết kiệm thời gian so với tra cứu thủ công.": "Results are returned in just a few<br>seconds. Save time compared to manual searching.",
        
        # Auth form
        "Quên mật<br>khẩu?</a>": "Forgot<br>password?</a>",
        "Quên mật khẩu?": "Forgot password?",
        "Bằng việc tiếp tục, bạn đồng ý với": "By continuing, you agree to our",
        "Điều khoản Dịch vụ": "Terms of Service",
        "Chính sách Bảo mật": "Privacy Policy",
        "Chính<br>sách bảo mật</a>": "Privacy<br>Policy</a>",
        
        # Footer / About
        "Về chúng tôi": "About Us",
        "học bằng thị giác máy tính và trí tuệ nhân tạo.": "learning through computer vision and artificial intelligence.",
        "Hệ thống ứng dụng sức mạnh của mô hình PaddleOCR kết hợp cùng các kỹ thuật tiền xử lý<br>ảnh (Computer Vision) để trích xuất ký tự Hán Nôm từ hình ảnh hiệu đề một cách tự động và ổn định.": "The system applies the power of the PaddleOCR model combined with image pre-processing techniques (Computer Vision) to extract Sino-Nom characters from mark images automatically and stably.",
        "Bên cạnh việc đọc chữ, hệ thống triển khai thuật toán ORB (Oriented FAST and Rotated<br>BRIEF) nhằm trích xuất và đối chiếu các điểm đặc trưng hình học, giúp đối soát chéo với cơ sở dữ liệu mẫu.": "In addition to reading characters, the system implements the ORB (Oriented FAST and Rotated BRIEF) algorithm to extract and match geometric features, assisting in cross-checking with the sample database.",
        "Xây dựng kiến trúc lưu trữ có cấu trúc (MySQL) quản lý thông tin các mẫu hiệu đề<br>thuộc các đại triều (Thanh, Minh, Nguyễn), hỗ trợ trích xuất thông tin niên đại và giải nghĩa nhanh chóng": "Building a structured storage architecture (MySQL) to manage information of mark samples belonging to major dynasties (Qing, Ming, Nguyen), supporting rapid extraction of dating and interpretation information.",
        "MarkSense AI là một giải pháp phần mềm được thiết kế để hỗ trợ công tác số hóa di<br>sản. Thay vì tra cứu thủ công qua sách vở, hệ thống cung cấp một công cụ đối chiếu kỹ thuật số trực quan,<br>giúp người dùng dễ dàng tiếp cận và tìm hiểu thông tin lịch sử của gốm sứ cổ truyền.": "MarkSense AI is a software solution designed to support heritage digitization. Instead of manual searching through books, the system provides an intuitive digital cross-referencing tool, making it easy for users to access and learn historical information about traditional ceramics.",
        "Phiên bản": "Version",
        "Phát triển bởi": "Developed by",
        "Kết nối": "Connect",
        "Bạn có câu hỏi hoặc cần hỗ trợ? Đội ngũ chuyên gia của MarkSense AI<br>luôn sẵn sàng.": "Have a question or need support? The MarkSense AI expert team is always ready.",
        "Đường 3/2, Phường Tân An,<br>Ninh Kiều, Cần Thơ, Việt Nam": "3/2 Street, Tan An Ward,<br>Ninh Kieu, Can Tho, Vietnam",
        
        # Guide
        "Bắt đầu quá trình nhận dạng và giám định hiệu đề gốm sứ với 3 bước cơ bản trên hệ thống": "Start the mark recognition and authentication process with 3 basic steps on the system",
        "Nhấp vào \"Sign In\" ở góc trên cùng bên phải. Tạo tài khoản mới hoặc sử dụng hệ thống đăng nhập một chạm<br>(Google/SSO) để cấp quyền truy cập. Việc định danh là bắt buộc nhằm mục đích store personal analysis history<br>nhân.": "Click \"Sign In\" in the top right corner. Create a new account or use the one-tap login system (Google/SSO) to grant access. Identification is mandatory for the purpose of storing personal analysis history.",
        "Tại giao diện trung tâm, tải lên hình ảnh chụp hiệu đề hoặc sử dụng thao tác kéo thả. Nhấp \"Bắt đầu phân<br>credits\" để activate the computer vision AI core to process the image.": "At the central interface, upload a captured mark image or use drag and drop. Click \"Start analysis\" to activate the computer vision AI core to process the image.",
        "Hệ thống sẽ trả về kết quả nhận dạng Hán Nôm, phiên âm, triều đại và mẫu tham chiếu từ kho lưu trữ. Tất cả<br>báo cáo được tự động lưu trong mục \"History\" để tra cứu sau này.": "The system will return the Sino-Nom recognition result, transcription, dynasty, and reference sample from the repository. All reports are automatically saved in the \"History\" section for later retrieval.",
        "Chúng tôi chỉ thu thập dữ liệu định danh ở mức tối thiểu (email) nhằm duy trì phiên đăng<br>nhập hợp lệ. Các hình ảnh tải lên được tiếp nhận và xử lý cục bộ trên hệ thống server.": "We only collect identification data at a minimum level (email) to maintain a valid login session. Uploaded images are received and processed locally on the server system.",
        "danh hoàn toàn (anonymized) nếu được sử dụng như một phần của tập huấn luyện (training set) để cải thiện độ<br>chính xác OCR trong tương lai.": "fully anonymized if used as part of a training set to improve OCR accuracy in the future.",
        "Tất cả phiên truyền tải dữ liệu đều được mã hóa theo chuẩn SSL/TLS. Cơ sở dữ liệu và thư<br>mục hình ảnh của người dùng được Unlimited quyền truy cập bằng kiến trúc bảo mật đa tầng.": "All data transmission sessions are encrypted using the SSL/TLS standard. The database and user image directory have restricted access through a multi-tier security architecture.",
        "Sử dụng hệ thống giải pháp MarkSense AI đồng nghĩa với việc bạn chấp thuận các quy định pháp<br>lý sau.": "Using the MarkSense AI solution system means you agree to the following legal regulations.",
        "tác giám định chuyên môn. MarkSense AI không chịu trách nhiệm đối với bất kỳ quyết định mua bán, giao dịch hay<br>thẩm định giá trị nào dựa trên hệ thống.": "professional authentication work. MarkSense AI is not responsible for any buying, selling, trading, or valuation decisions based on the system.",
        "Người dùng cam kết sở hữu hợp pháp hình ảnh tải lên hệ thống. Bất kỳ khiếu nại bản quyền<br>nào phát sinh từ các mẫu cổ vật số hóa do người dùng tải lên sẽ thuộc trách nhiệm của người đó.": "Users commit to legally owning the images uploaded to the system. Any copyright claims arising from digitized artifact samples uploaded by the user will be their responsibility.",
        "Cấu trúc hệ thống, trọng số mô hình AI, thuật toán xử lý ảnh (Computer Vision), cùng kho<br>dữ liệu tham chiếu là tài sản trí tuệ độc quyền của đội ngũ HieuDe Team.": "The system structure, AI model weights, image processing algorithms (Computer Vision), and reference database are the exclusive intellectual property of the HieuDe Team.",
        
        "Hệ thống hiện cung cấp tính năng tra cứu cơ sở dữ liệu và 5 lượt phân credits đầu<br>tiên miễn phí cho tất cả tài khoản. Với nhu cầu lưu trữ và nhận dạng khối lượng lớn, người dùng có thể tham<br>khảo bảng giá dịch vụ cao cấp.": "The system currently offers database lookup and 5 initial free analysis credits for all accounts. For high-volume storage and recognition needs, users can refer to the premium service pricing.",
        "Lõi OCR của hệ thống có khả năng khôi phục một phần nét mờ dựa trên ngữ cảnh cấu<br>trúc chữ Hán. Tuy nhiên, hình ảnh cần được chụp rõ ràng, đủ ánh sáng, góc chụp vuông góc để tối đa hóa xác<br>suất trùng khớp.": "The system's OCR core has the ability to partially restore blurred strokes based on the structural context of Chinese characters. However, images need to be captured clearly, with sufficient lighting, and at a perpendicular angle to maximize the matching probability.",
        "Toàn bộ tác vụ nhận dạng được ghi nhận và lưu trong bộ nhớ tạm theo phiên làm<br>việc. Chúng tôi đang hoàn thiện cơ sở dữ liệu vĩnh viễn (cùng chức năng xóa thủ công) ở bản cập nhật tiếp": "All recognition tasks are recorded and saved in temporary memory per session. We are finalizing the permanent database (along with manual deletion functionality) in the next update.",
        "Bộ dữ liệu tập trung mạnh nhất vào các mẫu gốm sứ thuộc đại triều nhà Thanh, nhà<br>Minh và nhà Nguyễn. Các niên đại khác (Tống, Nguyên) đang trong quá trình số hóa và credits hợp dần.": "The dataset is heavily focused on ceramic samples from the great dynasties of Qing, Ming, and Nguyen. Other periods (Song, Yuan) are in the process of being digitized and integrated gradually.",
        
        # Payment labels
        "Ngân hàng TMCP<br>Phương Đông (OCB)": "Orient Commercial Joint Stock Bank (OCB)",
        "0đ": "0VND",
        
        # JS values
        "Chưa rõ": "Unknown",
        "Chưa xác định": "Unknown",
        "Đang cập nhật...": "Updating...",
        "Không có mô tả": "No description",
        "Thời kỳ:": "Period:",
        "Đặc điểm:": "Features:",
        "Hiệu đề": "Mark",
        "Gốm sứ": "Ceramics",
        "Không tìm thấy hiệu đề phù hợp.": "No matching marks found.",
        "Không thể truy cập camera. Vui lòng kiểm tra quyền.": "Cannot access camera. Please check permissions.",
        "Server báo lỗi:": "Server error:",
        "Lỗi kết nối — vui lòng thử lại": "Connection error - please try again",
        "Thành công": "Success",
        "Đang chờ": "Pending",
        "Thất bại": "Failed",
        
        "Hệ thống vẫn đang chờ xác nhận từ ngân hàng. Quá trình này có thể mất 1-3 phút. Nếu bạn đã chuyển khoản, vui lòng đợi thêm hoặc thử lại sau nhé.": "The system is still waiting for confirmation from the bank. This process may take 1-3 minutes. If you have transferred, please wait a bit more or try again later.",
        "Lỗi kết nối:": "Connection error:",
        "Hồ sơ của tôi": "My Profile",
        "Lịch sử giao dịch": "Transaction History",
        "Thông báo": "Notification",
        "Trợ lý MarkSense": "MarkSense Assistant",
        "Xin chào! 👋 Mình là trợ lý AI của MarkSense. Bạn cần giúp đỡ về cách dùng quét hiệu đề<br>hay thông tin nâng cấp tài khoản?": "Hello! 👋 I am the MarkSense AI assistant. Do you need help on how to use mark scanning or account upgrade information?",
        "Nhập câu trả lời...": "Type a reply...",
        "Hệ thống đang bận, vui lòng thử lại sau.": "System is busy, please try again later.",
        "Lỗi kết nối. Vui lòng kiểm tra mạng.": "Connection error. Please check your network.",
        
        "Nhận Dạng Hiệu Đề Gốm Sứ<br>Bằng AI": "Ceramic Mark Recognition<br>Using AI",
        "Chọn ảnh từ máy": "Select image from device",
        
        # More fixes
        "Lượt phân credits đầu": "free initial analysis credits",
        "phân credits": "analyze",
        "tích": "analyze", # Be careful, replace specific ones instead. Removed.
    }
    
    for vi, en in replacements.items():
        text = text.replace(vi, en)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)

if __name__ == '__main__':
    fix_all_vietnamese('index.html')
