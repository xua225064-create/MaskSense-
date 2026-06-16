import React from 'react';
import { SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, TouchableOpacity, View, Platform } from 'react-native';
import { Feather } from '@expo/vector-icons';

export default function LegalLayout({ title, subtitle, sections, setScreen, backTo = 'Settings', children }) {
  return (
    <SafeAreaView style={s.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#080808" />
      <View style={s.header}>
        <TouchableOpacity style={s.backBtn} onPress={() => setScreen(backTo)}>
          <Feather name="arrow-left" size={22} color="#f5f5f5" />
        </TouchableOpacity>
        <Text style={s.headerTitle} numberOfLines={1}>{title}</Text>
        <View style={{ width: 42 }} />
      </View>

      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
        <View style={s.hero}>
          <Text style={s.kicker}>MARKSENSE LEGAL</Text>
          <Text style={s.title}>{title}</Text>
          {!!subtitle && <Text style={s.subtitle}>{subtitle}</Text>}
        </View>

        {sections?.map((section, idx) => (
          <View style={s.card} key={`${section.title}-${idx}`}>
            <Text style={s.sectionTitle}>{section.title}</Text>
            {Array.isArray(section.body) ? (
              section.body.map((line, lineIdx) => (
                <Text style={s.body} key={`${section.title}-${lineIdx}`}>{line}</Text>
              ))
            ) : (
              <Text style={s.body}>{section.body}</Text>
            )}
          </View>
        ))}

        {children}
        <Text style={s.footer}>MarkSense - Ceramic Mark Recognition</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#080808', paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 18,
    paddingTop: 14,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  backBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
  },
  headerTitle: { flex: 1, textAlign: 'center', color: '#f5f5f5', fontSize: 16, fontWeight: '800' },
  scroll: { padding: 18, paddingBottom: 42 },
  hero: {
    borderRadius: 22,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.14)',
    backgroundColor: 'rgba(255,255,255,0.055)',
    padding: 22,
    marginBottom: 16,
  },
  kicker: { color: '#a1a1aa', fontSize: 11, fontWeight: '900', letterSpacing: 1.4, marginBottom: 10 },
  title: { color: '#f5f5f5', fontSize: 28, lineHeight: 34, fontWeight: '900', marginBottom: 10 },
  subtitle: { color: '#cbd5e1', fontSize: 14, lineHeight: 22 },
  card: {
    borderRadius: 18,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.11)',
    backgroundColor: 'rgba(15, 23, 42, 0.58)',
    padding: 18,
    marginBottom: 14,
  },
  sectionTitle: { color: '#f5f5f5', fontSize: 16, fontWeight: '850', marginBottom: 10 },
  body: { color: '#cbd5e1', fontSize: 14, lineHeight: 23, marginBottom: 8 },
  footer: { color: '#71717a', textAlign: 'center', fontSize: 12, marginTop: 12 },
  actionButton: {
    minHeight: 52,
    borderRadius: 16,
    backgroundColor: '#f5f5f5',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 18,
    marginTop: 4,
    marginBottom: 14,
  },
  actionText: { color: '#080808', fontSize: 15, fontWeight: '900' },
  input: {
    minHeight: 50,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.14)',
    backgroundColor: 'rgba(255,255,255,0.06)',
    color: '#f5f5f5',
    paddingHorizontal: 14,
    fontSize: 14,
    marginBottom: 12,
  },
  textArea: { minHeight: 120, paddingTop: 14, textAlignVertical: 'top' },
});

export const legalStyles = s;
