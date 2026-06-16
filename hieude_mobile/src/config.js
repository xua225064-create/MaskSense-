import { Platform } from 'react-native';

// Đối với Android Emulator: dùng 10.0.2.2
// Đối với thiết bị thật: thay bằng IP LAN máy tính (vd: 192.168.1.X)
// Đối với Web: dùng localhost
const DEV_LAN_BASE_URLS = [
  'http://10.0.2.2:8000',
  'http://127.0.0.1:8000',
  'http://10.215.74.132:8000',
  'http://192.168.100.8:8000',
];

const getBaseUrl = () => {
  if (Platform.OS === 'web') return 'http://localhost:8000';
  return DEV_LAN_BASE_URLS[0];
};

export const BASE_URL = getBaseUrl();
export const API_BASE_URLS = Platform.OS === 'web' ? [BASE_URL] : DEV_LAN_BASE_URLS;

// Design tokens aligned with the MarkSense web app.
export const COLORS = {
  paper: '#090d15',
  white: '#f5f5f5',
  navy: '#090d15',
  ink: '#f8fafc',
  ink60: '#cbd5e1',
  ink30: '#94a3b8',
  ink12: '#334155',
  ink06: '#1e293b',
  cobalt: '#f5f5f5',
  cobaltMid: '#d4d4d8',
  cobaltLite: 'rgba(255, 255, 255, 0.08)',
  green: '#4ade80',
  gold: '#fbbf24',
  rust: '#f87171',
  purple: '#f5f5f5',
  purpleLight: '#d4d4d8',
  indigo: '#f5f5f5',
  teal: '#2dd4bf',
  cyan: '#f5f5f5',
  cardBg: 'rgba(15, 23, 42, 0.6)',
  cardBorder: 'rgba(255, 255, 255, 0.08)',
  glassBg: 'rgba(15, 20, 30, 0.65)',
};
