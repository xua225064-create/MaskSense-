import React, { useState, useEffect, useCallback } from 'react';
import { View, StatusBar, StyleSheet } from 'react-native';
import { COLORS } from './src/config';
import { getStoredUser, storeUser, clearUser, apiGetCredits } from './src/api';

import HomeScreen from './src/screens/HomeScreen';
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import LibraryScreen from './src/screens/LibraryScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import PricingScreen from './src/screens/PricingScreen';
import CheckoutScreen from './src/screens/CheckoutScreen';
import AboutScreen from './src/screens/AboutScreen';
import TermsScreen from './src/screens/TermsScreen';
import PrivacyScreen from './src/screens/PrivacyScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import LanguageScreen from './src/screens/LanguageScreen';
import ChatScreen from './src/screens/ChatScreen';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { normalizeLanguage } from './src/i18n';

export default function App() {
  const [screen, setScreen] = useState('Home');
  const [user, setUser] = useState(null);
  const [credits, setCredits] = useState(null);
  const [checkoutPkg, setCheckoutPkg] = useState(null);
  const [language, setLanguage] = useState('vi');

  // Restore session
  useEffect(() => {
    getStoredUser().then((u) => { if (u) { setUser(u); } });
    AsyncStorage.getItem('appLang').then(l => { if (l) setLanguage(normalizeLanguage(l)); });
  }, []);

  // Fetch credits on user change
  useEffect(() => {
    if (user?.token) {
      apiGetCredits(user.token).then((d) => { if (d.success) setCredits(d.credits); }).catch(() => {});
    } else {
      setCredits(null);
    }
  }, [user]);

  const refreshCredits = useCallback(async () => {
    if (!user?.token) return;
    try {
      const d = await apiGetCredits(user.token);
      if (d.success) setCredits(d.credits);
    } catch (e) {}
  }, [user]);

  const handleLogin = async (u) => {
    await storeUser(u);
    setUser(u);
    setScreen('Home');
  };

  const handleLogout = async () => {
    await clearUser();
    setUser(null);
    setCredits(null);
    setScreen('Home');
  };

  const goCheckout = (pkgId) => {
    setCheckoutPkg(pkgId);
    setScreen('Checkout');
  };

  const changeLanguage = async (val) => {
    const normalized = normalizeLanguage(val);
    setLanguage(normalized);
    await AsyncStorage.setItem('appLang', normalized);
  };

  const props = {
    user,
    credits,
    setScreen,
    handleLogin,
    handleLogout,
    refreshCredits,
    goCheckout,
    checkoutPkg,
    language,
    setLanguage: changeLanguage,
    openChat: () => setScreen('Chat'),
  };

  const renderScreen = () => {
    switch (screen) {
      case 'Home':      return <HomeScreen {...props} />;
      case 'Scan':      return <HomeScreen {...props} startScanner />;
      case 'Login':     return <LoginScreen {...props} />;
      case 'Register':  return <RegisterScreen {...props} />;
      case 'History':   return <HistoryScreen {...props} />;
      case 'Library':   return <LibraryScreen {...props} />;
      case 'Profile':   return <ProfileScreen {...props} />;
      case 'Pricing':   return <PricingScreen {...props} />;
      case 'Checkout':  return <CheckoutScreen {...props} />;
      case 'About':     return <AboutScreen {...props} />;
      case 'Terms':     return <TermsScreen {...props} />;
      case 'Privacy':   return <PrivacyScreen {...props} />;
      case 'Settings':  return <SettingsScreen {...props} />;
      case 'Language':  return <LanguageScreen {...props} />;
      case 'Chat':      return <ChatScreen {...props} />;
      default:          return <HomeScreen {...props} />;
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.paper} />
      {renderScreen()}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.paper },
});
