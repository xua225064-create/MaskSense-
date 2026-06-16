import React from 'react';
import LegalLayout from './LegalLayout';
import { uiText } from '../i18n';

export default function PrivacyScreen({ setScreen, language }) {
  const L = (en, vi) => uiText(language, en, vi);
  const sections = [
    {
      title: L('Developer Information', 'Thông tin nhà phát triển'),
      body: [
        'MarkSense - Ceramic Mark Recognition',
        'Developer: MarkSense / HieuDe Team',
        'Support email: xuatruong30@gmail.com',
        'Phone: +84 85 264 1851',
        'Office: 3/2 Street, Tan An Ward, Ninh Kieu, Can Tho, Vietnam',
      ],
    },
    {
      title: L('Data We Collect', 'Dữ liệu được thu thập'),
      body: L(
        'We may collect account information such as name, email, login provider, scan credits, payment records, support messages, uploaded mark images, analysis results, device/network metadata needed for security, and app usage events.',
        'Chúng tôi có thể thu thập thông tin tài khoản như tên, email, nhà cung cấp đăng nhập, lượt quét, giao dịch thanh toán, tin nhắn hỗ trợ, ảnh hiệu đề tải lên, kết quả phân tích, thông tin thiết bị/mạng cần cho bảo mật và sự kiện sử dụng ứng dụng.'
      ),
    },
    {
      title: L('How We Use Data', 'Mục đích sử dụng dữ liệu'),
      body: L(
        'Data is used to provide mark recognition, maintain scan history, manage credits and payments, improve recognition quality, prevent abuse, answer support requests, and comply with legal obligations.',
        'Dữ liệu được dùng để nhận diện hiệu đề, lưu lịch sử phân tích, quản lý lượt quét và thanh toán, cải thiện chất lượng nhận diện, phòng chống lạm dụng, phản hồi hỗ trợ và tuân thủ nghĩa vụ pháp lý.'
      ),
    },
    {
      title: L('Third Parties', 'Chia sẻ với bên thứ ba'),
      body: L(
        'We do not sell personal data. Some data may be processed by service providers such as Google Sign-In, AI/vision providers, payment/bank confirmation services, hosting infrastructure, analytics, or email delivery providers when needed to operate the service.',
        'Chúng tôi không bán dữ liệu cá nhân. Một số dữ liệu có thể được xử lý bởi nhà cung cấp dịch vụ như Google Sign-In, nhà cung cấp AI/vision, dịch vụ xác nhận thanh toán/ngân hàng, hạ tầng lưu trữ, phân tích hoặc gửi email khi cần để vận hành dịch vụ.'
      ),
    },
    {
      title: L('Cookies, Analytics, Firebase', 'Cookies, Analytics, Firebase'),
      body: L(
        'The web version may use cookies or local storage for login state and preferences. The mobile app may use local storage for account/session data. Analytics or crash reporting may be used to understand reliability and improve the product.',
        'Phiên bản web có thể dùng cookies hoặc local storage để lưu đăng nhập và tùy chọn. Ứng dụng mobile có thể dùng bộ nhớ cục bộ để lưu tài khoản/phiên đăng nhập. Analytics hoặc crash reporting có thể được dùng để hiểu độ ổn định và cải thiện sản phẩm.'
      ),
    },
    {
      title: L('User Rights', 'Quyền của người dùng'),
      body: L(
        'You may request access, correction, export, or deletion of your account data. You can also stop using the service, revoke third-party login permissions, or contact support for privacy questions.',
        'Bạn có thể yêu cầu truy cập, chỉnh sửa, xuất hoặc xóa dữ liệu tài khoản. Bạn cũng có thể ngừng dùng dịch vụ, thu hồi quyền đăng nhập bên thứ ba hoặc liên hệ hỗ trợ về quyền riêng tư.'
      ),
    },
    {
      title: L('AI Notice', 'Lưu ý về AI'),
      body: L(
        'AI results may be incomplete or inaccurate. MarkSense is a research and reference tool, not a final legal, financial, medical, or professional appraisal. Users are responsible for verifying important conclusions.',
        'Kết quả AI có thể chưa đầy đủ hoặc chưa chính xác. MarkSense là công cụ tham khảo/nghiên cứu, không phải kết luận pháp lý, tài chính, y tế hoặc giám định chuyên môn cuối cùng. Người dùng chịu trách nhiệm xác minh các kết luận quan trọng.'
      ),
    },
    {
      title: L('Contact', 'Liên hệ'),
      body: L(
        'For privacy requests, contact xuatruong30@gmail.com. We will respond as reasonably soon as possible.',
        'Để gửi yêu cầu về quyền riêng tư, liên hệ xuatruong30@gmail.com. Chúng tôi sẽ phản hồi trong thời gian hợp lý.'
      ),
    },
  ];

  return (
    <LegalLayout
      title={L('Privacy Policy', 'Chính sách quyền riêng tư')}
      subtitle={L('Last updated: June 15, 2026', 'Cập nhật lần cuối: 15/06/2026')}
      sections={sections}
      setScreen={setScreen}
    />
  );
}
