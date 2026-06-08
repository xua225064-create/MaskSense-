import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { apiGetLibrary } from '../api';
import { AppFooter } from '../components/NavHeader';
import { normalizeLanguage, uiText } from '../i18n';

const ERAS = [
  { key: 'all', label: { en: 'ALL', vi: 'TẤT CẢ' } },
  { key: 'minh', label: { en: 'MING', vi: 'MINH' } },
  { key: 'thanh', label: { en: 'QING', vi: 'THANH' } },
  { key: 'nguyen', label: { en: 'NGUYEN', vi: 'NGUYỄN' } },
];

function normalizeSearch(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .trim();
}

function getEra(dyn) {
  const d = normalizeSearch(dyn);
  if (d.includes('nguyen') || d.includes('nguy')) return 'nguyen';
  if (d.includes('qing') || d.includes('thanh')) return 'thanh';
  if (d.includes('ming') || d.includes('minh')) return 'minh';
  return 'other';
}

function toPlainLatin(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/Đ/g, 'D')
    .replace(/đ/g, 'd');
}

function englishReignName(value) {
  const text = String(value || '');
  const norm = normalizeSearch(text);
  const names = [
    ['hong vu', 'Hongwu'],
    ['kien van', 'Jianwen'],
    ['vinh lac', 'Yongle'],
    ['khang hy', 'Kangxi'],
    ['can long', 'Qianlong'],
    ['ung chinh', 'Yongzheng'],
    ['gia khanh', 'Jiaqing'],
    ['dao quang', 'Daoguang'],
    ['ham phong', 'Xianfeng'],
    ['dong tri', 'Tongzhi'],
    ['quang tu', 'Guangxu'],
    ['tuyen thong', 'Xuantong'],
    ['thieu tri', 'Thieu Tri'],
    ['tu duc', 'Tu Duc'],
    ['minh mang', 'Minh Mang'],
    ['gia long', 'Gia Long'],
  ];
  const match = names.find(([key]) => norm.includes(key));
  if (match) return match[1];
  return toPlainLatin(text);
}

function englishNotes(desc, era, period) {
  const norm = normalizeSearch(desc);
  if (norm.includes('hoang de khai quoc nha minh') || norm.includes('founding emperor of the ming dynasty')) {
    return `Founding emperor of the Ming dynasty. Period ${period}.`;
  }
  if (norm.includes('hoang de cuoi cung nha thanh') || norm.includes('tuyen thong')) {
    return `Last emperor of the Qing dynasty. Period ${period}.`;
  }
  if (norm.includes('thu phap dat den do chuan muc cao') || norm.includes('net chu ngay ngan') || norm.includes('khai thu') || norm.includes('trien tu')) {
    return 'The calligraphy is highly standardized, with neat, sharp, and carefully controlled strokes.';
  }
  if (norm.includes('thuong viet thanh ba dong') || norm.includes('moi dong hai chu') || norm.includes('net chu day dan')) {
    return 'Usually written in three rows with two characters per row. The strokes are thick, firm, and forceful.';
  }
  if (norm.includes('hieu de rat hiem')) return `Very rare reign mark. Period ${period}.`;
  if (norm.includes('gom su noi tieng') || norm.includes('xuat khau nhieu')) return `Famous ceramic mark, widely associated with export wares. Period ${period}.`;
  if (norm.includes('tri vi lau nhat') || norm.includes('hieu de bi gia nhieu')) return `Longest reign in Chinese history; this mark is frequently copied. Period ${period}.`;
  if (norm.includes('chu thuong viet tu do')) return 'Usually written in a freer hand, with clear angular turns and often no border or a faint double border.';
  if (norm.includes('da phan dung the khai thu')) return 'Usually written in regular script with decisive brushwork and visible tonal variation.';
  if (norm.includes('bo cuc thuong dan trai')) return 'Balanced blue-and-white layout with darker cobalt accumulation and smooth glaze absorption.';
  return `Reference ceramic reign mark. Period ${period}.`;
}

function normalizeItem(item, idx, L, isVi) {
  const hanzi = item.chu_han || item.chu_han_6 || item.chu_han_4 || '';
  const period = (item.nam_bat_dau && item.nam_ket_thuc)
    ? `${item.nam_bat_dau} - ${item.nam_ket_thuc}`
    : item.nien_dai || L('Unknown', 'Chưa rõ');
  const era = getEra(item.trieu_dai || '');
  const englishName = item.hieu_de_en
    ? `${englishReignName(item.hieu_de_en)} Period Mark`
    : `${englishReignName(item.nien_hieu || item.ten_viet)} Period Mark`;

  return {
    id: item.id || idx,
    hanzi,
    name: isVi ? (item.hien_thi_chinh || item.hieu_de_vi || item.ten_viet || hanzi || L('Unknown mark', 'Chưa rõ hiệu đề')) : englishName,
    dyn: item.trieu_dai || L('Unknown', 'Chưa rõ'),
    nienhieu: isVi ? (item.nien_hieu || item.ten_viet || L('Unknown', 'Chưa rõ')) : englishReignName(item.nien_hieu || item.hieu_de_en || item.ten_viet),
    period,
    desc: isVi ? (item.mo_ta || item.ghi_chu || item.nghe_thuat || L('No detailed description available.', 'Chưa có mô tả chi tiết.')) : englishNotes(item.mo_ta || item.ghi_chu || item.nghe_thuat, era, period),
    era,
  };
}

export default function LibraryScreen({ setScreen, language }) {
  const lang = normalizeLanguage(language);
  const isVi = lang === 'vi';
  const L = useCallback((en, vi) => uiText(lang, en, vi), [lang]);
  const [items, setItems] = useState([]);
  const [era, setEra] = useState('all');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadLibrary = useCallback(async ({ showLoader = false, showRefresh = false } = {}) => {
    if (showLoader) setLoading(true);
    if (showRefresh) setRefreshing(true);
    try {
      const data = await apiGetLibrary();
      setItems((Array.isArray(data) ? data : []).map((item, index) => normalizeItem(item, index, L, isVi)));
    } catch (e) {
      setItems([]);
    } finally {
      if (showLoader) setLoading(false);
      if (showRefresh) setRefreshing(false);
    }
  }, [L, isVi]);

  useEffect(() => {
    loadLibrary({ showLoader: true });
  }, [loadLibrary, lang]);

  const refreshLibrary = useCallback(() => {
    loadLibrary({ showRefresh: true });
  }, [loadLibrary]);

  const filtered = items.filter((x) => {
    if (era !== 'all' && x.era !== era) return false;
    const q = normalizeSearch(search);
    if (!q) return true;
    const haystack = normalizeSearch([x.name, x.dyn, x.nienhieu, x.period, x.desc, x.hanzi].join(' '));
    return haystack.includes(q) || (x.hanzi || '').includes(search.trim());
  });

  const displayDynasty = (dyn) => {
    const norm = normalizeSearch(dyn);
    if (norm.includes('minh') || norm.includes('ming')) return L('Ming Dynasty', 'Triều Minh');
    if (norm.includes('thanh') || norm.includes('qing')) return L('Qing Dynasty', 'Triều Thanh');
    if (norm.includes('nguyen')) return L('Nguyen Dynasty', 'Triều Nguyễn');
    return String(dyn || '');
  };

  const displayNotes = (desc) => String(desc || '');

  const renderItem = ({ item }) => (
    <View style={s.card}>
      <Text style={s.cardTitle}>{item.name}</Text>
      {!!item.hanzi && <Text style={s.hanzi}>{item.hanzi}</Text>}
      <View style={s.dynPill}><Text style={s.dynPillText}>{displayDynasty(item.dyn)}</Text></View>

      <Text style={s.metaText}><Text style={s.bold}>{L('Reign title:', 'Niên hiệu:')} </Text>{item.nienhieu}</Text>
      <Text style={s.metaText}><Text style={s.bold}>{L('Period:', 'Niên đại:')} </Text>{item.period}</Text>
      <Text style={s.metaText} numberOfLines={3}><Text style={s.bold}>{L('Notes:', 'Ghi chú:')} </Text>{displayNotes(item.desc)}</Text>

      <View style={s.tagRow}>
        <View style={s.tag}><Text style={s.tagText}>{L('Mark', 'Hiệu đề')}</Text></View>
        <View style={s.tag}><Text style={s.tagText}>{L('Ceramic', 'Gốm sứ')}</Text></View>
        {item.period !== L('Unknown', 'Chưa rõ') && <View style={s.tag}><Text style={s.tagText}>{item.period}</Text></View>}
      </View>
    </View>
  );

  return (
    <View style={s.container}>
      <FlatList
        data={filtered}
        keyExtractor={(item, i) => String(item.id || i)}
        renderItem={renderItem}
        contentContainerStyle={s.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={refreshLibrary}
            tintColor="#065f46"
            colors={['#065f46']}
          />
        }
        ListHeaderComponent={
          <View style={{ paddingTop: 55 }}>
            <Text style={s.pageTitle}>
              {L('Mark Library', 'Thư viện hiệu đề')} <Text style={s.countText}>({filtered.length} {L('records', 'mục')})</Text>
            </Text>

            <View style={s.searchWrap}>
              <Feather name="search" size={20} color="#78716c" style={s.searchIcon} />
              <TextInput
                style={s.searchInput}
                placeholder={L('Search mark, reign title, dynasty...', 'Tìm hiệu đề, niên hiệu, triều đại...')}
                placeholderTextColor="#a8a29e"
                value={search}
                onChangeText={setSearch}
                autoCapitalize="none"
                autoCorrect={false}
                returnKeyType="search"
              />
              {!!search && (
                <TouchableOpacity style={s.clearSearchBtn} onPress={() => setSearch('')}>
                  <Feather name="x" size={18} color="#78716c" />
                </TouchableOpacity>
              )}
            </View>

            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.filterScroll} contentContainerStyle={s.filterWrap}>
              {ERAS.map((e) => (
                <TouchableOpacity key={e.key} style={[s.filterPill, era === e.key && s.filterPillOn]} onPress={() => setEra(e.key)}>
                  <Text style={[s.filterText, era === e.key && s.filterTextOn]}>{isVi ? e.label.vi : e.label.en}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        }
        ListEmptyComponent={loading ? (
          <ActivityIndicator size="large" color="#065f46" style={{ marginTop: 40 }} />
        ) : (
          <Text style={s.emptyText}>{L('No matching marks found.', 'Không tìm thấy hiệu đề phù hợp.')}</Text>
        )}
      />

      <AppFooter current="Library" setScreen={setScreen} language={lang} />
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fdfbf7' },
  listContent: { paddingHorizontal: 20, paddingBottom: 170 },
  pageTitle: { fontSize: 32, fontFamily: 'serif', color: '#064e3b', marginBottom: 24, flexWrap: 'wrap', fontWeight: 'bold' },
  countText: { fontSize: 16, color: '#78716c', fontWeight: '500', fontFamily: 'System' },
  searchWrap: { backgroundColor: '#f5f5f4', borderRadius: 24, flexDirection: 'row', alignItems: 'center', paddingLeft: 16, paddingRight: 8, height: 52, marginBottom: 20, borderWidth: 1, borderColor: '#eee8df' },
  searchIcon: { marginRight: 10 },
  searchInput: { flex: 1, height: '100%', fontSize: 15, color: '#1c1917', paddingVertical: 0, outlineStyle: 'none' },
  clearSearchBtn: { width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center' },
  emptyText: { marginTop: 32, textAlign: 'center', color: '#78716c', fontSize: 14, fontWeight: '700' },
  filterScroll: { marginHorizontal: -20, marginBottom: 24 },
  filterWrap: { paddingHorizontal: 20, gap: 10 },
  filterPill: { backgroundColor: '#e7e5e4', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20 },
  filterPillOn: { backgroundColor: '#064e3b' },
  filterText: { fontSize: 11, fontWeight: '800', color: '#44403c', letterSpacing: 0.5 },
  filterTextOn: { color: '#ffffff' },
  card: { backgroundColor: '#ffffff', borderRadius: 20, padding: 20, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 10, shadowOffset: { width: 0, height: 4 }, elevation: 2 },
  cardTitle: { fontSize: 18, fontWeight: '800', color: '#1c1917', fontFamily: 'serif', marginBottom: 4 },
  hanzi: { fontSize: 22, color: '#064e3b', marginBottom: 10, fontWeight: '700' },
  dynPill: { backgroundColor: '#e0f2fe', alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, marginBottom: 14 },
  dynPillText: { color: '#0369a1', fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
  metaText: { fontSize: 13, color: '#44403c', lineHeight: 22, marginBottom: 6 },
  bold: { fontWeight: '800', color: '#1c1917' },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  tag: { backgroundColor: '#f5f5f4', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  tagText: { color: '#57534e', fontSize: 10, fontWeight: '700' },
});
