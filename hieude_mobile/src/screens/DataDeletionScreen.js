import React from 'react';
import { Linking, TouchableOpacity, Text } from 'react-native';
import LegalLayout, { legalStyles } from './LegalLayout';
import { uiText } from '../i18n';

export default function DataDeletionScreen({ setScreen, language }) {
  const L = (en, vi) => uiText(language, en, vi);
  const sections = [
    {
      title: L('How to Request Deletion', 'Cách yêu cầu xóa dữ liệu'),
      body: L(
        'You can request account and data deletion by contacting support at xuatruong30@gmail.com from the email connected to your account.',
        'Bạn có thể yêu cầu xóa tài khoản và dữ liệu bằng cách liên hệ xuatruong30@gmail.com từ email đang liên kết với tài khoản.'
      ),
    },
    {
      title: L('What Will Be Deleted', 'Dữ liệu sẽ được xóa'),
      body: L(
        'We will delete or anonymize account profile data, scan history, uploaded analysis images where still stored, AI analysis reports, support records tied directly to the account, and payment metadata where deletion is legally allowed.',
        'Chúng tôi sẽ xóa hoặc ẩn danh dữ liệu hồ sơ tài khoản, lịch sử quét, ảnh phân tích đã tải lên nếu còn lưu, báo cáo AI, hồ sơ hỗ trợ gắn trực tiếp với tài khoản và metadata thanh toán trong phạm vi pháp luật cho phép.'
      ),
    },
    {
      title: L('Retention Period', 'Thời hạn xử lý'),
      body: L(
        'After verifying the request, deletion is normally completed within 30 days. Some financial, security, or legal records may be retained longer if required by law.',
        'Sau khi xác minh yêu cầu, việc xóa thường được hoàn tất trong vòng 30 ngày. Một số hồ sơ tài chính, bảo mật hoặc pháp lý có thể được lưu lâu hơn nếu pháp luật yêu cầu.'
      ),
    },
    {
      title: L('Google, Facebook, Apple Sign-In', 'Đăng nhập Google, Facebook, Apple'),
      body: L(
        'If you use a third-party sign-in provider, you may also revoke MarkSense access from that provider account settings.',
        'Nếu bạn dùng nhà cung cấp đăng nhập bên thứ ba, bạn cũng có thể thu hồi quyền truy cập MarkSense trong cài đặt tài khoản của nhà cung cấp đó.'
      ),
    },
  ];

  const emailSupport = () => {
    Linking.openURL('mailto:xuatruong30@gmail.com?subject=MarkSense%20Data%20Deletion%20Request');
  };

  return (
    <LegalLayout
      title={L('Data Deletion Policy', 'Chính sách xóa dữ liệu')}
      subtitle={L('Request deletion of your account and related personal data.', 'Yêu cầu xóa tài khoản và dữ liệu cá nhân liên quan.')}
      sections={sections}
      setScreen={setScreen}
    >
      <TouchableOpacity style={legalStyles.actionButton} onPress={emailSupport}>
        <Text style={legalStyles.actionText}>{L('Email deletion request', 'Gửi email yêu cầu xóa')}</Text>
      </TouchableOpacity>
    </LegalLayout>
  );
}
