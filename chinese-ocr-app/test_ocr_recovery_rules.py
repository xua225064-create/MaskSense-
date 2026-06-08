from ocr_engine import (
    _derive_database_mark_from_ocr_evidence,
    _derive_qing_guangxu_from_ocr_evidence,
)


def main():
    kangxi_noise = [
        "\u5927\u6e05\u88c5",  # 大清装
        "\u5927\u6e05\u7199\u88c5",  # 大清熙装
        "\u7528\u9c7c\u56e0\u591a\u7136\u529b\u5e74\u6cf0\u5927\u88c5\u7199\u6e05",
    ]
    assert _derive_database_mark_from_ocr_evidence(kangxi_noise) == "\u5927\u6e05\u5eb7\u7199\u5e74\u88fd"

    guangxu_noise = [
        "\u6e05\u5149\u5e74",  # 清光年
        "\u7ed3\u5927\u5e74\u6e05\u5149",  # 结大年清光
    ]
    assert _derive_qing_guangxu_from_ocr_evidence(guangxu_noise) == "\u5927\u6e05\u5149\u7dd2\u5e74\u88fd"

    print("OCR recovery rules OK")


if __name__ == "__main__":
    main()
