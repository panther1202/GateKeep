from gemini_client import _strip_dashes


def test_em_dash_becomes_comma():
    assert _strip_dashes("LangGraph — a library — I used") == "LangGraph, a library, I used"


def test_em_dash_without_spaces():
    assert _strip_dashes("fast—cheap") == "fast, cheap"


def test_spaced_en_dash_becomes_comma():
    assert _strip_dashes("cheap – reliable") == "cheap, reliable"


def test_numeric_range_en_dash_preserved():
    # A digit-flanked en-dash is a range, not punctuation; leave it.
    assert _strip_dashes("120–220 words") == "120–220 words"


def test_plain_text_unchanged():
    assert _strip_dashes("no dashes here, all good.") == "no dashes here, all good."
