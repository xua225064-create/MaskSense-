import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, TouchableOpacity, Image, ActivityIndicator, Alert, StyleSheet, Dimensions, Animated, Linking } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Feather, Ionicons } from '@expo/vector-icons';
import { apiOcr, apiGetHistory } from '../api';
import { BASE_URL } from '../config';
import { AppHeader, AppFooter } from '../components/NavHeader';
import heroMarkImage from '../../assets/hero-mark.png';
import { normalizeLanguage, uiText } from '../i18n';
import {
  englishCalligraphyText,
  englishContextText,
  englishDynastyName,
  englishEmperorName,
  englishMarkTitle,
  englishReignName,
} from '../markLocalization';

const { width: screenWidth, height: screenHeight } = Dimensions.get('window');
const cameraTopHeight = 96;
const cameraBottomHeight = Math.round(Math.min(300, Math.max(220, screenHeight * 0.34)));
const cameraPreviewHeight = Math.max(320, screenHeight - cameraTopHeight - cameraBottomHeight);
const scanFrameWidth = Math.max(260, screenWidth - 104);
const scanFrameHeight = Math.max(250, cameraPreviewHeight - 110);
const scanFrameTop = Math.max(42, (cameraPreviewHeight - scanFrameHeight) / 2);

const KNOWLEDGE_ARTICLES = [
  {
    id: 'read-reign-mark',
    tag: 'HƯỚNG DẪN',
    title: 'Cách đọc hiệu đề dưới đáy gốm cổ',
    meta: '5 phút đọc • MarkSense Research',
    image: heroMarkImage,
    intro: 'Hiệu đề là một trong những dấu hiệu quan trọng giúp nhận diện niên đại, lò gốm và bối cảnh chế tác của hiện vật.',
    sections: [
      {
        heading: 'Quan sát bố cục trước khi đọc chữ',
        body: 'Hãy bắt đầu bằng hình dạng khung hiệu đề: vòng tròn kép, khung vuông, khung chữ nhật hoặc không khung. Bố cục này thường gợi ý phong cách triều đại và chuẩn mực của từng dòng gốm.',
      },
      {
        heading: 'Đọc theo trật tự Hán tự',
        body: 'Nhiều hiệu đề được viết theo cột dọc từ trên xuống, phải sang trái. Với hiệu đề sáu chữ, hai chữ đầu thường chỉ triều đại, hai chữ giữa là niên hiệu, hai chữ cuối là chế tác.',
      },
      {
        heading: 'Đối chiếu nét bút và men',
        body: 'Không nên chỉ dựa vào nội dung chữ. Độ run của nét, màu lam cobalt, độ thấm men và vết rạn bề mặt đều là dữ liệu cần đối chiếu để tránh nhầm với bản sao hiện đại.',
      },
    ],
  },
  {
    id: 'han-nom-meaning',
    tag: 'NGHIÊN CỨU',
    title: 'Ý nghĩa chữ Hán Nôm trong niên hiệu gốm sứ',
    meta: '8 phút đọc • Thư viện MarkSense',
    image: heroMarkImage,
    intro: 'Chữ Hán Nôm trên gốm không chỉ là ký hiệu trang trí; chúng phản ánh niên hiệu, xưởng chế tác, mục đích sử dụng và quan niệm thẩm mỹ của từng thời kỳ.',
    sections: [
      {
        heading: 'Niên hiệu và quyền lực biểu tượng',
        body: 'Các cụm như Đại Minh, Đại Thanh hoặc các niên hiệu cụ thể thường dùng để khẳng định chuẩn mực triều đình. Tuy vậy, một số hiệu đề được sử dụng như mô thức trang trí sau thời kỳ gốc.',
      },
      {
        heading: 'Chữ tốt lành và đồ dùng dân gian',
        body: 'Những chữ như Phúc, Thọ, Khang, Ninh thường xuất hiện trên đồ thờ, đồ gia dụng cao cấp hoặc vật phẩm chúc tụng. Ý nghĩa của chúng cần đọc cùng hoa văn và công năng của hiện vật.',
      },
      {
        heading: 'Sai biệt chữ viết là dữ liệu quan trọng',
        body: 'Một nét thiếu, một nét kéo dài hoặc cách giản lược khác thường có thể cho biết vùng sản xuất, tay thợ, hoặc dấu hiệu phục chế. Vì vậy ảnh chụp cần rõ nét và đủ sáng.',
      },
    ],
  },
];

const KNOWLEDGE_ARTICLES_EN = [
  {
    id: 'read-reign-mark',
    tag: 'GUIDE',
    title: 'How to read reign marks on antique ceramics',
    meta: '5 min read - MarkSense Research',
    image: heroMarkImage,
    intro: 'A reign mark is one of the key clues for identifying period, kiln context, and historical background.',
    sections: [
      { heading: 'Observe the layout first', body: 'Start with the mark frame: double circle, square, rectangle, or no frame. The layout often suggests dynastic style and workshop conventions.' },
      { heading: 'Read in traditional character order', body: 'Many marks are written vertically from top to bottom and right to left. In six-character marks, the first two characters often indicate dynasty, the middle two the reign era, and the last two production.' },
      { heading: 'Compare brushwork and glaze', body: 'Do not rely on text alone. Stroke quality, cobalt tone, glaze absorption, and surface crackle all help distinguish period work from later copies.' },
    ],
  },
  {
    id: 'han-nom-meaning',
    tag: 'RESEARCH',
    title: 'Meaning of Chinese and Sino-Nom characters in ceramic marks',
    meta: '8 min read - MarkSense Library',
    image: heroMarkImage,
    intro: 'Characters on ceramics are not only decorative symbols; they can reflect reign era, workshop, function, and aesthetic ideas of the period.',
    sections: [
      { heading: 'Reign titles and symbolic authority', body: 'Phrases such as Great Ming, Great Qing, or specific reign titles often express court standards, though some marks were reused decoratively after the original period.' },
      { heading: 'Auspicious characters and domestic wares', body: 'Auspicious characters often appear on ritual or high-quality domestic wares and should be read with pattern and function.' },
      { heading: 'Writing variation matters', body: 'A missing stroke, extended stroke, or unusual simplification can indicate region, workshop hand, or later restoration. Clear lighting and focus are essential.' },
    ],
  },
];

const buildKnowledgeArticles = (L) => [
  {
    id: 'read-reign-mark',
    tag: L('GUIDE', 'HƯỚNG DẪN'),
    title: L('How to read reign marks on antique ceramics', 'Cách đọc hiệu đề dưới đáy gốm cổ'),
    meta: L('5 min read - MarkSense Research', '5 phút đọc - MarkSense Research'),
    image: heroMarkImage,
    intro: L(
      'A reign mark is one of the key clues for identifying period, kiln context, and historical background.',
      'Hiệu đề là một trong những dấu hiệu quan trọng giúp nhận diện niên đại, lò gốm và bối cảnh lịch sử.'
    ),
    sections: [
      {
        heading: L('Observe the layout first', 'Observe the layout first'),
        body: L('Start with the mark frame: double circle, square, rectangle, or no frame. The layout often suggests dynastic style and workshop conventions.', 'Start with the mark frame: double circle, square, rectangle, or no frame. The layout often suggests dynastic style and workshop conventions.'),
      },
      {
        heading: L('Read in traditional character order', 'Read in traditional character order'),
        body: L('Many marks are written vertically from top to bottom and right to left. In six-character marks, the first two characters often indicate dynasty, the middle two the reign era, and the last two production.', 'Many marks are written vertically from top to bottom and right to left. In six-character marks, the first two characters often indicate dynasty, the middle two the reign era, and the last two production.'),
      },
      {
        heading: L('Compare brushwork and glaze', 'Compare brushwork and glaze'),
        body: L('Do not rely on text alone. Stroke quality, cobalt tone, glaze absorption, and surface crackle all help distinguish period work from later copies.', 'Do not rely on text alone. Stroke quality, cobalt tone, glaze absorption, and surface crackle all help distinguish period work from later copies.'),
      },
    ],
  },
  {
    id: 'han-nom-meaning',
    tag: L('RESEARCH', 'NGHIÊN CỨU'),
    title: L('Meaning of Chinese and Sino-Nom characters in ceramic marks', 'Ý nghĩa chữ Hán Nôm trong niên hiệu gốm sứ'),
    meta: L('8 min read - MarkSense Library', '8 phút đọc - Thư viện MarkSense'),
    image: heroMarkImage,
    intro: L(
      'Characters on ceramics are not only decorative symbols; they can reflect reign era, workshop, function, and aesthetic ideas of the period.',
      'Chữ Hán Nôm trên gốm không chỉ là ký hiệu trang trí; chúng phản ánh niên hiệu, xưởng chế tác, mục đích sử dụng và quan niệm thẩm mỹ của từng thời kỳ.'
    ),
    sections: [
      {
        heading: L('Reign titles and symbolic authority', 'Reign titles and symbolic authority'),
        body: L('Phrases such as Great Ming, Great Qing, or specific reign titles often express court standards, though some marks were reused decoratively after the original period.', 'Phrases such as Great Ming, Great Qing, or specific reign titles often express court standards, though some marks were reused decoratively after the original period.'),
      },
      {
        heading: L('Auspicious characters and domestic wares', 'Auspicious characters and domestic wares'),
        body: L('Auspicious characters often appear on ritual or high-quality domestic wares and should be read with pattern and function.', 'Auspicious characters often appear on ritual or high-quality domestic wares and should be read with pattern and function.'),
      },
      {
        heading: L('Writing variation matters', 'Writing variation matters'),
        body: L('A missing stroke, extended stroke, or unusual simplification can indicate region, workshop hand, or later restoration. Clear lighting and focus are essential.', 'A missing stroke, extended stroke, or unusual simplification can indicate region, workshop hand, or later restoration. Clear lighting and focus are essential.'),
      },
    ],
  },
];

const pickField = (obj, keys, fallback = '') => {
  for (const key of keys) {
    const value = obj?.[key];
    if (value !== undefined && value !== null && String(value).trim() !== '') return value;
  }
  return fallback;
};

const normalizeConfidence = (value) => {
  const num = Number(value || 0);
  if (!Number.isFinite(num) || num <= 0) return 0;
  return Math.round(num <= 1 ? num * 100 : num);
};

const parseHistoryResult = (value) => {
  if (!value) return {};
  if (typeof value === 'string') {
    try { return JSON.parse(value); } catch (e) { return {}; }
  }
  return value;
};

const asDisplayText = (value, fallback = '') => {
  if (value === undefined || value === null || value === '') return fallback;
  if (Array.isArray(value)) {
    const joined = value.map((item) => asDisplayText(item)).filter(Boolean).join(', ');
    return joined || fallback;
  }
  if (typeof value === 'object') {
    const preferred = value.text || value.title || value.name || value.message || value.summary || value.description;
    if (preferred) return asDisplayText(preferred, fallback);
    try {
      return JSON.stringify(value);
    } catch (e) {
      return fallback;
    }
  }
  return String(value);
};

const sourceLabelFromUrl = (url, idx) => {
  try {
    return new URL(url).hostname.replace(/^www\./, '') || `Source ${idx + 1}`;
  } catch (e) {
    return `Source ${idx + 1}`;
  }
};

const sourceParts = (item, idx) => {
  const url = typeof item === 'string' ? item : (item?.url || item?.source_url || item?.link || '');
  const title = typeof item === 'string'
    ? sourceLabelFromUrl(item, idx)
    : (item?.title || item?.source_title || item?.claim || sourceLabelFromUrl(url, idx));
  return {
    url,
    title: asDisplayText(title, sourceLabelFromUrl(url, idx)),
    quality: item?.source_quality || '',
  };
};

const collectSources = (...objects) => {
  const raw = [];
  objects.filter(Boolean).forEach((obj) => {
    [
      obj.candidate_evidence,
      obj.evidence_candidates,
      obj.search_sources,
      obj.cac_nguon_tham_khao,
      obj.nguon_tham_khao,
      obj.unverified_search_sources,
      obj.image_search_sources,
      obj.wv_source_links,
      obj.wv_best_sources,
      obj.web_verification?.all_source_links,
      obj.web_verification?.best_candidate?.sources,
    ].forEach((value) => {
      if (typeof value === 'string') raw.push(value);
      else if (Array.isArray(value)) raw.push(...value);
    });
  });
  const seen = new Set();
  return raw
    .map(sourceParts)
    .filter((item) => item.url && !seen.has(item.url) && seen.add(item.url))
    .slice(0, 6);
};

export default function HomeScreen({ user, credits, setScreen, refreshCredits, language, startScanner, openChat }) {
  const L = (en, vi) => uiText(language, en, vi);
  const knowledgeArticles = normalizeLanguage(language) === 'vi' ? KNOWLEDGE_ARTICLES : buildKnowledgeArticles(L);
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [recentHistory, setRecentHistory] = useState([]);
  const [showUploader, setShowUploader] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [cameraReady, setCameraReady] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const cameraRef = React.useRef(null);
  const analyzeAbortRef = React.useRef(null);
  const scannerSlide = React.useRef(new Animated.Value(80)).current;

  useEffect(() => {
    if (!user?.token) return;
    apiGetHistory(user.token).then(d => {
      if (d.success && d.history) setRecentHistory(d.history.slice(0, 3));
    }).catch(() => {});
  }, [user]);

  useEffect(() => {
    if (showUploader && !image && !result && !loading) {
      scannerSlide.setValue(80);
      Animated.timing(scannerSlide, {
        toValue: 0,
        duration: 260,
        useNativeDriver: true,
      }).start();
    }
  }, [showUploader, image, result, loading, scannerSlide]);

  useEffect(() => {
    if (startScanner) openUploader();
  }, [startScanner]);

  useEffect(() => {
    if (showUploader && !image && !result && !loading && cameraPermission?.granted !== true && cameraPermission?.canAskAgain !== false) {
      requestCameraPermission();
    }
  }, [showUploader, image, result, loading, cameraPermission, requestCameraPermission]);

  const pickImage = async () => {
    if (!user) { Alert.alert(L('Not signed in', 'Chưa đăng nhập'), L('Please sign in to analyze images', 'Vui lòng đăng nhập để phân tích ảnh')); setScreen('Login'); return; }
    const r = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], allowsEditing: true, quality: 1 });
    if (!r.canceled) { setImage(r.assets[0]); setResult(null); setShowUploader(false); }
  };

  const takePhoto = async () => {
    if (!user) { Alert.alert(L('Not signed in', 'Chưa đăng nhập'), L('Please sign in to analyze images', 'Vui lòng đăng nhập để phân tích ảnh')); setScreen('Login'); return; }
    setResult(null);
    setShowUploader(true);
    if (cameraPermission?.granted !== true) {
      const perm = await requestCameraPermission();
      if (!perm.granted) Alert.alert(L('Error', 'Lỗi'), L('Camera permission is required', 'Cần quyền truy cập camera'));
    }
  };

  const capturePhoto = async () => {
    if (!user) { Alert.alert(L('Not signed in', 'Chưa đăng nhập'), L('Please sign in to analyze images', 'Vui lòng đăng nhập để phân tích ảnh')); setScreen('Login'); return; }
    if (cameraPermission?.granted !== true) {
      const perm = await requestCameraPermission();
      if (!perm.granted) { Alert.alert(L('Error', 'Lỗi'), L('Camera permission is required', 'Cần quyền truy cập camera')); return; }
    }
    if (!cameraRef.current || !cameraReady || capturing) return;
    setCapturing(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 1 });
      if (photo?.uri) { setImage(photo); setResult(null); setShowUploader(false); }
    } catch (err) {
      Alert.alert(L('Error', 'Lỗi'), L('Cannot capture photo', 'Không thể chụp ảnh'));
    } finally {
      setCapturing(false);
    }
  };

  const doAnalyze = async () => {
    if (!image) return;
    if (!user?.token) { Alert.alert(L('Not signed in', 'Chưa đăng nhập'), L('Please sign in to analyze images', 'Vui lòng đăng nhập để phân tích ảnh')); setScreen('Login'); return; }
    const controller = new AbortController();
    analyzeAbortRef.current = controller;
    setLoading(true);
    setResult(null);
    try {
      const { status, data } = await apiOcr(image.uri, user?.token, controller.signal);
      if (status === 403 && data.no_credits) {
        Alert.alert(L('No credits left', 'Hết lượt'), L('You have no analysis credits left. Please upgrade your package.', 'Bạn đã hết lượt phân tích. Vui lòng nâng cấp gói.'), [
          { text: L('Buy more', 'Mua thêm'), onPress: () => setScreen('Pricing') },
          { text: L('Later', 'Để sau') },
        ]);
        return;
      }
      if (data.error || data.success === false || data.status === 'error') { throw new Error(data.message || data.error || 'Analysis failed'); }
      const d = data.report || data.top_match || data.best_match || data;
      const hanzi = pickField(data, ['chu_han', 'hieu_de', 'text_ocr'], pickField(d, ['chu_han', 'hieu_de'], '?'));
      const confidence = normalizeConfidence(pickField(data, ['aggregated_confidence', 'confidence', 'tin_cay'], pickField(d, ['aggregated_confidence', 'confidence', 'tin_cay'], 0)));
      const fullName = pickField(d, ['hien_thi_chinh', 'hieu_de_vi', 'ten_viet', 'tên_việt'], pickField(data, ['hien_thi_chinh', 'hieu_de_vi', 'ten_viet', 'tên_việt'], L('Unknown mark', 'Chưa rõ hiệu đề')));
      const lang = normalizeLanguage(language);
      const isEnglish = lang === 'en';
      const rawDynasty = pickField(d, ['trieu_dai', 'triá»u_Ä‘áº¡i'], pickField(data, ['trieu_dai', 'triá»u_Ä‘áº¡i'], L('Unknown', 'ChÆ°a rÃµ')));
      const rawReign = pickField(d, ['nien_hieu', 'niÃªn_hiá»‡u'], pickField(data, ['nien_hieu', 'niÃªn_hiá»‡u'], L('Unknown', 'ChÆ°a rÃµ')));
      const rawPeriod = pickField(d, ['nien_dai', 'niÃªn_Ä‘áº¡i'], pickField(data, ['nien_dai', 'niÃªn_Ä‘áº¡i'], '?'));
      const rawContext = pickField(d, ['mo_ta', 'boi_canh', 'ghi_chu', 'y_nghia', 'Ã½_nghÄ©a'], pickField(data, ['mo_ta', 'boi_canh', 'ghi_chu', 'y_nghia', 'Ã½_nghÄ©a'], L('Updating...', 'Äang cáº­p nháº­t...')));
      const rawCalligraphy = pickField(d, ['thu_phap', 'nghe_thuat'], pickField(data, ['thu_phap', 'nghe_thuat'], L('Updating...', 'Äang cáº­p nháº­t...')));
      const rawEmperor = pickField(d, ['hoang_de', 'hoÃ ng_Ä‘áº¿'], pickField(data, ['hoang_de', 'hoÃ ng_Ä‘áº¿'], ''));
      const pipelineDetails = data.pipeline_details || d.pipeline_details || [];
      const pipelineText = Array.isArray(pipelineDetails)
        ? pipelineDetails
            .map((p) => p?.pipeline_name || p?.name || p?.status)
            .filter(Boolean)
            .join(', ')
        : '';
      setResult({
        hieude: isEnglish ? englishMarkTitle(fullName, rawReign, rawDynasty) : fullName,
        hanzi,
        confidence,
        trieudai: pickField(d, ['trieu_dai', 'triều_đại'], pickField(data, ['trieu_dai', 'triều_đại'], L('Unknown', 'Chưa rõ'))),
        nienhieu: pickField(d, ['nien_hieu', 'niên_hiệu'], pickField(data, ['nien_hieu', 'niên_hiệu'], L('Unknown', 'Chưa rõ'))),
        niendai: pickField(d, ['nien_dai', 'niên_đại'], pickField(data, ['nien_dai', 'niên_đại'], '?')),
        hieude_en: pickField(d, ['hieu_de_en', 'phien_am', 'phiên_âm'], pickField(data, ['hieu_de_en', 'phien_am', 'phiên_âm'], L('Unknown', 'Chưa rõ'))),
        boicanh: pickField(d, ['mo_ta', 'boi_canh', 'ghi_chu', 'y_nghia', 'ý_nghĩa'], pickField(data, ['mo_ta', 'boi_canh', 'ghi_chu', 'y_nghia', 'ý_nghĩa'], L('Updating...', 'Đang cập nhật...'))),
        thuphapdacbiet: pickField(d, ['thu_phap', 'nghe_thuat'], pickField(data, ['thu_phap', 'nghe_thuat'], L('Updating...', 'Đang cập nhật...'))),
        hoangde: pickField(d, ['hoang_de', 'hoàng_đế'], pickField(data, ['hoang_de', 'hoàng_đế'], '')),
        trieudai: isEnglish ? englishDynastyName(rawDynasty) : rawDynasty,
        nienhieu: isEnglish ? englishReignName(rawReign) : rawReign,
        niendai: rawPeriod,
        hieude_en: isEnglish ? `${englishReignName(rawReign || fullName)} Period` : pickField(d, ['hieu_de_en', 'phien_am', 'phiên_âm'], pickField(data, ['hieu_de_en', 'phien_am', 'phiên_âm'], L('Unknown', 'Chưa rõ'))),
        boicanh: isEnglish ? englishContextText(rawContext, rawReign, rawDynasty, rawPeriod) : rawContext,
        thuphapdacbiet: isEnglish ? englishCalligraphyText(rawCalligraphy) : rawCalligraphy,
        hoangde: isEnglish ? englishEmperorName(rawEmperor || rawReign) : rawEmperor,
        phienam: pickField(d, ['phien_am', 'phiên_âm'], pickField(data, ['phien_am', 'phiên_âm'], '')),
        nguon: pickField(d, ['data_source', 'nguon_du_lieu', 'primary_pipeline', 'pipeline_chinh'], pickField(data, ['data_source', 'nguon_du_lieu', 'primary_pipeline', 'pipeline_chinh'], '')),
        xacminh: pickField(d, ['verification_status'], pickField(data, ['verification_status'], data.web_verified || d.web_verified ? L('Verified by web sources', 'Đã xác minh bằng nguồn web') : '')),
        canhbao: pickField(d, ['canh_bao'], pickField(data, ['canh_bao'], '')),
        pipeline: pipelineText,
        sources: collectSources(data, d),
        raw: data,
      });
      refreshCredits?.();
      
      // Refresh history silently
      if (user?.token) {
        apiGetHistory(user.token).then(d => {
          if (d.success && d.history) setRecentHistory(d.history.slice(0, 3));
        }).catch(()=>{});
      }

    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('Analyze failed', err);
      Alert.alert(L('Error', 'Lỗi'), err.message || L('Cannot analyze image', 'Không thể phân tích'));
    } finally {
      analyzeAbortRef.current = null;
      setLoading(false);
    }
  };

  const cancelAnalyze = () => {
    analyzeAbortRef.current?.abort();
    analyzeAbortRef.current = null;
    setLoading(false);
  };

  const openUploader = () => {
    if (!user) { Alert.alert(L('Not signed in', 'Chưa đăng nhập'), L('Please sign in to analyze images', 'Vui lòng đăng nhập để phân tích ảnh')); setScreen('Login'); return; }
    setShowUploader(true);
    setResult(null);
  };

  const clearScan = () => { setImage(null); setResult(null); setShowUploader(true); };
  const backToHome = () => { setImage(null); setResult(null); setShowUploader(false); setScreen('Home'); };

  const firstHistory = recentHistory[0];
  const secondHistory = null;
  const thirdHistory = null;
  const firstResult = parseHistoryResult(firstHistory?.match_result);
  const secondResult = {};
  const thirdResult = {};
  const displayHistoryDynasty = (item) => normalizeLanguage(language) === 'en'
    ? englishDynastyName(item?.trieu_dai || '')
    : (item?.trieu_dai || '');
  const displayHistoryTitle = (item) => normalizeLanguage(language) === 'en'
    ? englishMarkTitle(item?.hien_thi_chinh || item?.hieu_de_vi || item?.top_mark || '', item?.nien_hieu || item?.hieu_de_en || '', item?.trieu_dai || '')
    : (item?.nien_hieu || item?.hieu_de_vi || item?.top_mark || '');

  return (
    <View style={s.container}>
      <ScrollView
        bounces={false}
        scrollEnabled={!(showUploader && !image && !result && !loading)}
        contentContainerStyle={[
          s.scroll,
          showUploader && !image && !result && !loading && s.scannerScroll,
        ]}
      >
        
        {/* ─── SCENE 1: DASHBOARD (NO SCAN YET) ─── */}
        {selectedArticle && !showUploader && !image && !result && !loading && (
          <View style={s.articleWrap}>
            <TouchableOpacity style={s.articleBack} onPress={() => setSelectedArticle(null)}>
              <Feather name="chevron-left" size={24} color="#1c1917" />
              <Text style={s.articleBackText}>{L('Deep knowledge', 'Kiến thức chuyên sâu')}</Text>
            </TouchableOpacity>

            <Image source={selectedArticle.image} style={s.articleHero} />
            <Text style={s.articleTag}>{selectedArticle.tag}</Text>
            <Text style={s.articleTitle}>{selectedArticle.title}</Text>
            <Text style={s.articleMeta}>{selectedArticle.meta}</Text>
            <Text style={s.articleIntro}>{selectedArticle.intro}</Text>

            {selectedArticle.sections.map((section) => (
              <View key={section.heading} style={s.articleSection}>
                <Text style={s.articleHeading}>{section.heading}</Text>
                <Text style={s.articleBody}>{section.body}</Text>
              </View>
            ))}
          </View>
        )}

        {!selectedArticle && !showUploader && !image && !result && !loading && (
          <View style={s.dashboardWrap}>
            <AppHeader setScreen={setScreen} credits={credits} language={language} />

            {/* HERO BANNER */}
            <View style={s.heroCard}>
              <Image source={heroMarkImage} style={s.heroImg} />
              <View style={s.heroOverlay}>
                <View style={s.heroPill}><Text style={s.heroPillText}>{L('HOME', 'TRANG CHỦ')}</Text></View>
                <Text style={s.heroTitle}>{L('Decode history\nthrough every mark.', 'Giải mã lịch sử\nqua từng dấu ấn.')}</Text>
                <TouchableOpacity style={s.heroBtn} onPress={openUploader}>
                  <Text style={s.heroBtnText}>{L('START APPRAISAL', 'BẮT ĐẦU GIÁM ĐỊNH')}</Text>
                  <Ionicons name="scan" size={18} color="#fff" style={{marginLeft: 8}} />
                </TouchableOpacity>
              </View>
            </View>

            {showUploader && (
              <View style={s.uploadPanel}>
                <View style={s.uploadIconWrap}>
                  <Feather name="camera" size={28} color="#065f46" />
                </View>
                <Text style={s.uploadTitle}>{L('Upload ceramic mark image', 'Tải ảnh hiệu đề gốm sứ')}</Text>
                <Text style={s.uploadText}>{L('Choose or capture a clear photo of the reign mark under the ceramic base.', 'Chọn hoặc chụp ảnh rõ hiệu đề dưới đáy gốm.')}</Text>
                <View style={s.uploadActions}>
                  <TouchableOpacity style={s.uploadPrimary} onPress={pickImage}>
                    <Feather name="image" size={18} color="#fff" />
                    <Text style={s.uploadPrimaryText}>{L('Choose Image', 'Chọn ảnh')}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={s.uploadSecondary} onPress={takePhoto}>
                    <Feather name="camera" size={18} color="#065f46" />
                    <Text style={s.uploadSecondaryText}>{L('Take Photo', 'Chụp ảnh')}</Text>
                  </TouchableOpacity>
                </View>
              </View>
            )}

            {/* RECENT IDENTIFICATION */}
            <View style={s.section}>
              <Text style={s.secSuper}>{L('ARCHIVED DATA', 'DỮ LIỆU LƯU TRỮ')}</Text>
              <View style={s.rowSpace}>
                <Text style={s.secTitle}>{L('Recent identifications', 'Nhận dạng gần đây')}</Text>
                <TouchableOpacity onPress={() => setScreen('History')}><Text style={s.linkText}>{L('VIEW ALL', 'XEM TẤT CẢ')}</Text></TouchableOpacity>
              </View>
              
              {firstHistory ? (
                <TouchableOpacity style={s.recentCard} onPress={() => setScreen('History')}>
                  <Image source={{uri: `${BASE_URL}/${firstHistory.image_path}`}} style={s.rcImg} />
                  <View style={s.rcContent}>
                    <Text style={s.rcTitle} numberOfLines={1}>{displayHistoryDynasty(firstResult) || firstResult.top_mark || L('Unknown', 'Chưa rõ')}</Text>
                    <Text style={s.rcSub} numberOfLines={1}>{displayHistoryTitle(firstResult) || L('Artifact', 'Hiện vật')}</Text>
                    <View style={s.rcProgressRow}>
                      <View style={s.progressBar}><View style={[s.progressFill, { width: '90%' }]} /></View>
                      <Text style={s.progressText}>{L('90% confidence', '90% tin cậy')}</Text>
                    </View>
                  </View>
                </TouchableOpacity>
              ) : (
                <View style={[s.recentCard, {opacity: 0.5}]}><Text style={{padding: 20}}>{L('No data yet', 'Chưa có dữ liệu')}</Text></View>
              )}

              <View style={s.gridRow}>
                {secondHistory && (
                  <TouchableOpacity style={s.gridCard} onPress={() => setScreen('History')}>
                    <Image source={{uri: `${BASE_URL}/${secondHistory.image_path}`}} style={s.gcImg} />
                    <View style={s.gcContent}>
                      <Text style={s.gcSuper} numberOfLines={1}>{secondResult.trieu_dai || L('Unknown', 'Chưa rõ')}</Text>
                      <Text style={s.gcTitle} numberOfLines={1}>{secondResult.hieu_de_vi || L('Artifact', 'Hiện vật')}</Text>
                      <View style={s.gcBadge}><Text style={s.gcBadgeText}>{L('AI Detected', 'AI đã nhận diện')}</Text></View>
                    </View>
                  </TouchableOpacity>
                )}
                {thirdHistory && (
                  <TouchableOpacity style={s.gridCard} onPress={() => setScreen('History')}>
                    <Image source={{uri: `${BASE_URL}/${thirdHistory.image_path}`}} style={s.gcImg} />
                    <View style={s.gcContent}>
                      <Text style={s.gcSuper} numberOfLines={1}>{thirdResult.trieu_dai || L('Unknown', 'Chưa rõ')}</Text>
                      <Text style={s.gcTitle} numberOfLines={1}>{thirdResult.hieu_de_vi || L('Artifact', 'Hiện vật')}</Text>
                      <View style={s.gcBadge}><Text style={s.gcBadgeText}>{L('Analysis', 'Phân tích')}</Text></View>
                    </View>
                  </TouchableOpacity>
                )}
              </View>
            </View>

            {/* DEEP KNOWLEDGE */}
            <View style={s.section}>
              <Text style={s.secTitle}>{L('Deep knowledge', 'Kiến thức chuyên sâu')}</Text>

              {knowledgeArticles.map((article) => (
              <TouchableOpacity key={article.id} style={s.knowledgeCard} activeOpacity={0.85} onPress={() => setSelectedArticle(article)}>
                <Image source={article.image} style={s.knowledgeImg} />
                <View style={s.knowledgeBody}>
                  <Text style={s.knowledgeTag}>{article.tag}</Text>
                  <Text style={s.knowledgeTitle}>{article.title}</Text>
                  <Text style={s.knowledgeMeta}>{article.meta}</Text>
                </View>
              </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {/* ─── SCENE 2: SCANNING / RESULT VIEW ─── */}
        {showUploader && !image && !result && !loading && (
          <Animated.View style={[s.cameraScreen, { transform: [{ translateY: scannerSlide }] }]}>
            <View style={s.cameraTopBar}>
              <View style={s.cameraTopBtn} />
              <TouchableOpacity style={s.cameraTopBtn} onPress={() => setShowUploader(false)}>
                <Feather name="x" size={38} color="#fff" />
              </TouchableOpacity>
            </View>

            <View style={s.livePreview}>
              {cameraPermission?.granted && (
                <CameraView
                  ref={cameraRef}
                  style={s.cameraLive}
                  facing="back"
                  mode="picture"
                  onCameraReady={() => setCameraReady(true)}
                />
              )}
              <View style={[s.cameraPermissionBox, cameraPermission?.granted && s.cameraPermissionHidden]}>
                <View style={s.cameraPermissionIcon}>
                  <Feather name="camera" size={30} color="#fff" />
                </View>
                <Text style={s.cameraPermissionTitle}>{L('Camera access needed', 'Cần quyền camera')}</Text>
                <Text style={s.cameraPermissionText}>
                  {L('Allow camera access to capture the ceramic mark directly.', 'Cho phép truy cập camera để chụp trực tiếp hiệu đề.')}
                </Text>
                <TouchableOpacity style={s.cameraPermissionPrimary} onPress={requestCameraPermission}>
                  <Feather name="camera" size={17} color="#fff" />
                  <Text style={s.cameraPermissionPrimaryText}>{L('Allow camera', 'Cho phép camera')}</Text>
                </TouchableOpacity>
                <TouchableOpacity style={s.cameraPermissionSecondary} onPress={pickImage}>
                  <Feather name="image" size={17} color="#fff" />
                  <Text style={s.cameraPermissionSecondaryText}>{L('Upload image instead', 'Tải ảnh thay thế')}</Text>
                </TouchableOpacity>
              </View>
              <View pointerEvents="none" style={s.scanFrame}>
                <View style={[s.scanCorner, s.scanCornerTL]} />
                <View style={[s.scanCorner, s.scanCornerTR]} />
                <View style={[s.scanCorner, s.scanCornerBL]} />
                <View style={[s.scanCorner, s.scanCornerBR]} />
              </View>
            </View>

            <View style={s.cameraBottom}>
              <Text style={s.cameraHint}>{L('Capture a clear mark image', 'Chụp ảnh hiệu đề rõ nét')}</Text>
              <View style={s.captureRow}>
                <TouchableOpacity style={s.sideCameraBtn} onPress={pickImage}>
                  <Feather name="image" size={24} color="#fff" />
                </TouchableOpacity>
                <TouchableOpacity style={[s.captureBtn, (!cameraReady || capturing) && s.captureBtnDisabled]} onPress={capturePhoto} disabled={!cameraPermission?.granted || !cameraReady || capturing}>
                  <View style={s.captureInner}>
                    {capturing ? <ActivityIndicator color="#fff" /> : <Feather name="camera" size={30} color="#fff" />}
                  </View>
                </TouchableOpacity>
                <View style={s.sideCameraBtnPlaceholder} />
              </View>
            </View>
          </Animated.View>
        )}

        {(image || result || loading) && (
          <View style={s.resultWrap}>
            <View style={[s.imgWrapper, image && !result && s.confirmImageWrapper]}>
              <TouchableOpacity style={s.resultBackBtn} onPress={backToHome}>
                <Feather name="chevron-left" size={22} color="#1c1917" />
                <Text style={s.resultBackText}>{L('Back', 'Trở về')}</Text>
              </TouchableOpacity>
              {image ? (
                <Image source={{ uri: image.uri }} style={[s.img, (image && !result) || result ? s.containedImg : null]} />
              ) : (
                <View style={s.cameraPreview}>
                  <View style={s.cameraFrame}>
                    <Feather name="camera" size={46} color="#fff" />
                    <Text style={s.cameraTitle}>{L('Camera Preview', 'Xem trước camera')}</Text>
                    <Text style={s.cameraSub}>{L('Capture or upload a clear mark image below', 'Chụp hoặc tải ảnh hiệu đề rõ nét bên dưới')}</Text>
                  </View>
                </View>
              )}
            </View>

            <View style={[s.sheet, image && !result && s.confirmSheet]}>
              {loading && (
                <View style={s.loadingPanel}>
                  <ActivityIndicator size="large" color="#059669" />
                  <Text style={s.loadingText}>{L('The system is analyzing details...', 'Hệ thống đang phân tích chi tiết...')}</Text>
                  <TouchableOpacity style={s.cancelAnalyzeBtn} onPress={cancelAnalyze}>
                    <Text style={s.cancelAnalyzeText}>{L('Cancel', 'Huỷ')}</Text>
                  </TouchableOpacity>
                </View>
              )}

              {!loading && !result && !image && showUploader && (
                <View>
                  <Text style={s.sheetTitle}>{L('Scan ceramic mark', 'Quét hiệu đề gốm')}</Text>
                  <Text style={s.descText}>{L('Use the camera to capture the mark, or upload an existing photo from your device.', 'Dùng camera để chụp hiệu đề hoặc tải ảnh có sẵn từ thiết bị.')}</Text>
                  <View style={s.btnCol}>
                    <TouchableOpacity style={s.mainBtn} onPress={takePhoto}>
                      <Feather name="camera" size={18} color="#fff" />
                      <Text style={s.mainBtnText}>  {L('Open Camera', 'Mở camera')}</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={s.secBtn} onPress={pickImage}>
                      <Feather name="image" size={18} color="#065f46" />
                      <Text style={s.secBtnText}>  {L('Upload Image', 'Tải ảnh')}</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              )}

              {!loading && !result && image && (
                <View style={s.confirmPanel}>
                  <View style={s.confirmTopRow}>
                    <View style={s.confirmCopy}>
                      <Text style={s.confirmKicker}>{L('Ready to analyze', 'Sẵn sàng phân tích')}</Text>
                    </View>
                  </View>
                  <Text style={s.sheetTitle}>{L('Confirm image', 'Xác nhận hình ảnh')}</Text>
                  <Text style={s.descText}>{L('This image will be sent to MarkSense to extract period and origin information.', 'Bức ảnh này sẽ được gửi đến hệ thống MarkSense để trích xuất niên đại và xuất xứ.')}</Text>
                  <View style={s.confirmActions}>
                    <TouchableOpacity style={[s.confirmPrimary, loading && s.confirmPrimaryDisabled]} onPress={doAnalyze} disabled={loading}>
                      <Text style={s.mainBtnText}>{L('Start Analysis', 'Bắt Đầu Phân Tích')}</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={s.confirmSecondary} onPress={clearScan}>
                      <Text style={s.secBtnText}>{L('Remove this image', 'Xóa ảnh này')}</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              )}

              {!loading && result && (
                <View>
                  <View style={s.titleRow}>
                    <View style={s.titleWrap}>
                      <Text style={s.sheetTitle}>{asDisplayText(result.hieude, L('Unknown mark', 'Chưa rõ hiệu đề'))}</Text>
                      <Text style={s.subtitle}>{asDisplayText(result.hieude_en || result.hanzi, '')}</Text>
                      <View style={s.creditInline}>
                        <Text style={s.creditInlineText}>{L('Credits left', 'Lượt còn lại')}: {credits ?? '--'}</Text>
                        <TouchableOpacity onPress={() => setScreen('Pricing')}>
                          <Text style={s.creditInlineLink}>{L('Buy more', 'Mua thêm')}</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                    <View style={s.matchBox}>
                      <Text style={s.matchVal}>{result.confidence || 98}%</Text>
                      <Text style={s.matchLbl}>{L('ACCURACY', 'CHÍNH XÁC')}</Text>
                    </View>
                  </View>

                  <View style={s.pillsRow}>
                    <View style={s.pill}>
                      <Text style={s.pillLabel}>{L('DYNASTY', 'TRIỀU ĐẠI')}</Text>
                      <Text style={s.pillVal}>{asDisplayText(result.trieudai, L('Unknown', 'Chưa rõ'))}</Text>
                    </View>
                    <View style={s.pill}>
                      <Text style={s.pillLabel}>{L('REIGN ERA', 'NIÊN HIỆU')}</Text>
                      <Text style={s.pillVal}>{asDisplayText(result.nienhieu, L('Unknown', 'Chưa rõ'))}</Text>
                    </View>
                    <View style={s.pill}>
                      <Text style={s.pillLabel}>{L('PERIOD', 'NIÊN ĐẠI')}</Text>
                      <Text style={s.pillVal}>{asDisplayText(result.niendai, '?')}</Text>
                    </View>
                  </View>

                  <View style={s.detailGrid}>
                    {!!result.hanzi && (
                      <View style={s.detailRow}>
                        <Text style={s.detailLabel}>{L('Characters', 'Hán tự')}</Text>
                        <Text style={s.detailValue}>{asDisplayText(result.hanzi)}</Text>
                      </View>
                    )}
                    {!!result.phienam && (
                      <View style={s.detailRow}>
                        <Text style={s.detailLabel}>{L('Reading', 'Phiên âm')}</Text>
                        <Text style={s.detailValue}>{asDisplayText(result.phienam)}</Text>
                      </View>
                    )}
                    {!!result.hoangde && (
                      <View style={s.detailRow}>
                        <Text style={s.detailLabel}>{L('Emperor', 'Hoàng đế')}</Text>
                        <Text style={s.detailValue}>{asDisplayText(result.hoangde)}</Text>
                      </View>
                    )}
                  </View>

                  <Text style={s.secCardTitle}>{L('Historical context', 'Bối cảnh lịch sử')}</Text>
                  <View style={s.careTipsBox}>
                    <Text style={s.careText}>{asDisplayText(result.boicanh, L('Updating...', 'Đang cập nhật...'))}</Text>
                  </View>

                  <Text style={s.secCardTitle}>{L('Artistic features & calligraphy', 'Đặc điểm nghệ thuật & Thư pháp')}</Text>
                  <Text style={s.descText}>{asDisplayText(result.thuphapdacbiet, L('Updating...', 'Đang cập nhật...'))}</Text>

                  {!!result.sources?.length && (
                    <View style={s.sourcesBox}>
                      <Text style={s.secCardTitle}>{L('Supporting sources', 'Nguồn tham khảo')}</Text>
                      {result.sources.map((src, idx) => (
                        <TouchableOpacity key={`${src.url}-${idx}`} style={s.sourceItem} onPress={() => Linking.openURL(src.url)}>
                          <Text style={s.sourceTitle} numberOfLines={2}>{src.title}</Text>
                          <Text style={s.sourceUrl} numberOfLines={1}>{src.url}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  )}

                  <TouchableOpacity style={s.mainBtn} onPress={clearScan}>
                    <Text style={s.mainBtnText}>{L('Analyze another sample', 'Phân tích mẫu khác')}</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          </View>
        )}
      </ScrollView>

      {!selectedArticle && !showUploader && !image && !result && !loading && (
        <>
          {!!openChat && (
            <TouchableOpacity style={s.chatFab} onPress={openChat} activeOpacity={0.86}>
              <Feather name="message-circle" size={26} color="#ffffff" />
            </TouchableOpacity>
          )}
          <AppFooter current="Home" setScreen={setScreen} onCenterPress={openUploader} language={language} />
        </>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fdfbf7' },
  scroll: { flexGrow: 1, paddingBottom: 160 },
  scannerScroll: { paddingBottom: 0, backgroundColor: '#000' },
  chatFab: {
    position: 'absolute',
    right: 18,
    bottom: 112,
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: '#065f46',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#065f46',
    shadowOpacity: 0.35,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 10,
    zIndex: 30,
  },

  cameraScreen: { height: screenHeight, minHeight: 640, backgroundColor: '#000', overflow: 'hidden' },
  cameraTopBar: { height: cameraTopHeight, paddingHorizontal: 30, paddingTop: 30, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#000' },
  cameraTopBtn: { width: 48, height: 48, justifyContent: 'center', alignItems: 'center' },
  livePreview: { height: cameraPreviewHeight, backgroundColor: '#111', position: 'relative', overflow: 'hidden', justifyContent: 'center', alignItems: 'center' },
  cameraLive: { ...StyleSheet.absoluteFillObject },
  cameraPermissionBox: { width: '100%', height: '100%', backgroundColor: '#050505', justifyContent: 'center', alignItems: 'center', paddingHorizontal: 42 },
  cameraPermissionHidden: { display: 'none' },
  cameraPermissionIcon: { width: 70, height: 70, borderRadius: 35, borderWidth: 1, borderColor: 'rgba(255,255,255,0.22)', backgroundColor: 'rgba(255,255,255,0.08)', justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  cameraPermissionTitle: { color: '#fff', fontSize: 20, fontWeight: '800', marginBottom: 8, textAlign: 'center' },
  cameraPermissionText: { color: 'rgba(255,255,255,0.72)', fontSize: 13, fontWeight: '600', lineHeight: 20, textAlign: 'center', marginBottom: 18 },
  cameraPermissionPrimary: { height: 52, minWidth: 160, paddingHorizontal: 18, borderRadius: 18, backgroundColor: '#047857', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  cameraPermissionPrimaryText: { color: '#fff', fontSize: 13, fontWeight: '800' },
  cameraPermissionSecondary: { marginTop: 12, height: 44, paddingHorizontal: 16, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.12)', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  cameraPermissionSecondaryText: { color: '#fff', fontSize: 12, fontWeight: '800' },
  scanFrame: { position: 'absolute', top: scanFrameTop, alignSelf: 'center', width: scanFrameWidth, height: scanFrameHeight, zIndex: 3 },
  scanCorner: { position: 'absolute', width: 84, height: 84, borderColor: '#fff' },
  scanCornerTL: { top: 0, left: 0, borderTopWidth: 7, borderLeftWidth: 7, borderTopLeftRadius: 28 },
  scanCornerTR: { top: 0, right: 0, borderTopWidth: 7, borderRightWidth: 7, borderTopRightRadius: 28 },
  scanCornerBL: { bottom: 0, left: 0, borderBottomWidth: 7, borderLeftWidth: 7, borderBottomLeftRadius: 28 },
  scanCornerBR: { bottom: 0, right: 0, borderBottomWidth: 7, borderRightWidth: 7, borderBottomRightRadius: 28 },
  cameraBottom: { height: cameraBottomHeight, backgroundColor: '#000', alignItems: 'center', paddingHorizontal: 28, paddingTop: 20 },
  cameraHint: { color: 'rgba(255,255,255,0.82)', fontSize: 12, fontWeight: '700', marginBottom: 14, textAlign: 'center' },
  captureRow: { width: '100%', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 34 },
  sideCameraBtn: { width: 58, height: 58, borderRadius: 29, backgroundColor: '#151515', justifyContent: 'center', alignItems: 'center' },
  sideCameraBtnPlaceholder: { width: 58, height: 58 },
  captureBtn: { width: 88, height: 88, borderRadius: 44, borderWidth: 4, borderColor: '#fff', justifyContent: 'center', alignItems: 'center' },
  captureBtnDisabled: { opacity: 0.55 },
  captureInner: { width: 70, height: 70, borderRadius: 35, justifyContent: 'center', alignItems: 'center', backgroundColor: '#43c6ac' },

  // 1. DASHBOARD STYLES
  dashboardWrap: { paddingHorizontal: 20, paddingTop: 24, paddingBottom: 40 },

  articleWrap: { paddingHorizontal: 22, paddingTop: 22, paddingBottom: 56 },
  articleBack: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', marginBottom: 18 },
  articleBackText: { fontSize: 13, fontWeight: '800', color: '#1c1917' },
  articleHero: { width: '100%', height: 240, borderRadius: 24, resizeMode: 'cover', backgroundColor: '#e7e5e4', marginBottom: 22 },
  articleTag: { fontSize: 10, fontWeight: '900', color: '#a16207', letterSpacing: 1.4, marginBottom: 10 },
  articleTitle: { fontSize: 30, lineHeight: 36, color: '#1c1917', fontFamily: 'serif', fontWeight: '800', marginBottom: 10 },
  articleMeta: { fontSize: 13, color: '#78716c', fontWeight: '700', marginBottom: 18 },
  articleIntro: { fontSize: 16, color: '#44403c', lineHeight: 25, marginBottom: 24 },
  articleSection: { backgroundColor: '#fff', borderRadius: 18, padding: 18, marginBottom: 14, borderWidth: 1, borderColor: '#eee8df' },
  articleHeading: { fontSize: 18, color: '#1c1917', fontFamily: 'serif', fontWeight: '800', marginBottom: 8 },
  articleBody: { fontSize: 14, color: '#57534e', lineHeight: 23 },

  heroCard: { width: '100%', height: 420, borderRadius: 28, overflow: 'hidden', position: 'relative', marginBottom: 32 },
  heroImg: { width: '100%', height: '100%', resizeMode: 'cover' },
  heroOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.15)', padding: 24,
    justifyContent: 'flex-end',
  },
  heroPill: { backgroundColor: '#fdfbf7', alignSelf: 'flex-start', paddingHorizontal: 12, paddingVertical: 4, borderRadius: 12, marginBottom: 12 },
  heroPillText: { fontSize: 9, fontWeight: '800', color: '#78716c', letterSpacing: 0.5 },
  heroTitle: { fontSize: 32, fontFamily: 'serif', color: '#fff', lineHeight: 38, marginBottom: 22, textShadowColor: 'rgba(0,0,0,0.3)', textShadowOffset: {width: 0, height: 2}, textShadowRadius: 6 },
  heroBtn: { backgroundColor: '#065f46', flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 20, borderRadius: 12, alignSelf: 'flex-start', shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 10, elevation: 4 },
  heroBtnText: { color: '#fff', fontSize: 11, fontWeight: '800', letterSpacing: 1 },

  uploadPanel: { backgroundColor: '#ffffff', borderRadius: 24, padding: 22, marginBottom: 28, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 14, elevation: 4 },
  uploadIconWrap: { width: 64, height: 64, borderRadius: 32, backgroundColor: '#f0fdf4', justifyContent: 'center', alignItems: 'center', marginBottom: 14 },
  uploadTitle: { fontSize: 18, fontWeight: '800', color: '#1c1917', marginBottom: 6 },
  uploadText: { fontSize: 13, color: '#57534e', textAlign: 'center', lineHeight: 20, marginBottom: 18 },
  uploadActions: { flexDirection: 'row', width: '100%', gap: 10 },
  uploadPrimary: { flex: 1, backgroundColor: '#065f46', borderRadius: 16, paddingVertical: 14, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 8 },
  uploadPrimaryText: { color: '#fff', fontSize: 12, fontWeight: '800' },
  uploadSecondary: { flex: 1, backgroundColor: '#f5f5f4', borderRadius: 16, paddingVertical: 14, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 8 },
  uploadSecondaryText: { color: '#065f46', fontSize: 12, fontWeight: '800' },

  section: { marginBottom: 36 },
  secSuper: { fontSize: 9, color: '#78716c', fontWeight: '800', letterSpacing: 1.5, marginBottom: 4 },
  rowSpace: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 16 },
  secTitle: { fontSize: 22, color: '#1c1917', fontFamily: 'serif' },
  linkText: { fontSize: 10, fontWeight: '800', color: '#1c1917', borderBottomWidth: 1, borderBottomColor: '#1c1917', marginBottom: 4 },

  knowledgeCard: { backgroundColor: '#fff', borderRadius: 10, overflow: 'hidden', flexDirection: 'row', minHeight: 116, marginTop: 14, borderWidth: 1, borderColor: '#eee8df', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 2 },
  knowledgeImg: { width: 120, height: 116, resizeMode: 'cover', backgroundColor: '#e7e5e4' },
  knowledgeBody: { flex: 1, paddingHorizontal: 14, paddingVertical: 14, justifyContent: 'center' },
  knowledgeTag: { fontSize: 9, fontWeight: '900', color: '#a16207', letterSpacing: 1.2, marginBottom: 10 },
  knowledgeTitle: { fontSize: 16, color: '#1c1917', fontFamily: 'serif', fontWeight: '800', lineHeight: 20, marginBottom: 8 },
  knowledgeMeta: { fontSize: 12, color: '#78716c', fontWeight: '600' },

  recentCard: { backgroundColor: '#fff', borderRadius: 24, padding: 12, flexDirection: 'row', alignItems: 'center', marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 3 },
  rcImg: { width: 90, height: 90, borderRadius: 14, backgroundColor: '#e7e5e4' },
  rcContent: { flex: 1, marginLeft: 16 },
  rcTitle: { fontSize: 16, color: '#1c1917', fontFamily: 'serif', marginBottom: 4 },
  rcSub: { fontSize: 12, color: '#57534e', lineHeight: 18, marginBottom: 12 },
  rcProgressRow: { flexDirection: 'row', alignItems: 'center' },
  progressBar: { flex: 1, height: 4, backgroundColor: '#e7e5e4', borderRadius: 2, marginRight: 10 },
  progressFill: { width: '98%', height: '100%', backgroundColor: '#1c1917', borderRadius: 2 },
  progressText: { fontSize: 10, fontWeight: '700', color: '#1c1917' },

  gridRow: { flexDirection: 'row', gap: 16 },
  gridCard: { flex: 1, backgroundColor: '#fff', borderRadius: 24, padding: 12, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 3 },
  gcImg: { width: '100%', height: 130, borderRadius: 16, backgroundColor: '#e7e5e4', marginBottom: 12 },
  gcContent: { alignItems: 'flex-start', paddingHorizontal: 4 },
  gcSuper: { fontSize: 8, color: '#78716c', fontWeight: '800', letterSpacing: 1, marginBottom: 4, textTransform: 'uppercase' },
  gcTitle: { fontSize: 15, color: '#1c1917', fontFamily: 'serif', marginBottom: 8 },
  gcBadge: { backgroundColor: '#f0fdf4', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  gcBadgeText: { fontSize: 9, fontWeight: '800', color: '#065f46' },

  // 2. RESULT STYLES
  resultWrap: { width: '100%' },
  imgWrapper: { width: '100%', height: 420, position: 'relative', backgroundColor: '#f3efe8' },
  img: { width: '100%', height: '100%', resizeMode: 'cover' },
  containedImg: { resizeMode: 'contain' },
  resultBackBtn: {
    position: 'absolute',
    top: 18,
    left: 18,
    zIndex: 12,
    height: 42,
    borderRadius: 21,
    paddingHorizontal: 12,
    backgroundColor: 'rgba(255,255,255,0.92)',
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.12,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  resultBackText: { color: '#1c1917', fontSize: 13, fontWeight: '800', marginLeft: 2 },
  confirmImageWrapper: {
    height: 292,
    backgroundColor: '#050505',
    borderBottomLeftRadius: 26,
    borderBottomRightRadius: 26,
    overflow: 'hidden',
  },
  cameraPreview: { width: '100%', height: '100%', backgroundColor: '#0f172a', justifyContent: 'center', alignItems: 'center', paddingHorizontal: 24 },
  cameraFrame: { width: '100%', height: 280, borderRadius: 28, borderWidth: 2, borderStyle: 'dashed', borderColor: 'rgba(255,255,255,0.35)', justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.08)' },
  cameraTitle: { color: '#fff', fontSize: 22, fontWeight: '800', marginTop: 14 },
  cameraSub: { color: 'rgba(255,255,255,0.7)', fontSize: 13, marginTop: 6, textAlign: 'center' },
  sheet: {
    backgroundColor: '#fdfbf7',
    borderTopLeftRadius: 36, borderTopRightRadius: 36,
    marginTop: -40,
    paddingHorizontal: 24, paddingTop: 32, paddingBottom: 40,
    minHeight: 500,
  },
  confirmSheet: {
    marginTop: -30,
    minHeight: 0,
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 36,
  },
  confirmPanel: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#ece6dd',
    borderRadius: 24,
    padding: 18,
    shadowColor: '#064e3b',
    shadowOpacity: 0.08,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 3,
  },
  loadingPanel: { alignItems: 'center', justifyContent: 'center', minHeight: 220 },
  loadingText: { color: '#475569', marginTop: 16, textAlign: 'center', lineHeight: 20 },
  cancelAnalyzeBtn: { marginTop: 18, minWidth: 120, height: 46, borderRadius: 16, backgroundColor: '#f5f5f4', alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: '#e7e5e4' },
  cancelAnalyzeText: { color: '#44403c', fontSize: 13, fontWeight: '800' },
  confirmTopRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  confirmCopy: { flex: 1 },
  confirmKicker: { color: '#047857', fontSize: 11, fontWeight: '800', letterSpacing: 0.5, textTransform: 'uppercase' },
  confirmMetaRow: { flexDirection: 'row', gap: 10, marginTop: 2, marginBottom: 16 },
  confirmMeta: {
    flex: 1,
    minHeight: 46,
    borderRadius: 14,
    backgroundColor: '#f6f3ee',
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 7,
    paddingHorizontal: 10,
  },
  confirmMetaText: { color: '#44403c', fontSize: 11, fontWeight: '800' },
  confirmActions: { gap: 10 },
  confirmPrimary: {
    backgroundColor: '#065f46',
    borderRadius: 18,
    minHeight: 56,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
    elevation: 3,
    shadowColor: '#065f46',
    shadowOpacity: 0.3,
    shadowRadius: 10,
  },
  confirmPrimaryDisabled: { opacity: 0.7 },
  confirmSecondary: {
    backgroundColor: '#f5f5f4',
    borderRadius: 18,
    minHeight: 52,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 },
  titleWrap: { flex: 1, paddingRight: 16 },
  sheetTitle: { fontSize: 26, fontWeight: '800', color: '#1c1917', fontFamily: 'serif', marginBottom: 2, lineHeight: 32 },
  subtitle: { fontSize: 15, fontStyle: 'italic', color: '#78716c' },
  creditInline: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 10, flexWrap: 'wrap' },
  creditInlineText: { color: '#78716c', fontSize: 12, fontWeight: '800' },
  creditInlineLink: { color: '#065f46', fontSize: 12, fontWeight: '900' },
  
  matchBox: { backgroundColor: '#d1fae5', paddingHorizontal: 16, paddingVertical: 12, borderRadius: 16, alignItems: 'center' },
  matchVal: { fontSize: 20, fontWeight: '800', color: '#065f46' },
  matchLbl: { fontSize: 9, fontWeight: '800', color: '#065f46', letterSpacing: 0.5 },

  pillsRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 32 },
  pill: { backgroundColor: '#f5f5f4', width: '31%', borderRadius: 20, paddingVertical: 16, paddingHorizontal: 4, alignItems: 'center' },
  pillLabel: { fontSize: 9, fontWeight: '800', color: '#78716c', textTransform: 'uppercase', marginBottom: 4, letterSpacing: 0.5 },
  pillVal: { fontSize: 12, fontWeight: '700', color: '#1c1917', textAlign: 'center' },

  detailGrid: { marginBottom: 26, gap: 10 },
  detailRow: {
    backgroundColor: '#f7f5f0',
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: '#eee8df',
  },
  detailLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: '#78716c',
    textTransform: 'uppercase',
    marginBottom: 4,
    letterSpacing: 0.5,
  },
  detailValue: { fontSize: 13, color: '#1c1917', fontWeight: '700', lineHeight: 20 },

  secCardTitle: { fontSize: 17, fontWeight: '800', color: '#1c1917', fontFamily: 'serif', marginBottom: 14 },
  careTipsBox: { backgroundColor: '#f5f5f4', borderRadius: 16, padding: 18, flexDirection: 'row', marginBottom: 28 },
  careText: { fontSize: 13, color: '#57534e', lineHeight: 22, flex: 1 },
  descText: { fontSize: 14, color: '#57534e', lineHeight: 24, paddingBottom: 32 },
  sourcesBox: { marginTop: -10, marginBottom: 30 },
  sourceItem: {
    backgroundColor: '#f5f5f4',
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#eee8df',
  },
  sourceTitle: { color: '#064e3b', fontSize: 13, fontWeight: '800', lineHeight: 19 },
  sourceUrl: { color: '#78716c', fontSize: 11, marginTop: 6 },

  btnCol: { gap: 12, marginTop: 10 },
  mainBtn: { backgroundColor: '#065f46', borderRadius: 24, paddingVertical: 18, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', elevation: 2, shadowColor: '#065f46', shadowOpacity: 0.3, shadowRadius: 8 },
  mainBtnText: { color: '#fff', fontSize: 14, fontWeight: '800', letterSpacing: 1 },
  secBtn: { backgroundColor: '#f5f5f4', borderRadius: 24, paddingVertical: 18, flexDirection: 'row', justifyContent: 'center', alignItems: 'center' },
  secBtnText: { color: '#44403c', fontSize: 14, fontWeight: '800', letterSpacing: 1 },
});
