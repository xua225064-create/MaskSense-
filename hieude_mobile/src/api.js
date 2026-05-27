import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { BASE_URL } from './config';
import fallbackLibrary from '../assets/data/hieu_de_database.json';

const STORAGE_KEY = 'marksense_user';

// ─── Auth helpers ───
export async function getStoredUser() {
  try {
    const val = await AsyncStorage.getItem(STORAGE_KEY);
    if (val) {
      const user = JSON.parse(val);
      if (!user.token) { await AsyncStorage.removeItem(STORAGE_KEY); return null; }
      return user;
    }
  } catch (e) {}
  return null;
}

export async function storeUser(user) {
  try { await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(user)); } catch (e) {}
}

export async function clearUser() {
  try { await AsyncStorage.removeItem(STORAGE_KEY); } catch (e) {}
}

function authHeaders(token) {
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// ─── API calls ───

export async function apiLogin(username, password) {
  const resp = await fetch(`${BASE_URL}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return resp.json();
}

export async function apiRegister(username, password) {
  const resp = await fetch(`${BASE_URL}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return resp.json();
}

export async function apiSocialLogin(email, name, provider) {
  const resp = await fetch(`${BASE_URL}/social-login`, {
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
    formData.append('file', { uri: imageUri, name: `photo.${imageType === 'png' ? 'png' : 'jpg'}`, type: `image/${imageType}` });
  }
  formData.append('mode', 'deep');

  let resp;
  try {
    resp = await fetch(`${BASE_URL}/api/nckh/analyze`, {
      method: 'POST',
      headers: authHeaders(token),
      body: formData,
      signal,
    });
  } catch (e) {
    throw new Error(`Không kết nối được backend tại ${BASE_URL}. Hãy chạy server API rồi thử lại.`);
  }
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
  const resp = await fetch(`${BASE_URL}/api/history`, { headers: authHeaders(token) });
  return resp.json();
}

export async function apiGetLibrary() {
  try {
    const resp = await fetch(`${BASE_URL}/api/library`);
    const data = await resp.json();
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.marks)) return data.marks;
    if (Array.isArray(data?.library)) return data.library;
  } catch (e) {}
  return fallbackLibrary;
}

export async function apiGetCredits(token) {
  const resp = await fetch(`${BASE_URL}/api/credits`, { headers: authHeaders(token) });
  return resp.json();
}

export async function apiGetPackages() {
  const resp = await fetch(`${BASE_URL}/api/v1/packages`);
  return resp.json();
}

export async function apiCreatePayment(packageId, token) {
  const resp = await fetch(`${BASE_URL}/api/v1/payment/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
    body: JSON.stringify({ package: packageId }),
  });
  return resp.json();
}

export async function apiCheckPaymentStatus(paymentId) {
  const resp = await fetch(`${BASE_URL}/api/v1/payment/status/${paymentId}`);
  return resp.json();
}

export async function apiMockPayment(paymentId, token) {
  const resp = await fetch(`${BASE_URL}/api/v1/payment/mock/${paymentId}`, {
    method: 'POST',
    headers: authHeaders(token),
  });
  return resp.json();
}

export async function apiChat(message, language = 'en') {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 12000);
  const resp = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, language }),
    signal: controller.signal,
  });
  clearTimeout(timer);
  return resp.json();
}
