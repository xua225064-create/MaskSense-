import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Feather } from '@expo/vector-icons';
import { apiChat } from '../api';
import { normalizeLanguage, uiText } from '../i18n';

const CHAT_HISTORY_KEY = 'marksense_chat_history';
const CHAT_HISTORY_LIMIT = 80;

const quickPrompts = [
  {
    en: 'How do I scan a ceramic mark?',
    vi: 'Cách quét hiệu đề gốm?',
  },
  {
    en: 'How much are the credit plans?',
    vi: 'Các gói lượt giá bao nhiêu?',
  },
  {
    en: 'Why is my result not accurate?',
    vi: 'Vì sao kết quả chưa chính xác?',
  },
];

export default function ChatScreen({ setScreen, language }) {
  const L = (en, vi) => uiText(language, en, vi);
  const lang = normalizeLanguage(language);
  const welcomeText = L(
    'Hello, I am the MarkSense Assistant. I can help with mark scanning, credits, upgrade plans, payments, accounts, and image tips.',
    'Xin chào, tôi là trợ lý MarkSense. Tôi có thể hỗ trợ quét hiệu đề, lượt phân tích, nâng cấp gói, thanh toán, tài khoản và mẹo chụp ảnh.'
  );
  const [messages, setMessages] = useState([{ id: 'welcome', role: 'bot', text: welcomeText }]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);
  const historyLoadedRef = useRef(false);

  const persistMessages = async (items) => {
    const trimmed = items.slice(-CHAT_HISTORY_LIMIT);
    try { await AsyncStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(trimmed)); } catch (e) {}
  };

  useEffect(() => {
    let mounted = true;
    AsyncStorage.getItem(CHAT_HISTORY_KEY)
      .then((stored) => {
        if (!mounted) return;
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed) && parsed.length) {
            setMessages(parsed);
            return;
          }
        }
        setMessages([{ id: 'welcome', role: 'bot', text: welcomeText }]);
      })
      .catch(() => {
        if (mounted) setMessages([{ id: 'welcome', role: 'bot', text: welcomeText }]);
      })
      .finally(() => {
        historyLoadedRef.current = true;
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    setMessages((prev) => {
      if (prev.length === 1 && prev[0].id === 'welcome') return [{ id: 'welcome', role: 'bot', text: welcomeText }];
      return prev;
    });
  }, [welcomeText]);

  useEffect(() => {
    if (!historyLoadedRef.current) return;
    persistMessages(messages);
  }, [messages]);

  const closeChat = async () => {
    await persistMessages(messages);
    setScreen('Home');
  };

  useEffect(() => {
    requestAnimationFrame(() => scrollRef.current?.scrollToEnd({ animated: true }));
  }, [messages, sending]);

  const sendMessage = async (preset) => {
    const msg = String(preset || text || '').trim();
    if (!msg || sending) return;

    const userMessage = { id: `u-${Date.now()}`, role: 'user', text: msg };
    setMessages((prev) => [...prev, userMessage]);
    setText('');
    setSending(true);

    try {
      const data = await apiChat(msg, lang);
      setMessages((prev) => [
        ...prev,
        {
          id: `b-${Date.now()}`,
          role: 'bot',
          text: data.reply || L('System is busy, please try again later.', 'Hệ thống đang bận, vui lòng thử lại sau.'),
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: 'bot',
          text: L('Connection error. Please check your network or backend server.', 'Lỗi kết nối. Vui lòng kiểm tra mạng hoặc server backend.'),
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <KeyboardAvoidingView style={s.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={s.header}>
        <TouchableOpacity style={s.backBtn} onPress={closeChat} activeOpacity={0.8}>
          <Feather name="chevron-left" size={24} color="#1c1917" />
        </TouchableOpacity>
        <View style={s.headerText}>
          <Text style={s.title}>MarkSense Assistant</Text>
          <Text style={s.subtitle}>{L('Scanning, credits, accounts, and image tips', 'Hỗ trợ quét hiệu đề, lượt dùng, tài khoản và ảnh chụp')}</Text>
        </View>
      </View>

      <ScrollView ref={scrollRef} style={s.chat} contentContainerStyle={s.chatContent} keyboardShouldPersistTaps="handled">
        {messages.map((message) => (
          <View key={message.id} style={[s.row, message.role === 'user' ? s.userRow : s.botRow]}>
            {message.role === 'bot' && (
              <View style={s.avatar}>
                <Feather name="message-circle" size={18} color="#065f46" />
              </View>
            )}
            <View style={[s.bubble, message.role === 'user' ? s.userBubble : s.botBubble]}>
              <Text style={[s.bubbleText, message.role === 'user' ? s.userText : s.botText]}>{message.text}</Text>
            </View>
          </View>
        ))}

        {sending && (
          <View style={[s.row, s.botRow]}>
            <View style={s.avatar}>
              <Feather name="message-circle" size={18} color="#065f46" />
            </View>
            <View style={[s.bubble, s.botBubble, s.typingBubble]}>
              <ActivityIndicator size="small" color="#065f46" />
              <Text style={s.typingText}>{L('Typing...', 'Đang trả lời...')}</Text>
            </View>
          </View>
        )}
      </ScrollView>

      <View style={s.quickWrap}>
        {quickPrompts.map((prompt) => (
          <TouchableOpacity key={prompt.en} style={s.quickChip} onPress={() => sendMessage(lang === 'vi' ? prompt.vi : prompt.en)} activeOpacity={0.8}>
            <Text style={s.quickText} numberOfLines={1}>{lang === 'vi' ? prompt.vi : prompt.en}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={s.inputWrap}>
        <TextInput
          style={s.input}
          value={text}
          onChangeText={setText}
          placeholder={L('Type a reply...', 'Nhập câu hỏi...')}
          placeholderTextColor="#a8a29e"
          multiline
          maxLength={600}
          returnKeyType="send"
          onSubmitEditing={() => sendMessage()}
          blurOnSubmit={false}
        />
        <TouchableOpacity
          style={[s.sendBtn, (!text.trim() || sending) && s.sendBtnDisabled]}
          onPress={() => sendMessage()}
          disabled={!text.trim() || sending}
          activeOpacity={0.82}
        >
          <Feather name="send" size={20} color="#fff" />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fdfbf7' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 18,
    paddingTop: 18,
    paddingBottom: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#eee8df',
    backgroundColor: '#fdfbf7',
  },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#f5f5f4', justifyContent: 'center', alignItems: 'center', marginRight: 10 },
  headerText: { flex: 1 },
  title: { fontSize: 21, fontFamily: 'serif', fontWeight: '800', color: '#1c1917' },
  subtitle: { marginTop: 3, fontSize: 12, lineHeight: 17, color: '#78716c', fontWeight: '600' },
  chat: { flex: 1 },
  chatContent: { paddingHorizontal: 18, paddingTop: 18, paddingBottom: 18 },
  row: { flexDirection: 'row', marginBottom: 14, alignItems: 'flex-end' },
  botRow: { justifyContent: 'flex-start' },
  userRow: { justifyContent: 'flex-end' },
  avatar: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: '#ecfdf5',
    borderWidth: 1,
    borderColor: '#bbf7d0',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 9,
  },
  bubble: { maxWidth: '78%', borderRadius: 18, paddingHorizontal: 14, paddingVertical: 11 },
  botBubble: { backgroundColor: '#ffffff', borderBottomLeftRadius: 6, borderWidth: 1, borderColor: '#eee8df' },
  userBubble: { backgroundColor: '#065f46', borderBottomRightRadius: 6 },
  bubbleText: { fontSize: 14, lineHeight: 21 },
  botText: { color: '#44403c' },
  userText: { color: '#ffffff', fontWeight: '600' },
  typingBubble: { flexDirection: 'row', alignItems: 'center', gap: 8, minWidth: 112 },
  typingText: { color: '#78716c', fontSize: 12, fontWeight: '700' },
  quickWrap: {
    maxHeight: 46,
    paddingHorizontal: 16,
    paddingBottom: 8,
    flexDirection: 'row',
    gap: 8,
  },
  quickChip: { flex: 1, height: 36, borderRadius: 18, backgroundColor: '#f5f5f4', borderWidth: 1, borderColor: '#eee8df', justifyContent: 'center', paddingHorizontal: 10 },
  quickText: { color: '#57534e', fontSize: 10, fontWeight: '800', textAlign: 'center' },
  inputWrap: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 10,
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: Platform.OS === 'ios' ? 24 : 18,
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#eee8df',
  },
  input: {
    flex: 1,
    minHeight: 48,
    maxHeight: 112,
    borderRadius: 18,
    backgroundColor: '#f5f5f4',
    paddingHorizontal: 15,
    paddingVertical: 12,
    color: '#1c1917',
    fontSize: 14,
    lineHeight: 20,
  },
  sendBtn: { width: 48, height: 48, borderRadius: 24, backgroundColor: '#065f46', justifyContent: 'center', alignItems: 'center' },
  sendBtnDisabled: { opacity: 0.45 },
});
