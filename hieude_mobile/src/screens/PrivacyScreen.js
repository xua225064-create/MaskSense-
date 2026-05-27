import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Platform, SafeAreaView, StatusBar } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { uiText } from '../i18n';

export default function PrivacyScreen({ setScreen, language }) {
  const L = (en, vi) => uiText(language, en, vi);
  const sections = [
    {
      title: L('1. Information We Collect', '1. Thu thập thông tin'),
      body: L(
        'We may collect images you upload or scan, basic device information, IP address for abuse prevention, and account information such as display name and email when you sign in.',
        'Chúng tôi có thể thu thập ảnh hiệu đề bạn tải lên hoặc quét, thông tin thiết bị, địa chỉ IP để phòng chống lạm dụng và thông tin tài khoản như tên hiển thị, email khi bạn đăng nhập.'
      ),
    },
    {
      title: L('2. How We Use Data', '2. Mục đích sử dụng'),
      body: L(
        'Uploaded images are used to provide recognition and analysis. Account data supports saved history, credits, and account recovery.',
        'Ảnh tải lên được dùng để cung cấp nhận diện và phân tích. Dữ liệu tài khoản phục vụ lưu lịch sử, credits và khôi phục tài khoản.'
      ),
    },
    {
      title: L('3. Security', '3. Bảo mật thông tin'),
      body: L(
        'MarkSense AI uses reasonable security measures to protect user data and manage access to the system.',
        'MarkSense AI áp dụng các biện pháp bảo mật phù hợp để bảo vệ dữ liệu người dùng và quản lý quyền truy cập hệ thống.'
      ),
    },
    {
      title: L('4. Disclosure', '4. Tiết lộ thông tin'),
      body: L(
        'We do not sell personal information. Data may be disclosed only when required by law or valid authority requests.',
        'Chúng tôi không bán thông tin cá nhân. Dữ liệu chỉ có thể được cung cấp khi pháp luật hoặc cơ quan có thẩm quyền yêu cầu.'
      ),
    },
    {
      title: L('5. Your Control', '5. Quyền kiểm soát dữ liệu'),
      body: L(
        'You may manage your account details and request removal of analysis history where supported by the service.',
        'Bạn có thể quản lý thông tin tài khoản và yêu cầu xoá lịch sử phân tích khi dịch vụ hỗ trợ.'
      ),
    },
  ];

  return (
    <SafeAreaView style={s.container}>
      <View style={s.topBar}>
        <TouchableOpacity style={s.backBtn} onPress={() => setScreen('Home')}>
          <Feather name="arrow-left" size={22} color="#1c1917" />
        </TouchableOpacity>
        <Text style={s.headerTitle}>{L('Privacy Policy', 'Chính Sách Bảo Mật')}</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
        <View style={s.contentCard}>
          <Text style={s.title}>{L('Privacy Policy', 'Chính sách Bảo mật')}</Text>
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
