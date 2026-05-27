import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Platform, SafeAreaView, StatusBar, Share, Linking, Alert } from 'react-native';
import { Feather, MaterialCommunityIcons, FontAwesome5 } from '@expo/vector-icons';
import { getLanguageLabel, t } from '../i18n';

const SOCIAL_LINKS = {
  instagram: 'https://www.instagram.com/marksense.ai',
  facebook: 'https://www.facebook.com/marksense.ai',
  tiktok: 'https://www.tiktok.com/@marksense.ai',
  website: 'https://marksense.ai',
};

export default function SettingsScreen({ setScreen, language }) {
  const goBack = () => setScreen('Profile');

  const handleLanguage = () => {
    setScreen('Language');
  };

  const handleShare = async () => {
    try {
      const msg = 'Discover ancient ceramic marks with MarkSense! The Evergreen Intelligence for art collectors. Check it out at https://marksense.ai';
      if (Platform.OS === 'web' && navigator.share) {
        await navigator.share({ title: 'MarkSense', text: msg, url: 'https://marksense.ai' });
      } else {
        await Share.share({ message: msg });
      }
    } catch (error) {
      alert(`${t(language, 'appName')}: https://marksense.ai`);
    }
  };

  const handleOpenLink = async (url, label) => {
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

  const BlockHeader = ({ title }) => (
    <Text style={s.blockHeader}>{title}</Text>
  );

  const SettItem = ({ iconLib, iconName, bgType, title, subtitle, rightText, rightIcon, noBorder, onPress }) => {
    const isGreen = bgType === 'green';
    return (
      <TouchableOpacity style={[s.itemRow, noBorder && { borderBottomWidth: 0 }]} activeOpacity={0.7} onPress={onPress}>
        <View style={[s.iconBadge, isGreen ? s.iconBadgeGreen : s.iconBadgeGray]}>
          {iconLib === 'Feather' && <Feather name={iconName} size={20} color={isGreen ? "#059669" : "#374151"} />}
          {iconLib === 'MaterialCommunityIcons' && <MaterialCommunityIcons name={iconName} size={22} color={isGreen ? "#059669" : "#374151"} />}
          {iconLib === 'FontAwesome5' && <FontAwesome5 name={iconName} size={18} color={isGreen ? "#059669" : "#374151"} />}
        </View>
        
        <View style={s.itemContent}>
          <Text style={s.itemTitle}>{title}</Text>
          {subtitle && <Text style={s.itemSubtitle}>{subtitle}</Text>}
        </View>
        
        <View style={s.rightWrap}>
          {rightText && <Text style={s.rightText}>{rightText}</Text>}
          {rightIcon === 'chevron' ? (
             <Feather name="chevron-right" size={18} color="#9ca3af" />
          ) : rightIcon === 'external' ? (
             <Feather name="external-link" size={18} color="#9ca3af" />
          ) : null}
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={s.safe}>
      <StatusBar barStyle="dark-content" backgroundColor="#f4f9f9" />
      
      {/* Header / Back */}
      <View style={s.header}>
        <TouchableOpacity style={s.backBtn} onPress={goBack} hitSlop={{top: 15, bottom:15, left:15, right:15}}>
          <Feather name="arrow-left" size={24} color="#064e3b" />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
        
        {/* App Info Badge */}
        <View style={s.appInfoCard}>
          <View style={s.appLogoWrap}>
             <Feather name="box" size={24} color="#059669" />
          </View>
          <View>
            <Text style={s.appName}>MarkSense</Text>
          </View>
        </View>

        <BlockHeader title={t(language, 'preferences').toUpperCase()} />
        <View style={s.card}>
          <SettItem 
            iconLib="MaterialCommunityIcons" iconName="translate" bgType="green"
            title={t(language, 'languageSelection')} subtitle={t(language, 'languageSubtitle')}
            rightText={getLanguageLabel(language)} rightIcon="chevron" noBorder
            onPress={handleLanguage}
          />
        </View>

        <BlockHeader title={t(language, 'socialHub').toUpperCase()} />
        <View style={s.card}>
          <SettItem 
            iconLib="Feather" iconName="share-2" bgType="green"
            title={t(language, 'shareMarkSense')} subtitle={t(language, 'shareSubtitle')}
            rightIcon="chevron" noBorder
            onPress={handleShare}
          />
        </View>

        <BlockHeader title={t(language, 'connectInfo').toUpperCase()} />
        <View style={s.card}>
          <SettItem 
            iconLib="Feather" iconName="camera" bgType="gray"
            title={t(language, 'instagram')} rightIcon="external"
            onPress={() => handleOpenLink(SOCIAL_LINKS.instagram, 'Instagram')}
          />
          <SettItem 
            iconLib="Feather" iconName="globe" bgType="gray"
            title={t(language, 'facebook')} rightIcon="external"
            onPress={() => handleOpenLink(SOCIAL_LINKS.facebook, 'Facebook')}
          />
          <SettItem 
            iconLib="MaterialCommunityIcons" iconName="play-box-multiple-outline" bgType="gray"
            title={t(language, 'tiktok')} rightIcon="external"
            onPress={() => handleOpenLink(SOCIAL_LINKS.tiktok, 'TikTok')}
          />
          <SettItem 
            iconLib="Feather" iconName="info" bgType="gray"
            title={t(language, 'aboutHeader')} subtitle={t(language, 'termsPrivacyTeam')}
            rightIcon="chevron" onPress={() => setScreen('About')} noBorder
          />
        </View>

        <View style={{ height: 60 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#f4f9f9', paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0 },
  header: { paddingHorizontal: 20, paddingTop: 16, paddingBottom: 8 },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  scroll: { paddingHorizontal: 20, paddingTop: 8 },
  
  appInfoCard: {
    backgroundColor: '#fff', borderRadius: 18, paddingHorizontal: 18, paddingVertical: 18,
    flexDirection: 'row', alignItems: 'center', marginBottom: 24, gap: 14,
    shadowColor: '#000', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.035, shadowRadius: 10, elevation: 2,
  },
  appLogoWrap: {
    width: 50, height: 50, borderRadius: 25, backgroundColor: '#ecfdf5',
    borderWidth: 1, borderColor: '#f3f4f6', justifyContent: 'center', alignItems: 'center',
    position: 'relative'
  },
  appName: { fontSize: 20, fontWeight: '800', color: '#064e3b', marginBottom: 0 },
  appVersion: { fontSize: 13, color: '#6b7280', fontWeight: '500' },
  
  blockHeader: { fontSize: 12, color: '#4b5563', fontWeight: '800', marginBottom: 12, marginLeft: 8, letterSpacing: 1.2 },
  card: { backgroundColor: '#fff', borderRadius: 20, marginBottom: 28, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.03, shadowRadius: 8, elevation: 1 },
  
  itemRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 18, paddingHorizontal: 16, borderBottomWidth: 1, borderBottomColor: '#f8fafc' },
  iconBadge: { width: 44, height: 44, borderRadius: 22, justifyContent: 'center', alignItems: 'center', marginRight: 16 },
  iconBadgeGreen: { backgroundColor: '#d1fae5' },
  iconBadgeGray: { backgroundColor: '#f3f4f6' },
  
  itemContent: { flex: 1, paddingRight: 8 },
  itemTitle: { fontSize: 16, color: '#111827', fontWeight: '700', marginBottom: 2 },
  itemSubtitle: { fontSize: 13, color: '#6b7280', fontWeight: '500' },
  
  rightWrap: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  rightText: { fontSize: 14, color: '#059669', fontWeight: '700' },
});
