export const normalizeMarkText = (value) => String(value || '')
  .toLowerCase()
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .replace(/đ/g, 'd')
  .replace(/Đ/g, 'D');

export const toPlainLatin = (value) => String(value || '')
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .replace(/đ/g, 'd')
  .replace(/Đ/g, 'D');

const REIGN_NAMES = [
  ['hong vu', 'Hongwu'],
  ['kien van', 'Jianwen'],
  ['vinh lac', 'Yongle'],
  ['thuan tri', 'Shunzhi'],
  ['khang hy', 'Kangxi'],
  ['ung chinh', 'Yongzheng'],
  ['can long', 'Qianlong'],
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
  ['bao dai', 'Bao Dai'],
  ['quang trung', 'Quang Trung'],
];

export function englishReignName(value) {
  const text = String(value || '');
  const norm = normalizeMarkText(text);
  const match = REIGN_NAMES.find(([key]) => norm.includes(key));
  if (match) return match[1];
  return toPlainLatin(text).replace(/\s+Period$/i, '').trim();
}

export function englishDynastyName(value) {
  const norm = normalizeMarkText(value);
  if (norm.includes('thanh') || norm.includes('qing')) return 'Qing Dynasty';
  if (norm.includes('minh') || norm.includes('ming')) return 'Ming Dynasty';
  if (norm.includes('nguyen')) return 'Nguyen Dynasty';
  if (norm.includes('tay son')) return 'Tay Son Dynasty';
  return toPlainLatin(value);
}

export function englishEmperorName(value) {
  const norm = normalizeMarkText(value);
  if (norm.includes('tuyen thong') || norm.includes('puyi')) return 'Xuantong (Puyi)';
  if (norm.includes('quang tu')) return 'Guangxu Emperor';
  if (norm.includes('dong tri')) return 'Tongzhi Emperor';
  if (norm.includes('ham phong')) return 'Xianfeng Emperor';
  if (norm.includes('dao quang')) return 'Daoguang Emperor';
  if (norm.includes('gia khanh')) return 'Jiaqing Emperor';
  if (norm.includes('can long')) return 'Qianlong Emperor';
  if (norm.includes('ung chinh')) return 'Yongzheng Emperor';
  if (norm.includes('khang hy')) return 'Kangxi Emperor';
  if (norm.includes('thuan tri')) return 'Shunzhi Emperor';
  return englishReignName(value);
}

export function englishMarkTitle(value, reignValue = '', dynastyValue = '') {
  const combined = `${value || ''} ${reignValue || ''} ${dynastyValue || ''}`;
  const norm = normalizeMarkText(combined);
  const reign = englishReignName(combined);
  const hasReign = reign && normalizeMarkText(reign) !== normalizeMarkText(combined);
  if (norm.includes('dai thanh') || norm.includes('thanh') || norm.includes('qing')) {
    return hasReign ? `Great Qing ${reign} Reign Mark` : 'Great Qing Reign Mark';
  }
  if (norm.includes('dai minh') || norm.includes('minh') || norm.includes('ming')) {
    return hasReign ? `Great Ming ${reign} Reign Mark` : 'Great Ming Reign Mark';
  }
  if (norm.includes('nguyen')) {
    return hasReign ? `${reign} Reign Mark` : 'Nguyen Reign Mark';
  }
  return hasReign ? `${reign} Reign Mark` : toPlainLatin(value);
}

export function englishContextText(value, reignValue = '', dynastyValue = '', period = '') {
  const text = String(value || '');
  const norm = normalizeMarkText(`${text} ${reignValue} ${dynastyValue}`);
  const periodText = period ? ` Period ${period}.` : '';
  if (norm.includes('tri vi lau nhat') || norm.includes('hieu de bi gia nhieu') || norm.includes('lich su tq')) {
    return `Longest reign in Chinese history; this reign mark is frequently copied.${periodText}`;
  }
  if (norm.includes('hoang de cuoi cung nha thanh') || norm.includes('tuyen thong')) {
    return `Last emperor of the Qing dynasty.${periodText}`;
  }
  if (norm.includes('hoang de dau tien nha thanh') || norm.includes('thuan tri')) {
    return `First emperor of the Qing dynasty.${periodText}`;
  }
  if (norm.includes('hoang de khai quoc nha minh') || norm.includes('hong vu')) {
    return `Founding emperor of the Ming dynasty.${periodText}`;
  }
  if (norm.includes('hoang de cuoi nha minh')) {
    return `Last emperor of the Ming dynasty.${periodText}`;
  }
  if (norm.includes('hoang de khai quoc nha nguyen') || norm.includes('gia long')) {
    return `Founding emperor of the Nguyen dynasty.${periodText}`;
  }
  if (norm.includes('hoang de cuoi cung viet nam') || norm.includes('bao dai')) {
    return `Last emperor of Vietnam.${periodText}`;
  }
  if (norm.includes('hieu de rat hiem')) return `Very rare reign mark.${periodText}`;
  if (norm.includes('gom su noi tieng') || norm.includes('xuat khau nhieu')) {
    return `Famous ceramic mark, widely associated with export wares.${periodText}`;
  }
  if (!text.trim()) return '';
  return 'Reference information is available for this reign mark.';
}

export function englishCalligraphyText(value) {
  const text = String(value || '');
  const norm = normalizeMarkText(text);
  if (norm.includes('thuong viet thanh ba dong') || norm.includes('moi dong hai chu') || norm.includes('net chu day dan')) {
    return 'Usually written in three rows with two characters per row. The strokes are thick, firm, and forceful.';
  }
  if (
    norm.includes('thu phap dat den do chuan muc cao')
    || norm.includes('net chu ngay ngan')
    || norm.includes('khai thu')
    || norm.includes('trien tu')
  ) {
    return 'The calligraphy is highly standardized, with neat, sharp, and carefully controlled strokes. Regular script is common on imperial wares, while seal script is sometimes used.';
  }
  if (norm.includes('da phan dung the khai thu')) {
    return 'Usually written in regular script with decisive brushwork and visible tonal variation.';
  }
  if (norm.includes('bo cuc thuong dan trai')) {
    return 'Balanced blue-and-white layout with darker cobalt accumulation and smooth glaze absorption.';
  }
  if (!text.trim()) return '';
  return 'Calligraphy notes are available for this reign mark.';
}
