import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, FlatList, ActivityIndicator, Image, ScrollView, TouchableOpacity, Linking } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { BASE_URL } from '../config';
import { apiGetHistory } from '../api';
import { AppFooter } from '../components/NavHeader';
import { normalizeLanguage, uiText } from '../i18n';

const parseResult = (value) => {
  if (!value) return {};
  if (typeof value === 'string') {
    try { return JSON.parse(value); } catch (e) { return {}; }
  }
  return value;
};

const pick = (obj, keys, fallback = '') => {
  for (const key of keys) {
    const value = obj?.[key];
    if (value !== undefined && value !== null && String(value).trim() !== '') return value;
  }
  return fallback;
};

const confidenceText = (value, L = (text) => text) => {
  const num = Number(value || 0);
  if (!Number.isFinite(num) || num <= 0) return '';
  return `${Math.round(num <= 1 ? num * 100 : num)}% ${L('confidence', 'tin cậy')}`;
};

const imageUri = (path = '') => {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path;
  return `${BASE_URL}/${String(path).replace(/^\/+/, '')}`;
};

const asList = (value) => {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);
  return [value].filter(Boolean);
};

const sourceUrl = (source) => {
  if (!source) return '';
  if (typeof source === 'string') return source;
  return source.url || source.link || source.href || '';
};

const sourceTitle = (source, index) => {
  if (!source) return `Source ${index + 1}`;
  if (typeof source === 'string') return source.replace(/^https?:\/\//, '').split('/')[0] || `Source ${index + 1}`;
  return source.title || source.name || source.domain || sourceUrl(source) || `Source ${index + 1}`;
};

const normalizePlain = (value) => String(value || '')
  .toLowerCase()
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .replace(/đ/g, 'd');

const toPlainLatin = (value) => String(value || '')
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .replace(/Đ/g, 'D')
  .replace(/đ/g, 'd');

const englishReignName = (value) => {
  const text = String(value || '');
  const norm = normalizePlain(text);
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
    ['gia long', 'Gia Long'],
    ['minh mang', 'Minh Mang'],
    ['thieu tri', 'Thieu Tri'],
    ['tu duc', 'Tu Duc'],
  ];
  const match = names.find(([key]) => norm.includes(key));
  if (match) return match[1];
  return toPlainLatin(text);
};

const englishText = (value, fallback = '') => {
  const text = String(value || '');
  const norm = normalizePlain(text);
  if (!text.trim()) return fallback;
  if (norm.includes('tri vi lau nhat') || norm.includes('hieu de bi gia nhieu') || norm.includes('lich su tq')) {
    return 'Longest reign in Chinese history; this reign mark is frequently copied.';
  }
  if (norm.includes('thuong viet thanh ba dong') || norm.includes('moi dong hai chu') || norm.includes('net chu day dan')) {
    return 'Usually written in three rows with two characters per row. The strokes are thick, firm, and forceful.';
  }
  if (norm.includes('hoang de cuoi cung nha thanh') || norm.includes('tuyen thong')) {
    return 'Last emperor of the Qing dynasty. Period 1909 - 1912.';
  }
  if (norm.includes('thu phap dat den do chuan muc cao') || norm.includes('net chu ngay ngan') || norm.includes('khai thu') || norm.includes('trien tu')) {
    return 'The calligraphy is highly standardized, with neat, sharp, and carefully controlled strokes. Regular script is common on imperial wares, while seal script is sometimes used.';
  }
  if (norm.includes('tri vi lau nhat') || norm.includes('hieu de bi gia nhieu')) {
    return 'Longest reign in Chinese history; this mark is frequently copied.';
  }
  if (norm.includes('thuong viet thanh ba dong') || norm.includes('moi dong hai chu')) {
    return 'Usually written in three rows with two characters per row. The strokes are bold and strong.';
  }
  if (norm.includes('hoang de khai quoc nha minh')) return 'Founding emperor of the Ming dynasty.';
  if (norm.includes('hieu de rat hiem')) return 'Very rare reign mark.';
  if (norm.includes('gom su noi tieng') || norm.includes('xuat khau nhieu')) return 'Famous ceramic mark, widely associated with export wares.';
  if (norm.includes('da phan dung the khai thu')) return 'Usually written in regular script with decisive brushwork and visible tonal variation.';
  if (norm.includes('bo cuc thuong dan trai')) return 'Balanced blue-and-white layout with darker cobalt accumulation and smooth glaze absorption.';
  if (/[\u00C0-\u1EF9]/.test(text) || /\b(la|va|cua|nha|hieu|nien|thuong|chu|net|tri|lich|nhieu)\b/i.test(norm)) {
    return fallback || 'Reference information is available for this analysis.';
  }
  return text;
};

const DetailRow = ({ label, value }) => {
  if (value === undefined || value === null || String(value).trim() === '') return null;
  return (
    <View style={s.detailRow}>
      <Text style={s.detailLabel}>{label}</Text>
      <Text style={s.detailValue}>{String(value)}</Text>
    </View>
  );
};

const Section = ({ title, children }) => {
  if (!children) return null;
  return (
    <View style={s.detailSection}>
      <Text style={s.detailSectionTitle}>{title}</Text>
      {children}
    </View>
  );
};

export default function HistoryScreen({ user, setScreen, language }) {
  const lang = normalizeLanguage(language);
  const isEnglish = lang === 'en';
  const L = (en, vi) => uiText(lang, en, vi);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    if (!user?.token) { setLoading(false); return; }
    apiGetHistory(user.token)
      .then((d) => {
        if (d.success && d.history) setHistory(d.history);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  const displayDynasty = (dyn) => {
    const value = String(dyn || '');
    const norm = value
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
    if (norm.includes('minh') || norm.includes('ming')) return L('Ming Dynasty', 'Triều Minh');
    if (norm.includes('thanh') || norm.includes('qing')) return L('Qing Dynasty', 'Triều Thanh');
    if (norm.includes('nguyen')) return L('Nguyen Dynasty', 'Triều Nguyễn');
    return value;
  };

  const displayReign = (value) => isEnglish ? englishReignName(value) : value;
  const displayText = (value, fallback = '') => isEnglish ? englishText(value, fallback) : value;

  const renderItem = ({ item }) => {
    const r = parseResult(item.match_result);
    const title = pick(r, ['hien_thi_chinh', 'hieu_de_vi', 'ten_viet', 'top_mark', 'chu_han'], item.ocr_text || L('Unknown mark', 'Chưa rõ hiệu đề'));
    const subtitle = displayDynasty(pick(r, ['trieu_dai', 'nien_hieu', 'hieu_de_en', 'phien_am'], L('Web analysis', 'Phân tích web')));
    const conf = confidenceText(pick(r, ['aggregated_confidence', 'confidence', 'tin_cay'], ''), L);

    return (
      <TouchableOpacity style={s.card} activeOpacity={0.86} onPress={() => setSelected(item)}>
        <View style={s.thumb}>
          {!!item.image_path && <Image source={{ uri: imageUri(item.image_path) }} style={s.img} resizeMode="cover" />}
        </View>
        <View style={s.body}>
          <Text style={s.title} numberOfLines={1}>{title}</Text>
          <Text style={s.sub} numberOfLines={1}>{subtitle}</Text>
          <Text style={s.date}>{item.created_at || ''}</Text>
          {!!conf && <Text style={s.conf}>{conf}</Text>}
        </View>
      </TouchableOpacity>
    );
  };

  const renderDetail = () => {
    const r = parseResult(selected.match_result);
    const title = pick(r, ['hien_thi_chinh', 'hieu_de_vi', 'ten_viet', 'top_mark', 'chu_han'], selected.ocr_text || L('Unknown mark', 'Chưa rõ hiệu đề'));
    const conf = confidenceText(pick(r, ['aggregated_confidence', 'confidence', 'tin_cay'], ''), L);
    const period = pick(r, ['nien_dai'], '');
    const sources = [
      ...asList(r.search_sources),
      ...asList(r.cac_nguon_tham_khao),
      ...asList(r.wv_best_sources),
      ...asList(r.unverified_search_sources),
      ...asList(r.image_search_sources),
    ].filter((source, index, arr) => {
      const url = sourceUrl(source);
      return url && arr.findIndex((item) => sourceUrl(item) === url) === index;
    });
    const pipelineDetails = asList(r.pipeline_details);
    const ocrCandidates = asList(r.evidence_candidates || r.candidate_evidence || r.candidates).slice(0, 8);

    return (
      <View style={s.container}>
        <ScrollView contentContainerStyle={s.detailContent}>
          <TouchableOpacity style={s.backBtn} onPress={() => setSelected(null)} activeOpacity={0.82}>
            <Feather name="chevron-left" size={22} color="#1c1917" />
            <Text style={s.backText}>{L('History', 'Lịch sử')}</Text>
          </TouchableOpacity>

          <View style={s.detailHero}>
            {!!selected.image_path ? (
              <Image source={{ uri: imageUri(selected.image_path) }} style={s.detailImage} resizeMode="cover" />
            ) : (
              <View style={s.noImage}><Feather name="image" size={34} color="#a8a29e" /></View>
            )}
          </View>

          <View style={s.detailHeader}>
            <Text style={s.detailTitle}>{title}</Text>
            <Text style={s.detailSubtitle}>{displayReign(pick(r, ['nien_hieu', 'phien_am', 'hieu_de_en'], selected.ocr_text || L('Saved analysis', 'Phân tích đã lưu')))}</Text>
            <View style={s.metaLine}>
              {!!selected.created_at && <Text style={s.metaPill}>{selected.created_at}</Text>}
              {!!conf && <Text style={s.metaPill}>{conf}</Text>}
            </View>
          </View>

          <Section title={L('Recognition', 'Nhận diện')}>
            <DetailRow label={L('OCR text', 'Văn bản OCR')} value={selected.ocr_text || pick(r, ['chu_han', 'hieu_de', 'text_ocr'], '')} />
            <DetailRow label={L('Chinese mark', 'Chữ Hán')} value={pick(r, ['chu_han', 'hieu_de', 'text_ocr'], '')} />
            <DetailRow label={L('Vietnamese name', 'Tên tiếng Việt')} value={isEnglish ? '' : pick(r, ['hieu_de_vi', 'ten_viet', 'hien_thi_chinh'], '')} />
            <DetailRow label={L('Transcription', 'Phiên âm')} value={displayReign(pick(r, ['phien_am', 'hieu_de_en'], ''))} />
          </Section>

          <Section title={L('Historical Details', 'Chi tiết lịch sử')}>
            <DetailRow label={L('Dynasty', 'Triều đại')} value={displayDynasty(pick(r, ['trieu_dai'], ''))} />
            <DetailRow label={L('Reign era', 'Niên hiệu')} value={displayReign(pick(r, ['nien_hieu'], ''))} />
            <DetailRow label={L('Emperor', 'Hoàng đế')} value={displayReign(pick(r, ['hoang_de'], ''))} />
            <DetailRow label={L('Period', 'Niên đại')} value={period || (r.nam_bat_dau && r.nam_ket_thuc ? `${r.nam_bat_dau}-${r.nam_ket_thuc}` : '')} />
            <DetailRow label={L('Meaning', 'Ý nghĩa')} value={displayText(pick(r, ['y_nghia', 'ghi_chu'], ''), 'Reference meaning is available for this reign mark.')} />
          </Section>

          <Section title={L('Context', 'Bối cảnh')}>
            <Text style={s.paragraph}>{displayText(pick(r, ['mo_ta', 'boi_canh'], L('No context saved for this analysis yet.', 'Chưa có bối cảnh được lưu cho phân tích này.')), L('No context saved for this analysis yet.', 'Chưa có bối cảnh được lưu cho phân tích này.'))}</Text>
          </Section>

          <Section title={L('Art & Calligraphy', 'Mỹ thuật & thư pháp')}>
            <Text style={s.paragraph}>{displayText(pick(r, ['thu_phap', 'thu_phap_dac_biet', 'nghe_thuat'], L('No calligraphy notes saved for this analysis yet.', 'Chưa có ghi chú thư pháp cho phân tích này.')), L('No calligraphy notes saved for this analysis yet.', 'Chưa có ghi chú thư pháp cho phân tích này.'))}</Text>
          </Section>

          {(pick(r, ['primary_pipeline', 'pipeline_chinh'], '') || pipelineDetails.length > 0 || ocrCandidates.length > 0) && (
            <Section title={L('AI Evidence', 'Bằng chứng AI')}>
              <DetailRow label={L('Primary pipeline', 'Pipeline chính')} value={pick(r, ['primary_pipeline', 'pipeline_chinh'], '')} />
              <DetailRow label={L('Valid pipelines', 'Pipeline hợp lệ')} value={pick(r, ['num_valid_pipelines', 'so_pipeline_hop_le'], '')} />
              <DetailRow label={L('Verification', 'Xác minh')} value={pick(r, ['verification_status', 'canh_bao'], '')} />
              {ocrCandidates.length > 0 && (
                <View style={s.chipWrap}>
                  {ocrCandidates.map((candidate, index) => (
                    <Text key={`${String(candidate)}-${index}`} style={s.chip} numberOfLines={1}>
                      {typeof candidate === 'string' ? candidate : pick(candidate, ['chu_han', 'name', 'label', 'candidate'], `${L('Candidate', 'Ứng viên')} ${index + 1}`)}
                    </Text>
                  ))}
                </View>
              )}
              {pipelineDetails.slice(0, 5).map((pipeline, index) => (
                <View key={`${pipeline.pipeline_name || 'pipeline'}-${index}`} style={s.pipelineRow}>
                  <Text style={s.pipelineName}>{pipeline.pipeline_name || `Pipeline ${index + 1}`}</Text>
                  <Text style={s.pipelineMeta}>{confidenceText(pipeline.confidence, L) || pipeline.status || ''}</Text>
                </View>
              ))}
            </Section>
          )}

          {sources.length > 0 && (
            <Section title={L('Sources', 'Nguồn tham khảo')}>
              {sources.slice(0, 8).map((source, index) => {
                const url = sourceUrl(source);
                return (
                  <TouchableOpacity key={`${url}-${index}`} style={s.sourceRow} onPress={() => Linking.openURL(url)} activeOpacity={0.75}>
                    <Feather name="external-link" size={16} color="#065f46" />
                    <Text style={s.sourceText} numberOfLines={2}>{sourceTitle(source, index)}</Text>
                  </TouchableOpacity>
                );
              })}
            </Section>
          )}
        </ScrollView>
        <AppFooter current="History" setScreen={setScreen} language={lang} />
      </View>
    );
  };

  if (selected) return renderDetail();

  return (
    <View style={s.container}>
      <View style={s.content}>
        <View style={s.pgHd}>
          <Text style={s.pgTitle}>{L('Analysis History', 'Lịch sử phân tích')}</Text>
          <Text style={s.pgSub}>{L('Recognition sessions saved by the web engine', 'Các phiên nhận diện đã lưu từ hệ thống web')}</Text>
        </View>

        {loading ? (
          <ActivityIndicator size="large" color="#065f46" style={{ marginTop: 60 }} />
        ) : !user ? (
          <View style={s.emptyBox}><Text style={s.emptyIcon}>?</Text><Text style={s.emptyText}>{L('Please sign in to view your history.', 'Vui lòng đăng nhập để xem lịch sử.')}</Text></View>
        ) : history.length === 0 ? (
          <View style={s.emptyBox}><Text style={s.emptyIcon}>?</Text><Text style={s.emptyText}>{L('No analysis sessions yet.', 'Chưa có phiên phân tích nào.')}</Text></View>
        ) : (
          <FlatList
            data={history}
            keyExtractor={(item, i) => String(item.id || i)}
            renderItem={renderItem}
            numColumns={2}
            columnWrapperStyle={s.row}
            contentContainerStyle={s.listContent}
          />
        )}
      </View>
      <AppFooter current="History" setScreen={setScreen} language={lang} />
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fdfbf7' },
  content: { flex: 1 },
  pgHd: { paddingHorizontal: 20, paddingTop: 55, paddingBottom: 16, marginBottom: 8 },
  pgTitle: { fontSize: 32, fontFamily: 'serif', color: '#064e3b', fontWeight: 'bold' },
  pgSub: { fontSize: 13, color: '#78716c', marginTop: 4 },
  listContent: { paddingHorizontal: 20, paddingBottom: 170 },
  row: { justifyContent: 'space-between', marginBottom: 16 },
  card: { width: '48%', backgroundColor: '#ffffff', borderRadius: 16, overflow: 'hidden', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 3 },
  thumb: { height: 130, backgroundColor: '#e7e5e4' },
  img: { width: '100%', height: '100%' },
  body: { padding: 12 },
  title: { fontSize: 13, fontWeight: '700', color: '#1c1917', marginBottom: 2, fontFamily: 'serif' },
  sub: { fontSize: 11, color: '#57534e', fontWeight: '500', marginBottom: 6 },
  date: { fontSize: 9, color: '#a8a29e', fontWeight: '800' },
  conf: { fontSize: 9, color: '#065f46', fontWeight: '800', marginTop: 4 },
  emptyBox: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 40 },
  emptyIcon: { fontSize: 56, color: '#d6d3d1', fontWeight: 'bold', marginBottom: 16 },
  emptyText: { fontSize: 13, color: '#78716c', textAlign: 'center' },
  detailContent: { paddingHorizontal: 20, paddingTop: 24, paddingBottom: 170 },
  backBtn: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', paddingVertical: 10, marginBottom: 10 },
  backText: { fontSize: 13, fontWeight: '800', color: '#1c1917' },
  detailHero: { width: '100%', height: 300, borderRadius: 22, overflow: 'hidden', backgroundColor: '#e7e5e4', marginBottom: 22 },
  detailImage: { width: '100%', height: '100%' },
  noImage: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  detailHeader: { marginBottom: 22 },
  detailTitle: { fontSize: 30, lineHeight: 36, fontFamily: 'serif', fontWeight: '800', color: '#1c1917' },
  detailSubtitle: { fontSize: 14, lineHeight: 21, color: '#57534e', marginTop: 6 },
  metaLine: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 14 },
  metaPill: { backgroundColor: '#f5f5f4', color: '#44403c', fontSize: 11, fontWeight: '800', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 12 },
  detailSection: { backgroundColor: '#fff', borderRadius: 10, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: '#eee8df' },
  detailSectionTitle: { fontSize: 18, fontFamily: 'serif', fontWeight: '800', color: '#1c1917', marginBottom: 12 },
  detailRow: { borderTopWidth: 1, borderTopColor: '#f5f5f4', paddingTop: 10, marginTop: 10 },
  detailLabel: { fontSize: 10, fontWeight: '900', letterSpacing: 0.8, textTransform: 'uppercase', color: '#78716c', marginBottom: 4 },
  detailValue: { fontSize: 14, lineHeight: 21, fontWeight: '600', color: '#1c1917' },
  paragraph: { fontSize: 14, lineHeight: 23, color: '#57534e' },
  chipWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  chip: { maxWidth: '48%', backgroundColor: '#f0fdf4', color: '#065f46', fontSize: 12, fontWeight: '800', paddingHorizontal: 10, paddingVertical: 7, borderRadius: 12 },
  pipelineRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderTopWidth: 1, borderTopColor: '#f5f5f4', paddingTop: 10, marginTop: 10 },
  pipelineName: { fontSize: 13, fontWeight: '800', color: '#1c1917' },
  pipelineMeta: { fontSize: 12, fontWeight: '800', color: '#065f46' },
  sourceRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 10, borderTopWidth: 1, borderTopColor: '#f5f5f4' },
  sourceText: { flex: 1, fontSize: 13, lineHeight: 18, fontWeight: '700', color: '#065f46' },
});
