import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Platform, SafeAreaView, StatusBar } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { LANGUAGES, normalizeLanguage, t } from '../i18n';

const SUPPORTED_LANGUAGES = LANGUAGES.filter((item) => item.id === 'vi' || item.id === 'en');

export default function LanguageScreen({ setScreen, language, setLanguage }) {
  const goBack = () => setScreen('Settings');
  const activeLanguage = normalizeLanguage(language || 'vi');

  const onSelect = (lang) => {
    if (setLanguage) {
      setLanguage(lang);
    }
    goBack();
  };

  return (
    <SafeAreaView style={s.safe}>
      <StatusBar barStyle="dark-content" backgroundColor="#fff" />
      
      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity style={s.backBtn} onPress={goBack} hitSlop={{top: 15, bottom:15, left:15, right:15}}>
          <Feather name="chevron-left" size={28} color="#064e3b" />
        </TouchableOpacity>
        <Text style={s.headerTitle}>{t(activeLanguage, 'language')}</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
        {SUPPORTED_LANGUAGES.map((item, index) => {
          const isSelected = activeLanguage === item.id;
          return (
            <TouchableOpacity 
              key={index} 
              style={[s.langCard, isSelected && s.langCardActive]} 
              activeOpacity={0.7} 
              onPress={() => onSelect(item.id)}
            >
              <Text style={s.flagIcon}>{item.flag}</Text>
              <View style={s.langTextWrap}>
                <Text style={[s.langName, isSelected && s.langNameActive]}>{item.nativeName}</Text>
                <Text style={s.langCode}>{item.code}</Text>
              </View>
              {isSelected && (
                <View style={s.selectedWrap}>
                  <Text style={s.selectedText}>{t(activeLanguage, 'selected')}</Text>
                  <Feather name="check" size={20} color="#059669" />
                </View>
              )}
            </TouchableOpacity>
          );
        })}
        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#fdfbf7', paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0 },
  header: { 
    flexDirection: 'row', alignItems: 'center', 
    paddingHorizontal: 16, paddingTop: 16, paddingBottom: 16,
    backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#f3f4f6'
  },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { flex: 1, textAlign: 'center', fontSize: 20, color: '#064e3b', fontWeight: '700' },
  
  scroll: { paddingHorizontal: 20, paddingTop: 20 },
  
  langCard: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#fff',
    borderWidth: 1, borderColor: '#e5e7eb',
    borderRadius: 20,
    paddingVertical: 18, paddingHorizontal: 20,
    marginBottom: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.03, shadowRadius: 3, elevation: 1
  },
  langCardActive: {
    borderColor: '#059669',
    backgroundColor: '#f0fdf4',
    borderWidth: 2,
    paddingVertical: 17, paddingHorizontal: 19,
  },
  flagIcon: {
    fontSize: 22, marginRight: 16
  },
  langName: {
    fontSize: 16,
    color: '#374151',
    fontWeight: '600'
  },
  langTextWrap: { flex: 1 },
  langCode: { fontSize: 12, color: '#9ca3af', marginTop: 3, fontWeight: '600' },
  langNameActive: {
    color: '#064e3b',
  },
  selectedWrap: { marginLeft: 12, flexDirection: 'row', alignItems: 'center', gap: 6 },
  selectedText: { color: '#059669', fontSize: 11, fontWeight: '800' }
});
