from services.evidence_service import apply_evidence_to_final


GUANGXU = "\u5927\u6e05\u5149\u7dd2\u5e74\u88fd"
GUANGXU_REIGN = "\u5149\u7dd2"


def _final_result():
    return {
        "chu_han": GUANGXU,
        "hieu_de": GUANGXU,
        "nien_hieu": GUANGXU_REIGN,
        "phien_am": "Da Qing Guangxu Nian Zhi",
        "confidence": 0.82,
        "tin_cay": 0.82,
        "data_source": "database",
    }


def _candidate():
    return {
        "chu_han": GUANGXU,
        "nien_hieu": GUANGXU_REIGN,
        "phien_am": "Da Qing Guangxu Nian Zhi",
        "source_votes": ["ocr", "db_hint_from_ocr"],
    }


def test_apply_evidence_filters_mismatched_reference_links():
    report = {
        "status": "insufficient_web_evidence",
        "enough_evidence": False,
        "best_candidate": {
            "candidate": _candidate(),
            "evidence": [],
            "sources": [
                {
                    "title": "Kangxi porcelain mark reference",
                    "url": "https://example.test/kangxi-mark",
                    "snippet": "Da Qing Kangxi Nian Zhi",
                },
                {
                    "title": "Da Qing Guangxu Nian Zhi porcelain mark",
                    "url": "https://example.test/guangxu-mark",
                    "snippet": "Guangxu reign mark",
                },
            ],
        },
        "all_source_links": ["https://example.test/kangxi-extra"],
        "all_query_links": [],
    }

    result = apply_evidence_to_final(_final_result(), report)

    assert result["search_sources"] == ["https://example.test/guangxu-mark"]
    assert "https://example.test/kangxi-mark" not in result["search_sources"]
    assert "https://example.test/kangxi-extra" not in result["search_sources"]


def test_apply_evidence_requires_filtered_evidence_for_web_verified():
    report = {
        "status": "web_verified",
        "enough_evidence": True,
        "best_candidate": {
            "candidate": _candidate(),
            "evidence": [
                {
                    "source_url": "https://example.test/kangxi-evidence",
                    "source_title": "Kangxi porcelain mark",
                    "matched_text": "Kangxi",
                },
                {
                    "source_url": "https://example.test/guangxu-evidence",
                    "source_title": "Guangxu porcelain mark",
                    "matched_text": "Guangxu",
                },
            ],
            "sources": [],
            "final_score": 0.77,
        },
        "all_source_links": [],
        "all_query_links": [],
    }

    result = apply_evidence_to_final(_final_result(), report)

    assert result["web_verified"] is True
    assert result["search_sources"] == ["https://example.test/guangxu-evidence"]
    assert len(result["candidate_evidence"]) == 1
    assert result["candidate_evidence"][0]["matched_text"] == "Guangxu"


def test_apply_evidence_keeps_visual_links_separate_when_unverified():
    report = {
        "status": "insufficient_web_evidence",
        "enough_evidence": False,
        "best_candidate": {
            "candidate": _candidate(),
            "evidence": [],
            "sources": [
                {
                    "title": "Lens visual result",
                    "url": "https://example.test/visual-match",
                    "snippet": "Similar porcelain base image",
                    "source_pipeline": "img_search",
                    "search_type": "image",
                },
                {
                    "title": "大清光緒年製 porcelain mark reference",
                    "url": "https://example.test/visual-guangxu-mark",
                    "snippet": "大清光緒年製 similar porcelain base image",
                    "source_quality": "medium",
                    "source_pipeline": "img_search",
                    "search_type": "image",
                },
            ],
        },
        "all_source_links": [],
        "all_query_links": [],
    }

    result = apply_evidence_to_final(_final_result(), report)

    assert result["search_sources"] == []
    assert result["unverified_search_sources"][0]["url"] == "https://example.test/visual-guangxu-mark"
    assert "visual-match" not in {src["url"] for src in result["unverified_search_sources"]}


def test_apply_evidence_rejects_social_unrelated_evidence():
    report = {
        "status": "web_verified",
        "enough_evidence": True,
        "best_candidate": {
            "candidate": _candidate(),
            "evidence": [
                {
                    "source_url": "https://www.facebook.com/example-post",
                    "source_title": "Laughing Buddha Mark - Chinese Famille Rose Figurines",
                    "matched_text": GUANGXU,
                    "source_quality": "low",
                }
            ],
            "sources": [],
            "final_score": 0.77,
        },
        "all_source_links": [],
        "all_query_links": [],
    }

    result = apply_evidence_to_final(_final_result(), report)

    assert result["candidate_evidence"] == []
    assert result["search_sources"] == []
    assert result["web_verified"] is False
