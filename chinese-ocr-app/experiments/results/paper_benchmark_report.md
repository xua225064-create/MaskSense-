# MarkSense Benchmark Report

## Dataset
- Dataset: `reference_library_available_data`
- Images: **28** labeled ceramic-mark images
- Scope note: this is a functional benchmark on the labeled images currently available in the repository, not an independent public benchmark.

## Main Results
| Method | Relaxed Mark Accuracy | Strict Exact Mark Accuracy | Character Accuracy | Macro-F1 (strict) | Avg Latency | P95 Latency |
|---|---:|---:|---:|---:|---:|---:|
| OCR only | 50.00% | 39.29% | 62.84% | - | 68.10s | 77.69s |
| OCR candidate recall | 67.86% | - | - | - | - | - |
| OCR + database fuzzy | 85.71% | 60.71% | 75.68% | 48.77% | 0.026s | 0.224s |
| Combined offline core | 85.71% | 60.71% | 75.68% | 48.77% | 68.31s | 78.18s |
| ORB leave-one-out | 3.57% | 3.57% | - | - | 0.191s | 0.294s |

## Family Breakdown
| Group | N | Relaxed Accuracy | Strict Exact Accuracy |
|---|---:|---:|---:|
| Auspicious / studio marks | 1 | 100.00% | 100.00% |
| Chinese imperial marks | 21 | 80.95% | 47.62% |
| Vietnamese court marks | 6 | 100.00% | 100.00% |

## Failed Cases Under Relaxed Matching
| Image | Ground Truth | OCR Prediction | Final Prediction | Detail |
|---|---|---|---|---|
| da_ming_xuan_de_nian_zhi_c7e94867.jpg | 大明宣德年製 | (empty) | 贊普鐘年製 | fuzzy_tiedecision:年 |
| ä¹¾éš†å¹´è£½_40b1c803.jpg | 乾隆年製 | 轮蓬年 | 庚午年製 | top1:轮蓬年 |
| å¤§æ˜Žå¼˜æ²»å¹´è£½_2d687f6b.jpg | 大明弘治年製 | (empty) | 大明洪武年製 | top1:汤 |
| å¤§æ˜Žè¬æ›†å¹´è£½_79cdb9a5.jpg | 大明萬曆年製 | (empty) | 贊普鐘年製 | fuzzy_tiedecision:年 |

## Notes For Paper Writing
- Use `Relaxed Mark Accuracy` to describe operational correctness under the current matching policy, where accepted variants or shortened marks can be counted as correct.
- Use `Strict Exact Mark Accuracy` when the predicted inscription must exactly match the full ground-truth inscription.
- The current dataset is small. For a publishable benchmark, extend it to at least 100 images with balanced countries/periods and image conditions.