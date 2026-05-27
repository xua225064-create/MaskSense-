import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Feather, Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { normalizeLanguage, t, uiText } from '../i18n';

const HEADER_LABELS = {
  en: { credits: 'credits', pro: 'PRO' },
  vi: { credits: 'lượt', pro: 'Nâng cấp' },
  de: { credits: 'Credits', pro: 'PRO' },
  es: { credits: 'creditos', pro: 'PRO' },
  fr: { credits: 'credits', pro: 'PRO' },
  it: { credits: 'crediti', pro: 'PRO' },
  pt: { credits: 'creditos', pro: 'PRO' },
  tr: { credits: 'kredi', pro: 'PRO' },
  ja: { credits: 'クレジット', pro: 'プロ' },
  zh: { credits: '积分', pro: '专业版' },
  ru: { credits: 'кредиты', pro: 'PRO' },
  ar: { credits: 'رصيد', pro: 'احترافي' },
};

export function AppHeader({ setScreen, credits, language }) {
  const hasCredits = credits !== null && credits !== undefined;
  const L = (en, vi) => uiText(language, en, vi);
  const labels = HEADER_LABELS[normalizeLanguage(language)] || HEADER_LABELS.en;

  return (
    <View style={s.dashHeader}>
      <Text style={s.brandSerif}>MarkSense</Text>
      <View style={s.dashHeadRight}>
        <TouchableOpacity onPress={() => setScreen('Library')} style={{marginRight: 16}}>
          <Feather name="search" size={24} color="#1c1917" />
        </TouchableOpacity>
        {hasCredits && (
          <TouchableOpacity style={s.creditPill} onPress={() => setScreen('Pricing')}>
            <Text style={s.creditText}>{credits}</Text>
            <Text style={s.creditLabel}>{labels.credits}</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity style={s.proBtnBig} onPress={() => setScreen('Pricing')}>
          <Text style={s.proTextBig}>{labels.pro}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

export function AppFooter({ current, setScreen, onCenterPress, language }) {
  return (
    <View style={s.bottomNavWrap}>
      <View style={s.bottomNav}>
        <TouchableOpacity style={s.tabItem} onPress={() => setScreen('Home')}>
          <Feather name="home" size={24} color={current === 'Home' ? '#065f46' : '#78716c'} style={s.tabIco} />
          <Text style={[s.tabLbl, current === 'Home' && s.tabActive]} numberOfLines={1}>{t(language, 'home')}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.tabItem} onPress={() => setScreen('Library')}>
          <Ionicons name="copy-outline" size={24} color={current === 'Library' ? '#065f46' : '#78716c'} style={s.tabIco} />
          <Text style={[s.tabLbl, current === 'Library' && s.tabActive]} numberOfLines={1}>{t(language, 'library')}</Text>
        </TouchableOpacity>
        
        <View style={s.centerTabWrap}>
          <View style={s.centerScanWrap}>
            <TouchableOpacity style={s.centerScanBtn} onPress={() => { if(onCenterPress) onCenterPress(); else setScreen('Scan'); }}>
              <Feather name="camera" size={26} color="#fff" />
            </TouchableOpacity>
          </View>
        </View>

        <TouchableOpacity style={s.tabItem} onPress={() => setScreen('History')}>
          <MaterialCommunityIcons name="file-document-edit-outline" size={26} color={current === 'History' ? '#065f46' : '#78716c'} style={s.tabIco} />
          <Text style={[s.tabLbl, current === 'History' && s.tabActive]} numberOfLines={1}>{t(language, 'history')}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.tabItem} onPress={() => setScreen('Profile')}>
          <Feather name="user" size={24} color={current === 'Profile' ? '#065f46' : '#78716c'} style={s.tabIco} />
          <Text style={[s.tabLbl, current === 'Profile' && s.tabActive]} numberOfLines={1}>{t(language, 'account')}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  // HEADER
  dashHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginHorizontal: 20, paddingTop: 20, marginBottom: 20 },
  brandSerif: { fontSize: 22, color: '#065f46', fontFamily: 'serif', fontWeight: '800' },
  dashHeadRight: { flexDirection: 'row', alignItems: 'center' },
  creditPill: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: '#ecfdf5', borderWidth: 1, borderColor: '#bbf7d0', paddingHorizontal: 10, paddingVertical: 7, borderRadius: 999, marginRight: 10 },
  creditText: { color: '#065f46', fontSize: 13, fontWeight: '900' },
  creditLabel: { color: '#047857', fontSize: 10, fontWeight: '800', textTransform: 'uppercase' },
  proBtnBig: { backgroundColor: '#065f46', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 16, shadowColor: '#065f46', shadowOpacity: 0.3, shadowRadius: 6, shadowOffset: {width: 0, height: 2}, elevation: 3 },
  proTextBig: { color: '#fff', fontSize: 13, fontWeight: '900', letterSpacing: 0.5 },

  // BOTTOM NAV
  tabIco: { marginBottom: 4 },
  tabLbl: { fontSize: 10, fontWeight: '900', color: '#a8a29e', textTransform: 'uppercase', letterSpacing: 0.5 },
  tabActive: { color: '#065f46' },
  bottomNavWrap: { position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: 'transparent', paddingHorizontal: 0 },
  bottomNav: {
    backgroundColor: '#ffffff', flexDirection: 'row',
    paddingBottom: 10, paddingTop: 14, paddingHorizontal: 16,
    shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 24, elevation: 20,
    alignItems: 'flex-end',
  },
  tabItem: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  centerTabWrap: { flex: 1, alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 0 },
  centerScanWrap: { width: 86, height: 86, borderRadius: 43, backgroundColor: '#ffffff', justifyContent: 'center', alignItems: 'center', marginTop: -50 },
  centerScanBtn: { backgroundColor: '#065f46', width: 68, height: 68, borderRadius: 34, justifyContent: 'center', alignItems: 'center', elevation: 8, shadowColor: '#065f46', shadowOpacity: 0.5, shadowRadius: 10, shadowOffset: {width: 0, height: 4} }
});
