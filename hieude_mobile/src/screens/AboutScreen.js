import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Linking, Platform, Alert, SafeAreaView, StatusBar } from 'react-native';
import { Feather, MaterialCommunityIcons } from '@expo/vector-icons';
import { AppFooter } from '../components/NavHeader';
import { t } from '../i18n';

const LINKS = {
  website: 'https://marksense.ai',
  instagram: 'https://www.instagram.com/marksense.ai',
  facebook: 'https://www.facebook.com/marksense.ai',
  tiktok: 'https://www.tiktok.com/@marksense.ai',
  email: 'mailto:xuatruong30@gmail.com?subject=MarkSense%20AI%20support',
};

const openLink = async (url, label, language) => {
  try {
    if (Platform.OS === 'web' && typeof window !== 'undefined') {
      const opened = window.open(url, '_blank', 'noopener,noreferrer');
      if (!opened) window.location.href = url;
      return;
    }
    const supported = await Linking.canOpenURL(url);
    if (!supported) throw new Error('Unsupported URL');
    await Linking.openURL(url);
  } catch (err) {
    Alert.alert(label || 'Open link', `${t(language, 'cannotOpen')}\n${url}`);
  }
};

const InfoRow = ({ icon, title, subtitle, onPress, external }) => (
  <TouchableOpacity style={s.infoRow} activeOpacity={0.78} onPress={onPress}>
    <View style={s.infoIcon}>
      <Feather name={icon} size={19} color="#065f46" />
    </View>
    <View style={s.infoBody}>
      <Text style={s.infoTitle}>{title}</Text>
      {!!subtitle && <Text style={s.infoSubtitle}>{subtitle}</Text>}
    </View>
    <Feather name={external ? 'external-link' : 'chevron-right'} size={18} color="#9ca3af" />
  </TouchableOpacity>
);

const TeamMember = ({ name, role }) => (
  <View style={s.member}>
    <View style={s.avatar}><Text style={s.avatarText}>{name.slice(0, 1)}</Text></View>
    <View>
      <Text style={s.memberName}>{name}</Text>
      <Text style={s.memberRole}>{role}</Text>
    </View>
  </View>
);

export default function AboutScreen({ setScreen, language }) {
  return (
    <SafeAreaView style={s.safe}>
      <StatusBar barStyle="dark-content" backgroundColor="#f4f9f9" />
      <View style={s.header}>
        <TouchableOpacity style={s.backBtn} onPress={() => setScreen('Settings')} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
          <Feather name="arrow-left" size={24} color="#064e3b" />
        </TouchableOpacity>
        <Text style={s.headerTitle}>{t(language, 'aboutHeader')}</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
        <View style={s.heroCard}>
          <View style={s.logoWrap}>
            <MaterialCommunityIcons name="magnify-scan" size={34} color="#059669" />
          </View>
          <Text style={s.appName}>{t(language, 'appName')}</Text>
          <Text style={s.tagline}>{t(language, 'aboutSubtitle')}</Text>
          <View style={s.versionPill}><Text style={s.versionText}>{t(language, 'aboutVersion')}</Text></View>
        </View>

        <Text style={s.blockHeader}>{t(language, 'aboutWhatItDoes').toUpperCase()}</Text>
        <View style={s.card}>
          <Text style={s.body}>
            {t(language, 'aboutBody')}
          </Text>
          <View style={s.statRow}>
            <View style={s.statBox}>
              <Text style={s.statValue}>OCR</Text>
              <Text style={s.statLabel}>{t(language, 'ocrEvidence')}</Text>
            </View>
            <View style={s.statBox}>
              <Text style={s.statValue}>AI</Text>
              <Text style={s.statLabel}>{t(language, 'aiCrossCheck')}</Text>
            </View>
            <View style={s.statBox}>
              <Text style={s.statValue}>DB</Text>
              <Text style={s.statLabel}>{t(language, 'dataReference')}</Text>
            </View>
          </View>
        </View>

        <Text style={s.blockHeader}>{t(language, 'aboutTeam').toUpperCase()}</Text>
        <View style={s.card}>
          <TeamMember name="HieuDe Team" role={t(language, 'aboutTeamHieuDe')} />
          <TeamMember name="MarkSense AI" role={t(language, 'aboutTeamAi')} />
        </View>

        <Text style={s.blockHeader}>{t(language, 'termsPrivacyTeam').toUpperCase()}</Text>
        <View style={s.card}>
          <InfoRow icon="file-text" title={t(language, 'terms')} subtitle={t(language, 'aboutTermsSub')} onPress={() => setScreen('Terms')} />
          <InfoRow icon="shield" title={t(language, 'privacy')} subtitle={t(language, 'aboutPrivacySub')} onPress={() => setScreen('Privacy')} />
          <InfoRow icon="trash-2" title="Data Deletion" subtitle="Request account and data removal" onPress={() => setScreen('DataDeletion')} />
          <InfoRow icon="help-circle" title="Support" subtitle="FAQ, account, credits, and payment help" onPress={() => setScreen('Support')} />
          <InfoRow icon="mail" title={t(language, 'aboutContact')} subtitle={t(language, 'aboutContactSub')} external onPress={() => openLink(LINKS.email, 'Email', language)} />
          <InfoRow icon="globe" title={t(language, 'aboutWebsite')} subtitle={t(language, 'aboutWebsiteSub')} external onPress={() => openLink(LINKS.website, 'Website', language)} />
        </View>

        <Text style={s.blockHeader}>{t(language, 'aboutFollow').toUpperCase()}</Text>
        <View style={s.socialRow}>
          <TouchableOpacity style={s.socialBtn} onPress={() => openLink(LINKS.instagram, 'Instagram', language)}>
            <Feather name="camera" size={20} color="#1c1917" />
            <Text style={s.socialText}>Instagram</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.socialBtn} onPress={() => openLink(LINKS.facebook, 'Facebook', language)}>
            <Feather name="facebook" size={20} color="#1c1917" />
            <Text style={s.socialText}>Facebook</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.socialBtn} onPress={() => openLink(LINKS.tiktok, 'TikTok', language)}>
            <MaterialCommunityIcons name="music-note" size={21} color="#1c1917" />
            <Text style={s.socialText}>TikTok</Text>
          </TouchableOpacity>
        </View>

        <Text style={s.footerText}>Copyright 2026 MarkSense AI. HieuDe Team.</Text>
      </ScrollView>

      <AppFooter current="Profile" setScreen={setScreen} language={language} />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#f4f9f9', paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0 },
  header: { paddingHorizontal: 20, paddingTop: 16, paddingBottom: 8, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { fontSize: 17, fontWeight: '800', color: '#064e3b' },
  scroll: { paddingHorizontal: 20, paddingTop: 8, paddingBottom: 120 },
  heroCard: { backgroundColor: '#fff', borderRadius: 20, padding: 24, alignItems: 'center', marginBottom: 28, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.04, shadowRadius: 12, elevation: 2 },
  logoWrap: { width: 72, height: 72, borderRadius: 36, backgroundColor: '#d1fae5', justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  appName: { fontSize: 26, fontWeight: '900', color: '#064e3b', marginBottom: 8 },
  tagline: { fontSize: 14, lineHeight: 22, color: '#4b5563', textAlign: 'center' },
  versionPill: { marginTop: 16, backgroundColor: '#f3f4f6', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  versionText: { fontSize: 11, fontWeight: '800', color: '#4b5563' },
  blockHeader: { fontSize: 12, color: '#4b5563', fontWeight: '800', marginBottom: 12, marginLeft: 8, letterSpacing: 1.2 },
  card: { backgroundColor: '#fff', borderRadius: 20, padding: 18, marginBottom: 28, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.03, shadowRadius: 8, elevation: 1 },
  body: { fontSize: 14, color: '#4b5563', lineHeight: 23 },
  statRow: { flexDirection: 'row', gap: 10, marginTop: 18 },
  statBox: { flex: 1, backgroundColor: '#f8fafc', borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  statValue: { fontSize: 15, fontWeight: '900', color: '#065f46' },
  statLabel: { fontSize: 10, fontWeight: '700', color: '#6b7280', marginTop: 4, textAlign: 'center' },
  member: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10 },
  avatar: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#f3f4f6', justifyContent: 'center', alignItems: 'center', marginRight: 14 },
  avatarText: { fontSize: 16, fontWeight: '900', color: '#065f46' },
  memberName: { fontSize: 15, fontWeight: '800', color: '#111827' },
  memberRole: { fontSize: 12, color: '#6b7280', marginTop: 3, maxWidth: 260 },
  infoRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 13, borderBottomWidth: 1, borderBottomColor: '#f3f4f6' },
  infoIcon: { width: 42, height: 42, borderRadius: 21, backgroundColor: '#f0fdf4', justifyContent: 'center', alignItems: 'center', marginRight: 14 },
  infoBody: { flex: 1, paddingRight: 10 },
  infoTitle: { fontSize: 15, fontWeight: '800', color: '#111827' },
  infoSubtitle: { fontSize: 12, color: '#6b7280', marginTop: 3 },
  socialRow: { flexDirection: 'row', gap: 10, marginBottom: 26 },
  socialBtn: { flex: 1, minHeight: 74, backgroundColor: '#fff', borderRadius: 16, justifyContent: 'center', alignItems: 'center', gap: 8, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.03, shadowRadius: 8, elevation: 1 },
  socialText: { fontSize: 11, fontWeight: '800', color: '#1c1917' },
  footerText: { fontSize: 12, color: '#9ca3af', textAlign: 'center', marginBottom: 12 },
});
