import os
import re

def translate_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    for vi, en in replacements.items():
        text = text.replace(vi, en)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)

main_replacements = {
    '"Bạn đã hết lượt phân tích miễn phí."': '"You have run out of free analysis credits."',
    '"Không tìm thấy tệp hình ảnh."': '"Image file not found."',
    '"Định dạng ảnh không được hỗ trợ."': '"Unsupported image format."',
    '"Định dạng ảnh không hợp lệ"': '"Invalid image format"',
    '"Đây không phải ảnh gốm sứ có hiệu đề"': '"This is not a ceramic image with a mark"',
    '"Vui lòng đưa ảnh chân chính của hiệu đề gốm sứ (nằm ở đáy bát/bình/đĩa)"': '"Please provide a genuine image of a ceramic mark (located at the bottom of a bowl/vase/plate)"',
    '"Không đọc được chữ trong ảnh. Thử chụp rõ hơn."': '"Could not read text in the image. Try capturing a clearer photo."',
    '"Ảnh quá mờ hoặc chữ quá nhỏ, không đủ dữ liệu để xác định hiệu đề."': '"The image is too blurry or the text is too small, insufficient data to identify the mark."',
    '"Kết quả hiện tại không đủ dấu hiệu của hiệu đề niên chế (年製/年造). Vui lòng thử ảnh rõ hơn"': '"Current result lacks signs of a reign mark (年製/年造). Please try a clearer image"',
    '"Không đủ bằng chứng để xác định chính xác hiệu đề. Vui lòng thử ảnh rõ hơn hoặc chụp thẳng góc hơn."': '"Insufficient evidence to accurately identify the mark. Please try a clearer image or capture directly from above."',
    '"Ảnh quá mờ, hệ thống chưa đủ chắc chắn để kết luận chính xác hiệu đề."': '"The image is too blurry, the system is not confident enough to accurately conclude the mark."',
    '"Đã lưu thành công vào thư viện"': '"Successfully saved to library"',
    '"Không thể lưu ảnh mẫu."': '"Could not save sample image."',
    '"Không tìm thấy ảnh. Vui lòng thử lại sau."': '"Image not found. Please try again later."',
    '"Thiếu dữ liệu hiệu đề."': '"Missing mark data."',
    '"Không thể lưu mẫu."': '"Could not save sample."',
    '"Tên người dùng đã tồn tại"': '"Username already exists"',
    '"Đăng ký thành công!"': '"Registered successfully!"',
    '"Lỗi hệ thống."': '"System error."',
    '"Sai tài khoản hoặc mật khẩu"': '"Incorrect username or password"',
    '"Tài khoản của bạn đã bị khóa"': '"Your account has been locked"',
    '"Lỗi hệ thống khi xử lý đăng nhập social"': '"System error while processing social login"',
    '"Chưa đăng nhập."': '"Not logged in."',
    '"Gói không hợp lệ"': '"Invalid package"',
    '"Gói không hợp lệ."': '"Invalid package."',
    '"Không thể lưu giao dịch vào CSDL. Vui lòng kiểm tra lại."': '"Could not save transaction to database. Please check again."',
    '"Không tìm thấy"': '"Not found"',
    '"Đang kết nối ngân hàng..."': '"Connecting to bank..."',
    '"Hóa đơn không tồn tại"': '"Invoice does not exist"',
    '"Giả lập thanh toán thành công!"': '"Simulated payment successfully!"',
    '"Lỗi hệ thống khi xử lý"': '"System error while processing"',
    '"Đã thêm hiệu đề mới"': '"Added new mark"',
    '"Lỗi thêm hiệu đề"': '"Error adding mark"',
    '"Đã cập nhật hiệu đề"': '"Updated mark"',
    '"Lỗi cập nhật hiệu đề"': '"Error updating mark"',
    '"Đã xóa hiệu đề"': '"Deleted mark"',
    '"Lỗi xóa hiệu đề"': '"Error deleting mark"',
    '"Đã cập nhật cài đặt"': '"Updated settings"',
    '"Lỗi"': '"Error"',
    '"Đã khóa tài khoản"': '"Locked account"',
    '"Đã mở khóa tài khoản"': '"Unlocked account"',
    '"Đã cập nhật credits"': '"Updated credits"',
    '"Đã reset mật khẩu"': '"Reset password"',
    '"Chưa xác định"': '"Unknown"',
    '"Không rõ"': '"Unknown"',
    '"Đang cập nhật..."': '"Updating..."',
    '"Không tìm thấy trong database. Dịch nghĩa tham khảo từng chữ."': '"Not found in database. Character-by-character translation provided for reference."',
    '"Đăng nhập Google thành công!"': '"Google sign in successful!"',
    '"Đăng nhập Facebook thành công!"': '"Facebook sign in successful!"'
}

if __name__ == '__main__':
    translate_file('main.py', main_replacements)
    print("main.py translated.")
