import React, { useEffect, useRef, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Image, Alert, ActivityIndicator, ScrollView } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { apiCheckPaymentStatus, apiCreatePayment, apiGetPackages, apiMockPayment } from '../api';
import { uiText } from '../i18n';
import AppDialog from '../components/AppDialog';

const FALLBACK_PACKAGES = {
  basic: { name: 'Basic Package', credits: 50, amount: 490000 },
  pro: { name: 'Popular Package', credits: 200, amount: 447712 },
  enterprise: { name: 'Professional Package', credits: 99999, amount: 2490000 },
};

function formatVND(value) {
  return `${Number(value || 0).toLocaleString('vi-VN')} VND`;
}

function scanText(pkg, L) {
  if (!pkg) return '...';
  return pkg.credits >= 99999 ? L('Unlimited scans', 'Không giới hạn lượt') : `${pkg.credits} ${L('scans', 'lượt')}`;
}

export default function CheckoutScreen({ user, credits, setScreen, checkoutPkg, refreshCredits, language }) {
  const L = (en, vi) => uiText(language, en, vi);
  const [step, setStep] = useState(2);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [packages, setPackages] = useState(FALLBACK_PACKAGES);
  const [paymentData, setPaymentData] = useState(null);
  const [successDialog, setSuccessDialog] = useState(false);
  const intervalRef = useRef(null);

  const pkgId = checkoutPkg || 'pro';
  const pkg = packages[pkgId] || FALLBACK_PACKAGES.pro;

  useEffect(() => {
    let alive = true;
    apiGetPackages()
      .then((data) => {
        if (alive && data?.success && data.packages) setPackages(data.packages);
      })
      .catch(() => {});
    return () => {
      alive = false;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleCompleted = async () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    await refreshCredits?.();
    setSuccessDialog(true);
  };

  const closeSuccessDialog = () => {
    setSuccessDialog(false);
    setScreen('Home');
  };

  const checkStatus = async (paymentId, manual = false) => {
    try {
      if (manual) setChecking(true);
      const data = await apiCheckPaymentStatus(paymentId);
      if (data.status === 'completed') {
        await handleCompleted();
      } else if (manual) {
        Alert.alert(
          L('Payment not received yet', 'Chưa nhận được thanh toán'),
          data.message || L('The system is still waiting for bank confirmation. Please wait 1-3 minutes after transferring.', 'Hệ thống vẫn đang chờ xác nhận từ ngân hàng. Sau khi chuyển khoản, vui lòng đợi 1-3 phút.')
        );
      }
    } catch (e) {
      if (manual) Alert.alert(L('Error', 'Lỗi'), L('Connection error when checking status.', 'Lỗi kết nối khi kiểm tra trạng thái.'));
    } finally {
      if (manual) setChecking(false);
    }
  };

  const confirmPayment = async () => {
    if (!user?.token) {
      Alert.alert(L('Please sign in', 'Vui lòng đăng nhập'), L('Please sign in and select a plan', 'Vui lòng đăng nhập và chọn gói'));
      setScreen('Login');
      return;
    }
    setLoading(true);
    try {
      const data = await apiCreatePayment(pkgId, user.token);
      if (data.success) {
        setPaymentData(data);
        setStep(3);
        if (intervalRef.current) clearInterval(intervalRef.current);
        intervalRef.current = setInterval(() => checkStatus(data.payment_id), 5000);
      } else {
        Alert.alert(L('Error', 'Lỗi'), data.message || data.error || L('Payment failed.', 'Tạo thanh toán thất bại.'));
      }
    } catch (e) {
      Alert.alert(L('Error', 'Lỗi'), L('Cannot connect to server.', 'Không thể kết nối máy chủ.'));
    } finally {
      setLoading(false);
    }
  };

  const simulatePayment = async () => {
    if (!paymentData || !user?.token) return;
    try {
      setChecking(true);
      const data = await apiMockPayment(paymentData.payment_id, user.token);
      if (data.status === 'completed') {
        await handleCompleted();
      } else {
        await checkStatus(paymentData.payment_id, true);
      }
    } catch (e) {
      Alert.alert(L('Error', 'Lỗi'), L('Cannot simulate payment.', 'Không thể giả lập thanh toán.'));
    } finally {
      setChecking(false);
    }
  };

  const backToMethod = () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    setStep(2);
  };

  return (
    <View style={s.container}>
      <View style={s.topBar}>
        <TouchableOpacity onPress={() => (step === 2 ? setScreen('Pricing') : backToMethod())} style={s.backBtn}>
          <Feather name="chevron-left" size={22} color="#1c1917" />
          <Text style={s.backText}>{L('Back', 'Trở về')}</Text>
        </TouchableOpacity>
        <Text style={s.creditText}>{credits ?? '--'} {L('credits', 'lượt')}</Text>
      </View>

      <ScrollView
        style={s.bodyScroll}
        contentContainerStyle={s.body}
        showsVerticalScrollIndicator={false}
      >
        <TouchableOpacity onPress={() => setScreen('Pricing')} activeOpacity={0.8}>
          <Text style={s.kicker}>{L('Payment Processing System', 'Hệ thống xử lý thanh toán')}</Text>
          <Text style={s.title}>{L('Payment Method', 'Phương thức thanh toán')}</Text>
          <View style={s.titleLine} />
        </TouchableOpacity>

        {step === 2 && (
          <View style={s.panel}>
            <CornerMarks />
            <View style={s.pkgSummary}>
              <Text style={s.pkgName}>{pkg.name || FALLBACK_PACKAGES[pkgId]?.name}</Text>
              <Text style={s.pkgPrice}>{formatVND(pkg.amount)}</Text>
              <Text style={s.pkgDesc}>{scanText(pkg, L)}</Text>
            </View>

            <PaymentOption
              active
              title={L('Chuyển khoản ngân hàng', 'Chuyển khoản ngân hàng')}
              subtitle={L('Quét mã VietQR hoặc chuyển khoản 24/7', 'Quét mã VietQR hoặc chuyển khoản 24/7')}
              icon="grid"
            />
            <PaymentOption
              title={L('Ví điện tử MoMo', 'Ví điện tử MoMo')}
              subtitle={L('Thanh toán nhanh chóng qua ứng dụng MoMo', 'Thanh toán nhanh chóng qua ứng dụng MoMo')}
              icon="credit-card"
              disabled
            />
            <PaymentOption
              title={L('ATM / Internet Banking', 'ATM / Internet Banking')}
              subtitle={L('Thanh toán qua thẻ ATM nội địa', 'Thanh toán qua thẻ ATM nội địa')}
              icon="briefcase"
              disabled
            />

            <TouchableOpacity style={[s.continueBtn, loading && s.disabledBtn]} onPress={confirmPayment} disabled={loading}>
              {loading ? <ActivityIndicator color="#fff" /> : (
                <>
                  <Text style={s.continueText}>{L('Tiếp tục thanh toán', 'Tiếp tục thanh toán')}</Text>
                  <Feather name="arrow-right" size={18} color="#fff" />
                </>
              )}
            </TouchableOpacity>

          </View>
        )}

        {step === 3 && paymentData && (
          <View style={s.qrPanel}>
            <CornerMarks />
            <Text style={s.awaiting}>{L('AWAITING PAYMENT...', 'ĐANG CHỜ THANH TOÁN...')}</Text>
            <Text style={s.refText}>REF: #{paymentData.hex_id || paymentData.payment_id}</Text>

            <View style={s.qrBox}>
              <Image source={{ uri: paymentData.qr_url }} style={s.qrImg} resizeMode="contain" />
            </View>
            <Text style={s.verified}>VERIFIED BY SEPAY</Text>

            <InfoBlock label={L('PAYMENT AMOUNT', 'SỐ TIỀN')} value={formatVND(paymentData.amount)} highlight />
            <View style={s.twoCols}>
              <InfoBlock label={L('ACCOUNT HOLDER', 'CHỦ TÀI KHOẢN')} value="TRUONG XUA" />
              <InfoBlock label={L('ACCOUNT NUMBER', 'SỐ TÀI KHOẢN')} value="0852641851" mono />
            </View>
            <InfoBlock label={L('BENEFICIARY BANK', 'NGÂN HÀNG')} value="Orient Commercial Joint Stock Bank (OCB)" />

            <View style={s.transferBox}>
              <Text style={s.transferLabel}>{L('TRANSFER CONTENT', 'NỘI DUNG CHUYỂN KHOẢN')}</Text>
              <Text style={s.transferValue}>{paymentData.content}</Text>
            </View>

            <TouchableOpacity style={[s.confirmBtn, checking && s.disabledBtn]} onPress={() => checkStatus(paymentData.payment_id, true)} disabled={checking}>
              {checking ? <ActivityIndicator color="#fff" /> : <Text style={s.confirmText}>{L('CONFIRM TRANSFER', 'TÔI ĐÃ CHUYỂN KHOẢN')}</Text>}
            </TouchableOpacity>

            <TouchableOpacity style={s.devBtn} onPress={simulatePayment}>
              <Text style={s.devText}>{L('(DEV) SIMULATE RECEIVING MONEY', '(DEV) GIẢ LẬP NHẬN TIỀN')}</Text>
            </TouchableOpacity>

            <TouchableOpacity style={s.methodBackBtn} onPress={backToMethod}>
              <Feather name="chevron-left" size={14} color="#78716c" />
              <Text style={s.methodBackText}>{L('BACK TO CHOOSE METHOD', 'QUAY LẠI CHỌN PHƯƠNG THỨC')}</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>

      <AppDialog
        visible={successDialog}
        variant="success"
        title={L('Payment successful!', 'Thanh toán thành công!')}
        message={L('Credits have been added to your account.', 'Lượt phân tích đã được cộng vào tài khoản.')}
        onClose={closeSuccessDialog}
        actions={[
          { label: 'OK', primary: true, onPress: closeSuccessDialog },
        ]}
      />
    </View>
  );
}

function CornerMarks() {
  return null;
}

function PaymentOption({ title, subtitle, icon, active, disabled }) {
  return (
    <View style={[s.payOption, active && s.payOptionActive, disabled && s.payOptionDisabled]}>
      {active && (
        <View style={s.recommendBadge}>
          <Text style={s.recommendText}>KHUYÊN DÙNG</Text>
        </View>
      )}
      <View style={s.payLeft}>
        <View style={[s.payIcon, active && s.payIconActive]}>
          <Feather name={icon} size={18} color={active ? '#065f46' : '#a8a29e'} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={s.payTitle}>{title}</Text>
          <Text style={s.paySub}>{subtitle}</Text>
        </View>
      </View>
      <View style={[s.radio, active && s.radioActive]}>{active && <View style={s.radioDot} />}</View>
    </View>
  );
}

function InfoBlock({ label, value, highlight, mono }) {
  return (
    <View style={s.infoBlock}>
      <Text style={s.infoLabel}>{label}</Text>
      <Text style={[s.infoValue, highlight && s.infoHighlight, mono && s.mono]}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fdfbf7' },
  topBar: { paddingHorizontal: 18, paddingTop: 22, paddingBottom: 2, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  backBtn: { height: 38, paddingHorizontal: 11, borderRadius: 19, backgroundColor: '#f5f5f4', flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#eee8df' },
  backText: { color: '#1c1917', fontSize: 13, fontWeight: '800', marginLeft: 2 },
  creditText: { color: '#065f46', fontSize: 12, fontWeight: '800', backgroundColor: '#ecfdf5', borderWidth: 1, borderColor: '#bbf7d0', paddingHorizontal: 11, paddingVertical: 7, borderRadius: 15, overflow: 'hidden' },
  bodyScroll: { flex: 1 },
  body: { paddingHorizontal: 20, paddingBottom: 12, justifyContent: 'flex-start' },
  kicker: { color: '#065f46', fontSize: 10, letterSpacing: 1.6, fontWeight: '900', textAlign: 'center', textTransform: 'uppercase', marginTop: 4, marginBottom: 4 },
  title: { color: '#1c1917', fontSize: 25, fontWeight: '900', textAlign: 'center', fontFamily: 'serif' },
  titleLine: { width: 52, height: 3, backgroundColor: '#065f46', alignSelf: 'center', marginTop: 8, marginBottom: 12, borderRadius: 2 },
  panel: { position: 'relative', backgroundColor: 'transparent', borderWidth: 0, padding: 0, shadowOpacity: 0, elevation: 0 },
  corner: { position: 'absolute', width: 7, height: 7, backgroundColor: '#065f46' },
  cornerTL: { top: -1, left: -1 },
  cornerTR: { top: -1, right: -1 },
  cornerBL: { bottom: -1, left: -1 },
  cornerBR: { bottom: -1, right: -1 },
  pkgSummary: { alignItems: 'center', paddingBottom: 14, marginBottom: 14, borderBottomWidth: 1, borderBottomColor: '#eee8df' },
  pkgName: { color: '#1c1917', fontSize: 15, fontWeight: '800', marginBottom: 4 },
  pkgPrice: { color: '#065f46', fontSize: 28, fontWeight: '900' },
  pkgDesc: { color: '#78716c', fontSize: 12, marginTop: 2 },
  payOption: {
    minHeight: 70,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 17,
    borderWidth: 1,
    borderColor: '#eee8df',
    backgroundColor: '#fff',
    borderRadius: 5,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: '#1c1917',
    shadowOpacity: 0.07,
    shadowRadius: 9,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  payOptionActive: { borderColor: '#0f766e', backgroundColor: '#f2fffb', shadowOpacity: 0.04 },
  payOptionDisabled: { backgroundColor: '#fff', borderColor: '#f0ede7', shadowOpacity: 0.05 },
  recommendBadge: { position: 'absolute', top: -7, right: 10, backgroundColor: '#065f46', paddingHorizontal: 7, paddingVertical: 2, borderRadius: 6 },
  recommendText: { color: '#fff', fontSize: 6, fontWeight: '900', letterSpacing: 0.2 },
  payLeft: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 12 },
  payIcon: { width: 38, height: 38, backgroundColor: '#f8f7f3', borderRadius: 5, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: '#eee8df' },
  payIconActive: { backgroundColor: '#d1fae5', borderColor: '#bbf7d0' },
  payTitle: { color: '#1c1917', fontSize: 12, fontWeight: '800', letterSpacing: 0 },
  paySub: { color: '#78716c', fontSize: 9, lineHeight: 12, marginTop: 3 },
  radio: { width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: '#d6d3d1', alignItems: 'center', justifyContent: 'center', marginLeft: 10 },
  radioActive: { borderColor: '#065f46' },
  radioDot: { width: 9, height: 9, borderRadius: 5, backgroundColor: '#065f46' },
  continueBtn: { marginTop: 12, minHeight: 52, backgroundColor: '#065f46', borderRadius: 18, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  continueText: { color: '#fff', fontSize: 14, fontWeight: '900', letterSpacing: 1.2 },
  disabledBtn: { opacity: 0.7 },
  qrPanel: { position: 'relative', backgroundColor: 'transparent', borderWidth: 0, padding: 0, shadowOpacity: 0, elevation: 0 },
  awaiting: { color: '#065f46', fontSize: 12, fontWeight: '900', letterSpacing: 1.1, textAlign: 'center', marginBottom: 3 },
  refText: { color: '#a8a29e', fontSize: 10, fontFamily: 'monospace', textAlign: 'center', marginBottom: 8 },
  qrBox: { width: 166, height: 166, backgroundColor: '#fff', padding: 6, borderWidth: 2, borderColor: '#bbf7d0', borderRadius: 16, alignSelf: 'center', marginBottom: 6 },
  qrImg: { width: '100%', height: '100%' },
  verified: { color: '#78716c', fontSize: 9, fontWeight: '900', letterSpacing: 0.9, textAlign: 'center', marginBottom: 8 },
  infoBlock: { marginBottom: 7, flex: 1 },
  infoLabel: { color: '#78716c', fontSize: 10, fontWeight: '900', letterSpacing: 0.8, textTransform: 'uppercase', marginBottom: 3 },
  infoValue: { color: '#1c1917', fontSize: 13, fontWeight: '800', lineHeight: 17 },
  infoHighlight: { color: '#065f46', fontSize: 22, lineHeight: 27 },
  mono: { fontFamily: 'monospace', letterSpacing: 1 },
  twoCols: { flexDirection: 'row', gap: 12 },
  transferBox: { backgroundColor: '#f7f5f0', borderWidth: 1, borderColor: '#eee8df', borderLeftWidth: 3, borderLeftColor: '#065f46', borderRadius: 12, padding: 8, marginBottom: 8 },
  transferLabel: { color: '#065f46', fontSize: 9, fontWeight: '900', letterSpacing: 0.8, marginBottom: 4 },
  transferValue: { color: '#1c1917', fontSize: 14, fontWeight: '900', fontFamily: 'monospace', letterSpacing: 1.4 },
  confirmBtn: { minHeight: 42, backgroundColor: '#065f46', borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  confirmText: { color: '#fff', fontSize: 12, fontWeight: '900', letterSpacing: 0.8 },
  devBtn: { marginTop: 7, borderWidth: 1, borderStyle: 'dashed', borderColor: '#bbf7d0', borderRadius: 12, paddingVertical: 6, alignItems: 'center', backgroundColor: '#f0fdf4' },
  devText: { color: '#047857', fontSize: 10, fontWeight: '800' },
  methodBackBtn: { marginTop: 7, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 3 },
  methodBackText: { color: '#78716c', fontSize: 10, fontWeight: '900', letterSpacing: 0.8 },
});
