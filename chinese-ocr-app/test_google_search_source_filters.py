from services.google_search import (
    _external_result_url,
    _lens_candidate_score,
    _looks_like_lens_visual_match,
)


def _lens_item(url, text, has_image=True):
    return {
        "href": url,
        "text": text,
        "aria": "",
        "title": "",
        "parent_text": text,
        "img_alt": "",
        "has_image": has_image,
        "rect": {"width": 160, "height": 120},
    }


def test_lens_visual_match_rejects_social_sources():
    item = _lens_item(
        "https://www.instagram.com/p/example",
        "Chinese porcelain reign mark visual match",
    )

    assert _looks_like_lens_visual_match(item) is False


def test_lens_visual_match_requires_porcelain_context():
    item = _lens_item(
        "https://example.test/laughing-buddha",
        "Laughing Buddha decorative figurine result",
    )

    assert _looks_like_lens_visual_match(item) is False


def test_lens_visual_match_accepts_specific_mark_context_and_scores_cjk():
    item = _lens_item(
        "https://museum.example/object/guangxu-mark",
        "Chinese porcelain reign mark 大清光緒年製 reference object",
    )

    assert _looks_like_lens_visual_match(item) is True
    assert _lens_candidate_score(item) >= 7.0


def test_external_result_url_blocks_extra_low_signal_domains():
    assert _external_result_url("https://www.reddit.com/r/porcelain/comments/example") == ""
    assert _external_result_url("https://example.test/porcelain-mark") == "https://example.test/porcelain-mark"
