import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Platform, SafeAreaView, StatusBar } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { uiText } from '../i18n';

export default function TermsScreen({ setScreen, language }) {
  const L = (en, vi) => uiText(language, en, vi);
  const sections = [
    {
      title: L('1. Acceptance of Terms', '1. Chấp nhận các Điều khoản'),
      body: L(
        'By accessing or using MarkSense AI, you agree to follow these Terms and Conditions. If you do not agree with these terms, please stop using the service.',
        'Bằng việc truy cập hoặc sử dụng ứng dụng MarkSense AI, bạn đồng ý tuân thủ và bị ràng buộc bởi các Điều khoản và Điều kiện sử dụng này. Nếu bạn không đồng ý, vui lòng ngừng sử dụng dịch vụ.'
      ),
    },
    {
      title: L('2. Service Provided', '2. Dịch vụ cung cấp'),
      body: L(
        'MarkSense AI provides AI-assisted recognition, analysis, and research support for antique ceramic reign marks. Results are research references and do not replace final expert appraisal.',
        'MarkSense AI cung cấp nền tảng hỗ trợ nhận dạng, phân tích và giám định hiệu đề gốm sứ cổ bằng AI. Kết quả mang tính tham khảo và không thay thế quyết định giám định cuối cùng của chuyên gia.'
      ),
    },
    {
      title: L('3. Intellectual Property', '3. Quyền sở hữu trí tuệ'),
      body: L(
        'All system content, features, designs, software, analysis data, and images belong to the MarkSense AI Team unless otherwise stated.',
        'Mọi nội dung, tính năng, thiết kế, phần mềm, dữ liệu phân tích và hình ảnh của hệ thống thuộc bản quyền của MarkSense AI Team trừ khi có ghi chú khác.'
      ),
    },
    {
      title: L('4. User Responsibility', '4. Trách nhiệm người dùng'),
      body: L(
        'You agree not to use the system for illegal activity, commercial fraud, or actions that may harm the service.',
        'Bạn cam kết không sử dụng hệ thống vào mục đích trái pháp luật, gian lận thương mại hoặc gây tổn hại đến dịch vụ.'
      ),
    },
    {
      title: L('5. Credits', '5. Điểm tín dụng (Credits)'),
      body: L(
        'Scan credits are used for recognition requests. Purchased credits are added after successful payment and are not redeemable for cash.',
        'Credits được sử dụng cho mỗi lượt nhận dạng. Credits đã mua được cộng sau khi thanh toán thành công và không quy đổi thành tiền mặt.'
      ),
    },
  ];

  return (
    <SafeAreaView style={s.container}>
      <View style={s.topBar}>
        <TouchableOpacity style={s.backBtn} onPress={() => setScreen('Home')}>
          <Feather name="arrow-left" size={22} color="#1c1917" />
        </TouchableOpacity>
        <Text style={s.headerTitle}>{L('Terms of Service', 'Điều Khoản Dịch Vụ')}</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
        <View style={s.contentCard}>
          <Text style={s.title}>{L('Terms of Service', 'Điều khoản Dịch vụ')}</Text>
          <Text style={s.lastUpdate}>{L('Last updated: April 2026', 'Cập nhật lần cuối: Tháng 4/2026')}</Text>
          {sections.map((section) => (
            <View key={section.title}>
              <Text style={s.h2}>{section.title}</Text>
              <Text style={s.body}>{section.body}</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fdfbf7', paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0 },
  topBar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, paddingTop: 20, paddingBottom: 16, borderBottomWidth: 1, borderBottomColor: '#e7e5e4' },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#f5f5f4', justifyContent: 'center', alignItems: 'center' },
  headerTitle: { fontSize: 18, fontWeight: '700', color: '#1c1917' },
  scroll: { padding: 20, paddingBottom: 60 },
  contentCard: { backgroundColor: '#fff', borderColor: '#e7e5e4', borderWidth: 1, borderRadius: 16, padding: 24, marginBottom: 20, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.05, shadowRadius: 10, elevation: 2 },
  title: { fontSize: 24, fontWeight: '800', color: '#1c1917', marginBottom: 8 },
  lastUpdate: { fontSize: 13, color: '#a8a29e', marginBottom: 24, fontStyle: 'italic' },
  h2: { fontSize: 16, fontWeight: '700', color: '#065f46', marginTop: 24, marginBottom: 12 },
  body: { fontSize: 14, color: '#57534e', lineHeight: 24 },
});
