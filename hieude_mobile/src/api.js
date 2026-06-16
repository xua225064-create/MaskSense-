import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { API_BASE_URLS, BASE_URL } from './config';
import fallbackLibrary from '../assets/data/hieu_de_database.json';

const STORAGE_KEY = 'marksense_user';

export async function getStoredUser() {
  try {
    const val = await AsyncStorage.getItem(STORAGE_KEY);
    if (val) {
      const user = JSON.parse(val);
      if (!user.token) {
        await AsyncStorage.removeItem(STORAGE_KEY);
        return null;
      }
      return user;
    }
  } catch (e) {}
  return null;
}

export async function storeUser(user) {
  try {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  } catch (e) {}
}

export async function clearUser() {
  try {
    await AsyncStorage.removeItem(STORAGE_KEY);
  } catch (e) {}
}

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch(path, options = {}) {
  const endpoints = API_BASE_URLS.length ? API_BASE_URLS : [BASE_URL];
  for (const baseUrl of endpoints) {
    const controller = !options.signal ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), 15000) : null;
    try {
      const resp = await fetch(`${baseUrl}${path}`, {
        ...options,
        signal: options.signal || controller?.signal,
      });
      return { resp, baseUrl };
    } catch (e) {
    } finally {
      if (timer) clearTimeout(timer);
    }
  }
  throw new Error(`Không kết nối được backend. Đã thử: ${endpoints.join(', ')}. Hãy đảm bảo điện thoại cùng Wi-Fi và backend đang chạy.`);
}

function absoluteBackendUrl(url, baseUrl) {
  if (!url || typeof url !== 'string') return url;
  if (/^https?:\/\//i.test(url)) return url;
  if (url.startsWith('/')) return `${baseUrl}${url}`;
  return `${baseUrl}/${url}`;
}

export async function apiLogin(username, password) {
  const { resp } = await apiFetch('/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return resp.json();
}

export async function apiRegister(username, password) {
  const { resp } = await apiFetch('/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return resp.json();
}

export async function apiSocialLogin(email, name, provider) {
  const { resp } = await apiFetch('/social-login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, name, provider }),
  });
  return resp.json();
}

export async function apiOcr(imageUri, token, signal) {
  const formData = new FormData();
  const uriParts = imageUri.split('.');
  const fileType = uriParts[uriParts.length - 1] || 'jpg';
  const imageType = fileType === 'png' ? 'png' : 'jpeg';

  if (Platform.OS === 'web') {
    const imageResp = await fetch(imageUri);
    const blob = await imageResp.blob();
    formData.append('file', blob, `photo.${imageType === 'png' ? 'png' : 'jpg'}`);
  } else {
    formData.append('file', {
      uri: imageUri,
      name: `photo.${imageType === 'png' ? 'png' : 'jpg'}`,
      type: `image/${imageType}`,
    });
  }
  formData.append('mode', 'deep');
  formData.append('deep_mode', 'true');

  const { resp } = await apiFetch('/api/nckh/analyze', {
    method: 'POST',
    headers: authHeaders(token),
    body: formData,
    signal,
  });

  const status = resp.status;
  const text = await resp.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (e) {
    data = {
      success: false,
      message: text || `Server returned HTTP ${status}`,
    };
  }
  return { status, data };
}

export async function apiGetHistory(token) {
  const { resp } = await apiFetch(`/api/history?t=${Date.now()}`, {
    headers: {
      ...authHeaders(token),
      Accept: 'application/json',
      'Cache-Control': 'no-cache',
    },
    cache: 'no-store',
  });
  const text = await resp.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (e) {
    return { success: false, history: [], message: 'History API did not return JSON.' };
  }
  if (Array.isArray(data)) return { success: true, history: data };
  if (Array.isArray(data?.history)) return data;
  if (Array.isArray(data?.items)) return { ...data, success: data.success !== false, history: data.items };
  if (Array.isArray(data?.data)) return { ...data, success: data.success !== false, history: data.data };
  return { ...data, history: [] };
}

export async function apiGetLibrary() {
  try {
    const { resp } = await apiFetch(`/api/library?t=${Date.now()}`, {
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
        'Cache-Control': 'no-cache',
      },
    });
    const data = await resp.json();
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.marks)) return data.marks;
    if (Array.isArray(data?.library)) return data.library;
  } catch (e) {}
  return fallbackLibrary;
}

export async function apiGetCredits(token) {
  const { resp } = await apiFetch('/api/credits', { headers: authHeaders(token) });
  return resp.json();
}

export async function apiGetPackages() {
  const { resp } = await apiFetch('/api/v1/packages');
  return resp.json();
}

export async function apiCreatePayment(packageId, token, paymentMethod = 'bank') {
  const { resp, baseUrl } = await apiFetch('/api/v1/payment/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
    body: JSON.stringify({ package: packageId, payment_method: paymentMethod }),
  });
  const data = await resp.json();
  if (!data?.success) return data;
  return {
    ...data,
    qr_url: absoluteBackendUrl(data.qr_url || data.vietqr_url, baseUrl),
    vietqr_url: absoluteBackendUrl(data.vietqr_url, baseUrl),
  };
}

export async function apiCheckPaymentStatus(paymentId) {
  const { resp } = await apiFetch(`/api/v1/payment/status/${paymentId}`);
  return resp.json();
}

export async function apiMockPayment(paymentId, token) {
  const { resp } = await apiFetch(`/api/v1/payment/mock/${paymentId}`, {
    method: 'POST',
    headers: authHeaders(token),
  });
  return resp.json();
}

export async function apiChat(message, language = 'en') {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 12000);
  const { resp } = await apiFetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, language }),
    signal: controller.signal,
  });
  clearTimeout(timer);
  return resp.json();
}

export async function apiSendContact({ name, email, subject, message }) {
  const { resp } = await apiFetch('/contact/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, subject, message }),
  });
  return resp.json();
}
