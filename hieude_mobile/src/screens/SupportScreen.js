import React, { useState } from 'react';
import { Alert, Text, TextInput, TouchableOpacity, View } from 'react-native';
import LegalLayout, { legalStyles } from './LegalLayout';
import { apiSendContact } from '../api';
import { uiText } from '../i18n';

export default function SupportScreen({ user, setScreen, language }) {
  const L = (en, vi) => uiText(language, en, vi);
  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [subject, setSubject] = useState('MarkSense support');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  const sections = [
    {
      title: L('Support Contact', 'Liên hệ hỗ trợ'),
      body: [
        'Email: xuatruong30@gmail.com',
        'Phone: +84 85 264 1851',
        'Office: 3/2 Street, Tan An Ward, Ninh Kieu, Can Tho, Vietnam',
      ],
    },
    {
      title: L('Common Help Topics', 'Chủ đề hỗ trợ thường gặp'),
      body: L(
        'We can help with mark scanning, image capture, account access, credits, payments, upgrades, history, library data, and AI result questions.',
        'Chúng tôi hỗ trợ quét hiệu đề, chụp ảnh, truy cập tài khoản, lượt phân tích, thanh toán, nâng cấp, lịch sử, dữ liệu thư viện và câu hỏi về kết quả AI.'
      ),
    },
    {
      title: L('AI Safety Notice', 'Lưu ý an toàn AI'),
      body: L(
        'AI responses and recognition results may be wrong. Do not use MarkSense as the sole source for legal, financial, medical, or high-value purchase decisions.',
        'Câu trả lời AI và kết quả nhận diện có thể sai. Không dùng MarkSense làm nguồn duy nhất cho quyết định pháp lý, tài chính, y tế hoặc mua bán giá trị cao.'
      ),
    },
  ];

  const send = async () => {
    if (!name.trim() || !email.trim() || !message.trim()) {
      Alert.alert(L('Missing information', 'Thiếu thông tin'), L('Please fill name, email, and message.', 'Vui lòng nhập tên, email và nội dung.'));
      return;
    }
    setSending(true);
    try {
      const res = await apiSendContact({ name, email, subject, message });
      if (res?.success) {
        setMessage('');
        Alert.alert(L('Sent', 'Đã gửi'), L('Support request sent successfully.', 'Yêu cầu hỗ trợ đã được gửi.'));
      } else {
        Alert.alert(L('Error', 'Lỗi'), res?.message || L('Could not send request.', 'Không thể gửi yêu cầu.'));
      }
    } catch (e) {
      Alert.alert(L('Error', 'Lỗi'), L('Cannot connect to server.', 'Không thể kết nối máy chủ.'));
    } finally {
      setSending(false);
    }
  };

  return (
    <LegalLayout
      title={L('Support', 'Hỗ trợ')}
      subtitle={L('Get help with MarkSense account, scans, credits, and payments.', 'Nhận hỗ trợ về tài khoản, quét ảnh, lượt phân tích và thanh toán.')}
      sections={sections}
      setScreen={setScreen}
    >
      <View style={legalStyles.card}>
        <Text style={legalStyles.sectionTitle}>{L('Send a message', 'Gửi tin nhắn')}</Text>
        <TextInput style={legalStyles.input} value={name} onChangeText={setName} placeholder={L('Name', 'Tên')} placeholderTextColor="#71717a" />
        <TextInput style={legalStyles.input} value={email} onChangeText={setEmail} placeholder="email@example.com" placeholderTextColor="#71717a" autoCapitalize="none" keyboardType="email-address" />
        <TextInput style={legalStyles.input} value={subject} onChangeText={setSubject} placeholder={L('Subject', 'Chủ đề')} placeholderTextColor="#71717a" />
        <TextInput
          style={[legalStyles.input, legalStyles.textArea]}
          value={message}
          onChangeText={setMessage}
          placeholder={L('How can we help?', 'Bạn cần hỗ trợ gì?')}
          placeholderTextColor="#71717a"
          multiline
        />
        <TouchableOpacity style={legalStyles.actionButton} onPress={send} disabled={sending}>
          <Text style={legalStyles.actionText}>{sending ? L('Sending...', 'Đang gửi...') : L('Send support request', 'Gửi yêu cầu hỗ trợ')}</Text>
        </TouchableOpacity>
      </View>
    </LegalLayout>
  );
}
