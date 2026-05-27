import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { apiGetPackages } from '../api';
import { uiText } from '../i18n';

const FALLBACK_PACKAGES = {
  basic: { name: 'Basic Package', credits: 50, amount: 490000 },
  pro: { name: 'Popular Package', credits: 200, amount: 447712 },
  enterprise: { name: 'Professional Package', credits: 99999, amount: 2490000 },
};

function formatVND(value) {
  return `${Number(value || 0).toLocaleString('vi-VN')}đ`;
}

function creditText(pkg, L) {
  if (!pkg) return '...';
  return pkg.credits >= 99999 ? L('Unlimited scans', 'Không giới hạn lượt') : `${pkg.credits} ${L('credits', 'lượt')}`;
}

export default function PricingScreen({ user, credits, setScreen, goCheckout, language }) {
  const L = (en, vi) => uiText(language, en, vi);
  const [packages, setPackages] = useState(FALLBACK_PACKAGES);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState('pro');

  useEffect(() => {
    let alive = true;
    apiGetPackages()
      .then((data) => {
        if (alive && data?.success && data.packages) setPackages(data.packages);
      })
      .catch(() => {})
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, []);

  const selectPackage = () => {
    if (!user) {
      Alert.alert(L('Please sign in', 'Vui lòng đăng nhập'), L('Please sign in to purchase a plan', 'Vui lòng đăng nhập để mua gói'));
      setScreen('Login');
      return;
    }
    goCheckout(selected);
  };

  const selectedPkg = packages[selected] || FALLBACK_PACKAGES[selected];
  const nextText = selected === 'pro'
    ? L('Buy Pro Package', 'Mua gói Pro')
    : L('Buy Enterprise Package', 'Mua gói Enterprise');

  return (
    <View style={s.container}>
      <View style={s.topBar}>
        <TouchableOpacity onPress={() => setScreen('Home')} style={s.iconBtn}>
          <Feather name="x" size={24} color="#9ca3af" />
        </TouchableOpacity>
        <View style={s.creditPill}>
          <Text style={s.creditText}>{credits ?? '--'} {L('credits', 'lượt')}</Text>
        </View>
      </View>

      <View style={s.content}>
        <View style={s.headerBlock}>
          <Text style={s.title}>{L('Get Unlimited Access', 'Mở khóa truy cập')}</Text>
          <Text style={s.subtitle}>{L('Your personal antique mark assistant', 'Trợ lý nhận diện hiệu đề cá nhân')}</Text>

          <View style={s.benefits}>
            <Benefit icon="search" text={L('Unlimited identify & diagnose', 'Nhận diện và phân tích chuyên sâu')} />
            <Benefit icon="cpu" text={L('Multi-pipeline AI support', 'Hỗ trợ AI đa pipeline')} />
            <Benefit icon="clock" text={L('History and report storage', 'Lưu lịch sử và báo cáo')} />
          </View>
        </View>

        {loading && <ActivityIndicator color="#065f46" style={s.loading} />}

        <View style={s.purchaseBlock}>
          <View style={s.plans}>
            <PlanOption
              active={selected === 'pro'}
              label={L('Pro', 'Pro')}
              price={formatVND(packages.pro?.amount)}
              sub={creditText(packages.pro, L)}
              badge={L('Popular', 'Phổ biến')}
              onPress={() => setSelected('pro')}
            />

            <PlanOption
              active={selected === 'enterprise'}
              label={L('Enterprise', 'Enterprise')}
              price={formatVND(packages.enterprise?.amount)}
              sub={creditText(packages.enterprise, L)}
              badge={L('Best offer', 'Tốt nhất')}
              onPress={() => setSelected('enterprise')}
            />
          </View>

          <TouchableOpacity style={s.ctaBtn} onPress={selectPackage} activeOpacity={0.9}>
            <Text style={s.ctaText}>{nextText}</Text>
          </TouchableOpacity>

          <Text style={s.finePrint}>
            {selectedPkg?.credits >= 99999
              ? L('Unlimited recognition credits after payment.', 'Không giới hạn lượt nhận diện sau khi thanh toán.')
              : `${creditText(selectedPkg, L)} ${L('will be added after payment.', 'sẽ được cộng sau khi thanh toán.')}`}
          </Text>

          <View style={s.legalRow}>
            <TouchableOpacity onPress={() => setScreen('Terms')}><Text style={s.legalText}>{L('Terms', 'Điều khoản')}</Text></TouchableOpacity>
            <TouchableOpacity onPress={() => setScreen('Privacy')}><Text style={s.legalText}>{L('Privacy', 'Chính sách')}</Text></TouchableOpacity>
          </View>
        </View>
      </View>
    </View>
  );
}

function Benefit({ icon, text }) {
  return (
    <View style={s.benefitRow}>
      <Feather name={icon} size={28} color="#065f46" style={s.benefitIcon} />
      <Text style={s.benefitText}>{text}</Text>
    </View>
  );
}

function PlanOption({ active, label, price, sub, badge, onPress }) {
  return (
    <TouchableOpacity style={[s.planOption, active && s.planActive]} onPress={onPress} activeOpacity={0.85}>
      <View style={s.planLeft}>
        <Text style={s.planLabel}>{label}</Text>
        {!active && <Text style={s.planMuted}>{sub}</Text>}
      </View>
      <View style={[s.offerBadge, active && s.offerBadgeActive]}>
        <Text style={[s.offerBadgeText, active && s.offerBadgeTextActive]}>{badge}</Text>
      </View>
      <View style={s.planRight}>
        <Text style={s.planPrice}>{price}</Text>
        <Text style={s.planSub}>{sub}</Text>
      </View>
    </TouchableOpacity>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fdfbf7', overflow: 'hidden' },
  topBar: {
    paddingTop: 18,
    paddingHorizontal: 30,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  iconBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f5f5f4',
    borderWidth: 1,
    borderColor: '#eee8df',
  },
  creditPill: {
    minHeight: 36,
    paddingHorizontal: 15,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#ecfdf5',
    borderWidth: 1,
    borderColor: '#bbf7d0',
  },
  creditText: { color: '#065f46', fontSize: 13, fontWeight: '900' },
  content: { flex: 1, paddingTop: 16, paddingBottom: 26, justifyContent: 'space-between' },
  headerBlock: { alignItems: 'stretch' },
  purchaseBlock: { paddingTop: 8 },
  title: {
    color: '#064e3b',
    fontSize: 29,
    lineHeight: 34,
    fontWeight: '900',
    textAlign: 'center',
    marginHorizontal: 26,
  },
  subtitle: {
    color: '#57534e',
    fontSize: 15,
    lineHeight: 20,
    textAlign: 'center',
    marginTop: 7,
    marginBottom: 20,
    paddingHorizontal: 44,
  },
  benefits: { alignSelf: 'center', width: '72%', gap: 11 },
  benefitRow: { flexDirection: 'row', alignItems: 'center' },
  benefitIcon: { width: 40 },
  benefitText: { color: '#064e3b', fontSize: 15, lineHeight: 20, fontWeight: '800', flex: 1 },
  loading: { marginBottom: 12 },
  plans: { marginBottom: 14 },
  planOption: {
    marginHorizontal: 28,
    minHeight: 64,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#eee8df',
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 6,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#064e3b',
    shadowOpacity: 0.05,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  planActive: { borderColor: '#065f46', backgroundColor: '#f0fdfa' },
  planLeft: { flex: 1, paddingRight: 8 },
  planLabel: { color: '#064e3b', fontSize: 17, fontWeight: '900' },
  planMuted: { color: '#9ca3af', fontSize: 11, fontWeight: '700', marginTop: 2 },
  offerBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 13,
    backgroundColor: '#f5f5f4',
    marginRight: 10,
  },
  offerBadgeActive: {
    backgroundColor: '#dc2626',
  },
  offerBadgeText: { color: '#78716c', fontSize: 10, fontWeight: '900' },
  offerBadgeTextActive: { color: '#fff', fontSize: 10, fontWeight: '900' },
  planRight: { alignItems: 'flex-end', minWidth: 104 },
  planPrice: { color: '#064e3b', fontSize: 14, fontWeight: '900' },
  planSub: { color: '#047857', fontSize: 11, lineHeight: 13, fontWeight: '800', marginTop: 2, textAlign: 'right' },
  ctaBtn: {
    marginHorizontal: 28,
    minHeight: 54,
    borderRadius: 27,
    backgroundColor: '#065f46',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 0,
  },
  ctaText: { color: '#fff', fontSize: 18, fontWeight: '900' },
  finePrint: {
    color: '#064e3b',
    fontSize: 11,
    lineHeight: 15,
    fontWeight: '800',
    textAlign: 'center',
    marginTop: 12,
    paddingHorizontal: 26,
  },
  legalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 30,
    marginTop: 16,
  },
  legalText: { color: '#a8a29e', fontSize: 13, fontWeight: '600' },
});
