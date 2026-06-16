# Text-Only Database Retrieval Benchmark

This benchmark uses the mark database as ground truth and generates OCR-like text variants. It measures database matching and noise tolerance, not visual recognition.

## Overall
- Database records: **690**
- Known synthetic text cases: **2226**
- Unknown/fake text cases: **100**
- Top-1 retrieval accuracy: **76.86%**
- Top-3 retrieval accuracy: **89.44%**
- Unknown false-positive rate: **100.00%**
- Avg latency: **0.191810s**
- P95 latency: **0.294815s**

## Accuracy By Variant
| Variant | N | Top-1 | Top-3 |
|---|---:|---:|---:|
| drop_first_char | 609 | 44.01% | 66.50% |
| drop_last_char | 613 | 90.86% | 98.86% |
| exact_full | 690 | 99.28% | 100.00% |
| short_mark | 87 | 100.00% | 100.00% |
| single_confusion | 158 | 32.28% | 84.81% |
| wrong_order_pair | 69 | 91.30% | 100.00% |

## Accuracy By Region/Group
| Group | N | Top-1 | Top-3 |
|---|---:|---:|---:|
| China | 189 | 88.89% | 98.41% |
| Japan | 47 | 93.62% | 100.00% |
| Korea | 83 | 80.72% | 95.18% |
| Other | 1682 | 74.73% | 87.87% |
| Vietnam | 225 | 77.78% | 89.33% |

## Main Confusions
| Ground Truth | Prediction | Count |
|---|---|---:|
| 嘉靖年造 | 大明嘉靖年製 | 4 |
| 成化年造 | 大明成化年製 | 4 |
| 乾道年製 | 至道年製 | 4 |
| 乾祐年製 | 景祐年製 | 4 |
| 大慶年製 | 大明隆慶年製 | 4 |
| 正德年製 | 大明宣德年製 | 4 |
| 治平龍應年製 | 龍 | 4 |
| 萬曆年造 | 大明萬曆年製 | 3 |
| 福聖承道年製 | 福 | 3 |
| 龍符元化年製 | 龍 | 3 |
| 天符慶壽年製 | 壽 | 3 |
| 同慶年製 | 大明隆慶年製 | 2 |
| 成泰年製 | 大明景泰年製 | 2 |
| 御用 | 御製 | 2 |
| 福壽康寧 | 福 | 2 |
| 宣化年製 | 大明成化年製 | 2 |
| 康熙年製 | 大明洪熙年製 | 2 |
| 內府侍旨 | 內府 | 2 |
| 內府侍右 | 內府 | 2 |
| 泰德年製 | 大明宣德年製 | 2 |