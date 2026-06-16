import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Platform, SafeAreaView, StatusBar, Share, Linking, Alert, Image } from 'react-native';
import { Feather, MaterialCommunityIcons, FontAwesome5 } from '@expo/vector-icons';
import { getLanguageLabel, t } from '../i18n';

const SOCIAL_LINKS = {
  instagram: 'https://www.instagram.com/marksense.ai',
  facebook: 'https://www.facebook.com/marksense.ai',
  tiktok: 'https://www.tiktok.com/@marksense.ai',
  website: 'https://marksense.ai',
  email: 'mailto:xuatruong30@gmail.com?subject=MarkSense%20Support',
};

export default function SettingsScreen({ setScreen, language }) {
  const goBack = () => setScreen('Profile');

  const handleLanguage = () => {
    setScreen('Language');
  };

  const handleShare = async () => {
    try {
      const msg = 'Discover ceramic reign marks with MarkSense. AI-assisted OCR, vision analysis, and historical references for collectors and researchers.';
      if (Platform.OS === 'web' && navigator.share) {
        await navigator.share({ title: 'MarkSense', text: msg, url: 'https://marksense.ai' });
      } else {
        await Share.share({ message: msg });
      }
    } catch (error) {
      alert(`MarkSense: https://marksense.ai`);
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
          {iconLib === 'Feather' && <Feather name={iconName} size={20} color={isGreen ? "#f5f5f5" : "#d4d4d8"} />}
          {iconLib === 'MaterialCommunityIcons' && <MaterialCommunityIcons name={iconName} size={22} color={isGreen ? "#f5f5f5" : "#d4d4d8"} />}
          {iconLib === 'FontAwesome5' && <FontAwesome5 name={iconName} size={18} color={isGreen ? "#f5f5f5" : "#d4d4d8"} />}
        </View>
        
        <View style={s.itemContent}>
          <Text style={s.itemTitle}>{title}</Text>
          {subtitle && <Text style={s.itemSubtitle}>{subtitle}</Text>}
        </View>
        
        <View style={s.rightWrap}>
          {rightText && <Text style={s.rightText}>{rightText}</Text>}
          {rightIcon === 'chevron' ? (
             <Feather name="chevron-right" size={18} color="#a1a1aa" />
          ) : rightIcon === 'external' ? (
             <Feather name="external-link" size={18} color="#a1a1aa" />
          ) : null}
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={s.safe}>
      <StatusBar barStyle="light-content" backgroundColor="#080808" />
      
      {/* Header / Back */}
      <View style={s.header}>
        <TouchableOpacity style={s.backBtn} onPress={goBack} hitSlop={{top: 15, bottom:15, left:15, right:15}}>
          <Feather name="arrow-left" size={24} color="#f5f5f5" />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
        
        {/* App Info Badge */}
        <View style={s.appInfoCard}>
          <View style={s.appLogoWrap}>
             <Image source={require('../../assets/brand-mark.png')} style={s.appLogoImage} resizeMode="contain" />
          </View>
          <View>
            <Text style={s.appName}>MarkSense</Text>
            <Text style={s.appVersion}>Ceramic Mark Recognition</Text>
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
            title="Share MarkSense" subtitle="Send the app to another collector or researcher"
            rightIcon="chevron" noBorder
            onPress={handleShare}
          />
        </View>

        <BlockHeader title="LEGAL & SUPPORT" />
        <View style={s.card}>
          <SettItem 
            iconLib="Feather" iconName="shield" bgType="gray"
            title="Privacy Policy" subtitle="Data collection, AI, analytics, and user rights"
            rightIcon="chevron"
            onPress={() => setScreen('Privacy')}
          />
          <SettItem 
            iconLib="Feather" iconName="file-text" bgType="gray"
            title="Terms of Service" subtitle="Usage rules, accounts, payments, and liability"
            rightIcon="chevron"
            onPress={() => setScreen('Terms')}
          />
          <SettItem 
            iconLib="Feather" iconName="trash-2" bgType="gray"
            title="Data Deletion" subtitle="Request account and data deletion"
            rightIcon="chevron"
            onPress={() => setScreen('DataDeletion')}
          />
          <SettItem 
            iconLib="Feather" iconName="help-circle" bgType="gray"
            title="Support" subtitle="FAQ, contact, account, credits, and payment help"
            rightIcon="chevron" onPress={() => setScreen('Support')} noBorder
          />
        </View>

        <BlockHeader title="CONNECT" />
        <View style={s.card}>
          <SettItem 
            iconLib="Feather" iconName="info" bgType="gray"
            title="About MarkSense" subtitle="Team, mission, and app information"
            rightIcon="chevron" onPress={() => setScreen('About')}
          />
          <SettItem 
            iconLib="Feather" iconName="mail" bgType="gray"
            title="Contact" subtitle="xuatruong30@gmail.com"
            rightIcon="external" onPress={() => handleOpenLink(SOCIAL_LINKS.email, 'Email')}
          />
          <SettItem 
            iconLib="Feather" iconName="globe" bgType="gray"
            title="Website" rightIcon="external"
            onPress={() => handleOpenLink(SOCIAL_LINKS.website, 'Website')} noBorder
          />
        </View>

        <View style={{ height: 60 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#080808', paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0 },
  header: { paddingHorizontal: 20, paddingTop: 16, paddingBottom: 8 },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  scroll: { paddingHorizontal: 20, paddingTop: 8 },
  
  appInfoCard: {
    backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 18, paddingHorizontal: 18, paddingVertical: 18,
    flexDirection: 'row', alignItems: 'center', marginBottom: 24, gap: 14,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.12)',
  },
  appLogoWrap: {
    width: 54, height: 54, borderRadius: 27, backgroundColor: 'transparent',
    borderWidth: 0, borderColor: 'transparent', justifyContent: 'center', alignItems: 'center',
    position: 'relative'
  },
  appLogoImage: { width: 54, height: 54 },
  appName: { fontSize: 20, fontWeight: '900', color: '#f5f5f5', marginBottom: 2, letterSpacing: 0.8, textTransform: 'uppercase' },
  appVersion: { fontSize: 13, color: '#a1a1aa', fontWeight: '600' },
  
  blockHeader: { fontSize: 12, color: '#a1a1aa', fontWeight: '800', marginBottom: 12, marginLeft: 8, letterSpacing: 1.2 },
  card: { backgroundColor: 'rgba(15,23,42,0.58)', borderRadius: 20, marginBottom: 28, borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)' },
  
  itemRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 18, paddingHorizontal: 16, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.08)' },
  iconBadge: { width: 44, height: 44, borderRadius: 22, justifyContent: 'center', alignItems: 'center', marginRight: 16 },
  iconBadgeGreen: { backgroundColor: 'rgba(255,255,255,0.12)' },
  iconBadgeGray: { backgroundColor: 'rgba(255,255,255,0.08)' },
  
  itemContent: { flex: 1, paddingRight: 8 },
  itemTitle: { fontSize: 16, color: '#f5f5f5', fontWeight: '700', marginBottom: 2 },
  itemSubtitle: { fontSize: 13, color: '#a1a1aa', fontWeight: '500' },
  
  rightWrap: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  rightText: { fontSize: 14, color: '#f5f5f5', fontWeight: '700' },
});
