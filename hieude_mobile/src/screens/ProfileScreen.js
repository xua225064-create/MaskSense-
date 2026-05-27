import React, { useState } from 'react';
import {
  Image,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Feather, MaterialCommunityIcons } from '@expo/vector-icons';
import { clearUser, storeUser } from '../api';
import AppDialog from '../components/AppDialog';
import { AppFooter } from '../components/NavHeader';
import { uiText } from '../i18n';

export default function ProfileScreen({ user, setScreen, handleLogout, language }) {
  if (!user) {
    setScreen('Login');
    return null;
  }

  const L = (en, vi) => uiText(language, en, vi);
  const [name, setName] = useState(user.name || user.email?.split('@')[0] || L('User', 'Người dùng'));
  const [email, setEmail] = useState(user.email || '');
  const [avatarUri, setAvatarUri] = useState(user.avatar || user.picture || '');
  const [avatarFailed, setAvatarFailed] = useState(false);
  const [dialog, setDialog] = useState(null);

  const closeDialog = () => setDialog(null);
  const showMessage = (variant, title, message) => {
    setDialog({
      variant,
      title,
      message,
      actions: [{ label: L('OK', 'Đã hiểu'), primary: true, onPress: closeDialog }],
    });
  };

  const initials = (name || email || 'U')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
  const showAvatarImage = !!avatarUri && !avatarFailed;

  const pickAvatar = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.85,
      });

      if (!result.canceled && result.assets?.[0]?.uri) {
        setAvatarUri(result.assets[0].uri);
        setAvatarFailed(false);
      }
    } catch (e) {
      showMessage('danger', L('Error', 'Lỗi'), L('Cannot choose avatar image', 'Không thể chọn ảnh đại diện'));
    }
  };

  const handleSave = async () => {
    if (!name.trim()) {
      showMessage('warning', L('Missing name', 'Thiếu tên'), L('Display name cannot be empty', 'Tên hiển thị không được bỏ trống'));
      return;
    }

    await storeUser({ ...user, name, email, avatar: avatarUri || undefined });
    showMessage('success', L('Saved', 'Đã lưu'), L('Account information saved!', 'Thông tin tài khoản đã được lưu!'));
  };

  const doLogout = () => {
    setDialog({
      variant: 'warning',
      title: L('Confirm sign out', 'Xác nhận đăng xuất'),
      message: L('Are you sure you want to sign out of this account?', 'Bạn có chắc chắn muốn đăng xuất khỏi tài khoản này?'),
      actions: [
        { label: L('Cancel', 'Hủy'), onPress: closeDialog },
        {
          label: L('Sign out', 'Đăng xuất'),
          danger: true,
          onPress: async () => {
            closeDialog();
            await clearUser();
            if (handleLogout) handleLogout();
          },
        },
      ],
    });
  };

  return (
    <KeyboardAvoidingView style={s.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <StatusBar barStyle="light-content" backgroundColor="#064e3b" />

      <View style={s.topBg}>
        <View style={s.blob1} />
        <View style={s.blob2} />
      </View>

      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
        <View style={s.headerRow}>
          <View style={{ width: 44 }} />
          <Text style={s.pgTitle}>{L('Profile', 'Hồ sơ')}</Text>
          <TouchableOpacity style={s.settingsBtn} activeOpacity={0.8} onPress={() => setScreen('Settings')}>
            <Feather name="settings" size={24} color="#fff" />
          </TouchableOpacity>
        </View>

        <View style={s.profileCard}>
          <View style={s.avatarWrap}>
            <View style={s.avatarInner}>
              {showAvatarImage ? (
                <Image source={{ uri: avatarUri }} style={s.avatarImage} onError={() => setAvatarFailed(true)} />
              ) : (
                <Text style={s.avatarLetter}>{initials || 'U'}</Text>
              )}
            </View>
            <TouchableOpacity style={s.cameraBadge} activeOpacity={0.8} onPress={pickAvatar}>
              <Feather name="camera" size={14} color="#fff" />
            </TouchableOpacity>
          </View>

          <View style={s.formWrap}>
            <Text style={s.label}>{L('Full name', 'Họ và tên')}</Text>
            <View style={s.inputBox}>
              <Feather name="user" size={18} color="#065f46" style={s.inputIcon} />
              <TextInput
                style={s.input}
                value={name}
                onChangeText={setName}
                placeholder={L('Enter display name', 'Nhập tên hiển thị')}
                placeholderTextColor="#a8a29e"
              />
            </View>

            <Text style={s.label}>{L('Linked email', 'Email liên kết')}</Text>
            <View style={s.inputBox}>
              <Feather name="mail" size={18} color="#065f46" style={s.inputIcon} />
              <TextInput
                style={s.input}
                value={email}
                onChangeText={setEmail}
                placeholder="name@example.com"
                placeholderTextColor="#a8a29e"
                keyboardType="email-address"
                autoCapitalize="none"
              />
            </View>

            <Text style={s.label}>{L('Sign-in method', 'Phương thức đăng nhập')}</Text>
            <View style={[s.inputBox, s.inputBoxDisabled]}>
              <MaterialCommunityIcons name="shield-check-outline" size={18} color="#a8a29e" style={s.inputIcon} />
              <TextInput
                style={[s.input, { color: '#78716c' }]}
                value={user.picture ? 'Google OAuth' : L('Email / password', 'Email / mật khẩu')}
                editable={false}
              />
            </View>

            <TouchableOpacity style={s.saveBtn} activeOpacity={0.8} onPress={handleSave}>
              <Feather name="save" size={18} color="#fff" />
              <Text style={s.saveBtnText}>{L('Save information', 'Lưu thông tin')}</Text>
            </TouchableOpacity>
          </View>
        </View>

        <TouchableOpacity style={s.logoutBtn} activeOpacity={0.8} onPress={doLogout}>
          <Feather name="log-out" size={20} color="#ef4444" />
          <Text style={s.logoutText}>{L('Sign out from this device', 'Đăng xuất khỏi thiết bị')}</Text>
        </TouchableOpacity>

        <Text style={s.version}>MarkSense AI v1.0</Text>
        <View style={{ height: 120 }} />
      </ScrollView>

      <AppFooter current="Profile" setScreen={setScreen} language={language} />
      <AppDialog
        visible={!!dialog}
        title={dialog?.title}
        message={dialog?.message}
        variant={dialog?.variant}
        actions={dialog?.actions}
        onClose={closeDialog}
      />
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  flex: { flex: 1, backgroundColor: '#fdfbf7' },
  topBg: { position: 'absolute', top: 0, left: 0, right: 0, height: 260, backgroundColor: '#064e3b', borderBottomLeftRadius: 40, borderBottomRightRadius: 40, overflow: 'hidden' },
  blob1: { position: 'absolute', top: -50, right: -40, width: 200, height: 200, borderRadius: 100, backgroundColor: 'rgba(255,255,255,0.06)' },
  blob2: { position: 'absolute', top: 120, left: -60, width: 140, height: 140, borderRadius: 70, backgroundColor: 'rgba(255,255,255,0.04)' },
  scroll: { paddingHorizontal: 20, paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight + 20 : 60 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 30, paddingHorizontal: 10 },
  pgTitle: { fontSize: 26, fontFamily: 'serif', color: '#fff', fontWeight: 'bold' },
  settingsBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.15)', justifyContent: 'center', alignItems: 'center' },
  profileCard: { backgroundColor: '#fff', borderRadius: 24, padding: 24, alignItems: 'center', elevation: 8, shadowColor: '#064e3b', shadowOpacity: 0.15, shadowRadius: 20, shadowOffset: { width: 0, height: 10 }, marginBottom: 36 },
  avatarWrap: { position: 'relative', marginBottom: 26, marginTop: -60 },
  avatarInner: { width: 110, height: 110, borderRadius: 55, backgroundColor: '#f0fdf4', justifyContent: 'center', alignItems: 'center', borderWidth: 4, borderColor: '#fff', elevation: 4, shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 8, overflow: 'hidden' },
  avatarLetter: { color: '#065f46', fontSize: 42, fontFamily: 'serif', fontWeight: 'bold' },
  avatarImage: { width: '100%', height: '100%', resizeMode: 'cover' },
  cameraBadge: { position: 'absolute', bottom: 4, right: 4, width: 34, height: 34, borderRadius: 17, backgroundColor: '#065f46', justifyContent: 'center', alignItems: 'center', borderWidth: 2, borderColor: '#fff' },
  formWrap: { width: '100%' },
  label: { fontSize: 12, color: '#78716c', fontWeight: '700', marginBottom: 8, marginLeft: 4, textTransform: 'uppercase', letterSpacing: 0.5 },
  inputBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fdfbf7', borderWidth: 1, borderColor: '#e7e5e4', borderRadius: 14, marginBottom: 20, height: 50 },
  inputBoxDisabled: { backgroundColor: '#f5f5f4', borderColor: '#d6d3d1' },
  inputIcon: { paddingHorizontal: 16 },
  input: { flex: 1, height: '100%', fontSize: 15, color: '#1c1917', fontWeight: '600' },
  saveBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#065f46', borderRadius: 14, paddingVertical: 18, marginTop: 10, gap: 10, elevation: 6, shadowColor: '#065f46', shadowOpacity: 0.3, shadowRadius: 10, shadowOffset: { width: 0, height: 4 } },
  saveBtnText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  logoutBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, padding: 18, backgroundColor: '#fff', borderRadius: 20, borderWidth: 1, borderColor: '#fee2e2', marginBottom: 24, borderStyle: 'dashed' },
  logoutText: { color: '#ef4444', fontSize: 15, fontWeight: '700' },
  version: { textAlign: 'center', color: '#d6d3d1', fontSize: 12, fontWeight: '600' },
});
