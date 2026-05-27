import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { apiLogin, apiRegister, apiSocialLogin } from '../api';
import { uiText } from '../i18n';

const GOOGLE_CLIENT_ID = '166557696887-000bmp74q6m90gr0sv84ct7e6s21mdq0.apps.googleusercontent.com';

function loadGoogleScript() {
  if (Platform.OS !== 'web') return Promise.resolve();
  if (document.getElementById('google-gsi-script')) return Promise.resolve();

  return new Promise((resolve) => {
    const script = document.createElement('script');
    script.id = 'google-gsi-script';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = resolve;
    document.head.appendChild(script);
  });
}

export default function RegisterScreen({ handleLogin, setScreen, language }) {
  const L = (en, vi) => uiText(language, en, vi);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [showPw2, setShowPw2] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState('');
  const googleClientRef = useRef(null);

  const showAlert = (title, message) => {
    if (Platform.OS === 'web') {
      window.alert(`${title}\n${message}`);
      return;
    }
    Alert.alert(title, message);
  };

  useEffect(() => {
    if (Platform.OS !== 'web') return undefined;

    let timer;
    loadGoogleScript().then(() => {
      timer = setInterval(() => {
        if (window.google?.accounts) {
          clearInterval(timer);
          googleClientRef.current = window.google.accounts.oauth2.initTokenClient({
            client_id: GOOGLE_CLIENT_ID,
            scope: 'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile',
            callback: handleGoogleCallback,
          });
        }
      }, 200);
    });

    return () => {
      if (timer) clearInterval(timer);
    };
  }, []);

  const handleGoogleCallback = async (tokenResponse) => {
    if (!tokenResponse?.access_token) return;
    setSocialLoading('Google');

    try {
      const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
        headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
      });
      const payload = await res.json();
      const data = await apiSocialLogin(payload.email, payload.name, 'Google');

      if (data.success) {
        handleLogin({
          name: payload.name,
          email: payload.email,
          picture: payload.picture,
          token: data.token,
        });
      } else {
        showAlert(L('Notice', 'Thông báo'), data.message || L('Registration failed', 'Đăng ký thất bại'));
      }
    } catch (e) {
      showAlert(L('Error', 'Lỗi'), L('Cannot connect.', 'Không thể kết nối.'));
    } finally {
      setSocialLoading('');
    }
  };

  const doGoogleLogin = () => {
    if (Platform.OS === 'web' && googleClientRef.current) {
      googleClientRef.current.requestAccessToken();
      return;
    }

    showAlert(
      L('Google sign-in', 'Đăng nhập Google'),
      L('Google sign-in is only available on web in this build.', 'Đăng nhập Google chỉ khả dụng trên bản web hiện tại.')
    );
  };

  const doRegister = async () => {
    if (!name || !email || !pw) {
      showAlert(L('Error', 'Lỗi'), L('Please enter all required information', 'Vui lòng nhập đầy đủ thông tin'));
      return;
    }
    if (pw !== pw2) {
      showAlert(L('Error', 'Lỗi'), L('Passwords do not match', 'Mật khẩu không khớp'));
      return;
    }
    if (pw.length < 8) {
      showAlert(L('Error', 'Lỗi'), L('Password must be at least 8 characters', 'Mật khẩu tối thiểu 8 ký tự'));
      return;
    }

    setLoading(true);
    try {
      const data = await apiRegister(email, pw);
      if (data.success) {
        const loginData = await apiLogin(email, pw);
        if (loginData.success) {
          handleLogin({ name: loginData.username || name, email, token: loginData.token });
        } else {
          setScreen('Login');
        }
      } else {
        showAlert(L('Error', 'Lỗi'), data.message || L('Registration failed', 'Đăng ký thất bại'));
      }
    } catch (e) {
      showAlert(L('Error', 'Lỗi'), L('Connection error', 'Lỗi kết nối'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={s.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={s.inner} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        <TouchableOpacity style={s.backBtn} onPress={() => setScreen('Home')}>
          <Feather name="chevron-left" size={20} color="#1c1917" />
        </TouchableOpacity>

        <View style={s.brandBlock}>
          <View style={s.logoMark}>
            <Feather name="layers" size={24} color="#065f46" />
          </View>
          <Text style={s.brand}>MarkSense</Text>
          <Text style={s.title}>{L('Create account', 'Tạo tài khoản')}</Text>
        </View>

        <View style={s.form}>

          <View style={s.field}>
            <Text style={s.label}>{L('FULL NAME', 'HỌ VÀ TÊN')}</Text>
            <View style={s.inputWrap}>
              <Feather name="user" size={18} color="#78716c" />
              <TextInput
                style={s.input}
                placeholder={L('Your name', 'Tên của bạn')}
                placeholderTextColor="#a8a29e"
                value={name}
                onChangeText={setName}
              />
            </View>
          </View>

          <View style={s.field}>
            <Text style={s.label}>EMAIL</Text>
            <View style={s.inputWrap}>
              <Feather name="mail" size={18} color="#78716c" />
              <TextInput
                style={s.input}
                placeholder="name@company.com"
                placeholderTextColor="#a8a29e"
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                keyboardType="email-address"
              />
            </View>
          </View>

          <View style={s.field}>
            <Text style={s.label}>{L('PASSWORD', 'MẬT KHẨU')}</Text>
            <View style={s.inputWrap}>
              <Feather name="lock" size={18} color="#78716c" />
              <TextInput
                style={s.input}
                placeholder={L('Minimum 8 characters', 'Tối thiểu 8 ký tự')}
                placeholderTextColor="#a8a29e"
                value={pw}
                onChangeText={setPw}
                secureTextEntry={!showPw}
              />
              <TouchableOpacity onPress={() => setShowPw((value) => !value)} hitSlop={10}>
                <Feather name={showPw ? 'eye-off' : 'eye'} size={18} color="#78716c" />
              </TouchableOpacity>
            </View>
          </View>

          <View style={s.field}>
            <Text style={s.label}>{L('CONFIRM PASSWORD', 'XÁC NHẬN MẬT KHẨU')}</Text>
            <View style={s.inputWrap}>
              <Feather name="check-circle" size={18} color="#78716c" />
              <TextInput
                style={s.input}
                placeholder={L('Repeat password', 'Nhập lại mật khẩu')}
                placeholderTextColor="#a8a29e"
                value={pw2}
                onChangeText={setPw2}
                secureTextEntry={!showPw2}
              />
              <TouchableOpacity onPress={() => setShowPw2((value) => !value)} hitSlop={10}>
                <Feather name={showPw2 ? 'eye-off' : 'eye'} size={18} color="#78716c" />
              </TouchableOpacity>
            </View>
          </View>

          <TouchableOpacity style={[s.btn, loading && s.disabledBtn]} onPress={doRegister} disabled={loading}>
            {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>{L('Create account', 'Tạo tài khoản')}</Text>}
          </TouchableOpacity>

          <TouchableOpacity style={s.googleBtn} onPress={doGoogleLogin} disabled={!!socialLoading}>
            {socialLoading === 'Google' ? (
              <ActivityIndicator size="small" color="#065f46" />
            ) : (
              <>
                <Text style={s.googleIcon}>G</Text>
                <Text style={s.googleText}>{L('Continue with Google', 'Tiếp tục với Google')}</Text>
              </>
            )}
          </TouchableOpacity>

          <View style={s.switchRow}>
            <Text style={s.switchText}>{L('Already have an account?', 'Đã có tài khoản?')}</Text>
            <TouchableOpacity onPress={() => setScreen('Login')}>
              <Text style={s.switchLink}>{L('Sign in', 'Đăng nhập')}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fdfbf7' },
  inner: { flexGrow: 1, justifyContent: 'center', paddingHorizontal: 24, paddingVertical: 28 },
  backBtn: {
    position: 'absolute',
    top: 22,
    left: 20,
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#eee8df',
    alignItems: 'center',
    justifyContent: 'center',
  },
  brandBlock: { alignItems: 'center', marginBottom: 26 },
  logoMark: {
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: '#ecfdf5',
    borderWidth: 1,
    borderColor: '#bbf7d0',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 14,
  },
  brand: { color: '#065f46', fontSize: 24, fontFamily: 'serif', fontWeight: '900', marginBottom: 12 },
  title: { color: '#1c1917', fontSize: 30, fontWeight: '900' },
  form: { width: '100%', maxWidth: 420, alignSelf: 'center' },
  field: { marginBottom: 14 },
  label: { color: '#57534e', fontSize: 11, fontWeight: '900', letterSpacing: 0.5, marginBottom: 8, marginLeft: 2 },
  inputWrap: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e7e5e4',
    borderRadius: 16,
    paddingHorizontal: 15,
  },
  input: { flex: 1, color: '#1c1917', fontSize: 15, fontWeight: '700', paddingVertical: 15 },
  btn: {
    minHeight: 58,
    borderRadius: 16,
    backgroundColor: '#065f46',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 6,
  },
  disabledBtn: { opacity: 0.72 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '900' },
  googleBtn: {
    minHeight: 54,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#e7e5e4',
    backgroundColor: '#fff',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    marginTop: 12,
  },
  googleIcon: { color: '#4285F4', fontSize: 18, fontWeight: '900' },
  googleText: { color: '#1c1917', fontSize: 14, fontWeight: '900' },
  switchRow: { flexDirection: 'row', justifyContent: 'center', gap: 6, marginTop: 20, flexWrap: 'wrap' },
  switchText: { color: '#78716c', fontSize: 13, fontWeight: '700' },
  switchLink: { color: '#065f46', fontSize: 13, fontWeight: '900' },
});
