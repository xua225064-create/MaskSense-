import React from 'react';
import LegalLayout from './LegalLayout';
import { uiText } from '../i18n';

export default function TermsScreen({ setScreen, language }) {
  const L = (en, vi) => uiText(language, en, vi);
  const sections = [
    {
      title: L('Acceptance of Terms', 'Chấp nhận điều khoản'),
      body: L(
        'By accessing or using MarkSense, you agree to these Terms of Service. If you do not agree, please stop using the app and website.',
        'Khi truy cập hoặc sử dụng MarkSense, bạn đồng ý với Điều khoản sử dụng này. Nếu không đồng ý, vui lòng ngừng sử dụng ứng dụng và website.'
      ),
    },
    {
      title: L('Service Description', 'Mô tả dịch vụ'),
      body: L(
        'MarkSense provides AI-assisted ceramic mark recognition, OCR, visual comparison, historical reference search, scan history, account management, support, and credit-based analysis packages.',
        'MarkSense cung cấp nhận diện hiệu đề gốm bằng AI, OCR, so khớp hình ảnh, tra cứu tham khảo lịch sử, lịch sử phân tích, quản lý tài khoản, hỗ trợ và các gói phân tích theo lượt.'
      ),
    },
    {
      title: L('Accounts and Security', 'Tài khoản và bảo mật'),
      body: L(
        'You are responsible for keeping your login information secure and for all activity under your account. You must provide accurate information and notify support if you suspect unauthorized access.',
        'Bạn chịu trách nhiệm bảo mật thông tin đăng nhập và mọi hoạt động trong tài khoản. Bạn cần cung cấp thông tin chính xác và thông báo hỗ trợ nếu nghi ngờ truy cập trái phép.'
      ),
    },
    {
      title: L('Payments and Credits', 'Thanh toán và lượt phân tích'),
      body: L(
        'Paid credits are added after successful payment confirmation. Credits are used for analysis requests and are not redeemable for cash unless required by applicable law or a written refund policy.',
        'Lượt phân tích trả phí được cộng sau khi thanh toán được xác nhận thành công. Lượt dùng cho yêu cầu phân tích và không quy đổi thành tiền mặt trừ khi pháp luật áp dụng hoặc chính sách hoàn tiền bằng văn bản yêu cầu.'
      ),
    },
    {
      title: L('Prohibited Uses', 'Nội dung và hành vi bị cấm'),
      body: L(
        'You must not upload illegal content, infringe intellectual property, attempt to bypass security, overload the service, use the system for fraud, or misrepresent AI results as certified expert appraisal.',
        'Bạn không được tải nội dung trái pháp luật, xâm phạm sở hữu trí tuệ, cố vượt bảo mật, gây quá tải dịch vụ, dùng hệ thống để gian lận hoặc trình bày kết quả AI như giám định chuyên gia đã chứng nhận.'
      ),
    },
    {
      title: L('AI and Research Disclaimer', 'Miễn trừ về AI và tham khảo'),
      body: L(
        'Recognition results are generated from OCR, vision models, machine matching, and reference data. They may contain errors and should be used as research support only. They do not guarantee authenticity, value, age, or legal ownership.',
        'Kết quả nhận diện được tạo từ OCR, mô hình vision, máy học và dữ liệu tham khảo. Kết quả có thể có sai sót và chỉ nên dùng để hỗ trợ nghiên cứu. Kết quả không bảo đảm tính xác thực, giá trị, niên đại hoặc quyền sở hữu pháp lý.'
      ),
    },
    {
      title: L('Limitation of Liability', 'Giới hạn trách nhiệm'),
      body: L(
        'To the maximum extent permitted by law, MarkSense is not liable for indirect loss, business loss, valuation decisions, purchase decisions, or reliance on AI analysis without independent verification.',
        'Trong phạm vi pháp luật cho phép, MarkSense không chịu trách nhiệm cho thiệt hại gián tiếp, thiệt hại kinh doanh, quyết định định giá, quyết định mua bán hoặc việc dựa vào phân tích AI mà không xác minh độc lập.'
      ),
    },
    {
      title: L('Termination', 'Chấm dứt tài khoản'),
      body: L(
        'We may suspend or terminate access if an account violates these Terms, abuses the service, creates security risk, or is required to be restricted by law.',
        'Chúng tôi có thể tạm ngưng hoặc chấm dứt quyền truy cập nếu tài khoản vi phạm Điều khoản, lạm dụng dịch vụ, tạo rủi ro bảo mật hoặc phải bị hạn chế theo yêu cầu pháp luật.'
      ),
    },
    {
      title: L('Contact', 'Liên hệ'),
      body: 'xuatruong30@gmail.com',
    },
  ];

  return (
    <LegalLayout
      title={L('Terms of Service', 'Điều khoản sử dụng')}
      subtitle={L('Last updated: June 15, 2026', 'Cập nhật lần cuối: 15/06/2026')}
      sections={sections}
      setScreen={setScreen}
    />
  );
}
