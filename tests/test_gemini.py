from gemini_client import _split_pillar, _strip_dashes, find_buzzwords


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


def test_find_buzzwords_clean_text_empty():
    assert find_buzzwords("A plain honest post about Postgres advisory locks.") == []


def test_find_buzzwords_catches_all_bases_and_inflections():
    text = (
        "This will unlock seamless value, delve into a game-changing idea, and "
        "revolutionize the workflow."
    )
    # unlock, seamless, delve, game-changer, revolutionize all present.
    assert set(find_buzzwords(text)) == {
        "delve",
        "revolutionize",
        "game-changer",
        "unlock",
        "seamless",
    }


def test_find_buzzwords_is_case_insensitive():
    assert find_buzzwords("UNLOCKING real value") == ["unlock"]


def test_find_buzzwords_matches_game_changer_with_space():
    assert find_buzzwords("a real game changer here") == ["game-changer"]


def test_find_buzzwords_returns_stable_order():
    # Definition order: delve, revolutionize, game-changer, unlock, seamless.
    text = "seamless unlock delve"
    assert find_buzzwords(text) == ["delve", "unlock", "seamless"]


def test_find_buzzwords_no_false_positive_on_substring():
    # "lockdown" and "unlocked" differ: only real inflections of the stem match.
    assert find_buzzwords("we locked the door during lockdown") == []


def test_split_pillar_peels_the_tag_line():
    text = "PILLAR: llm-tip\n\nThe post body."
    assert _split_pillar(text) == ("llm-tip", "The post body.")


def test_split_pillar_is_case_insensitive():
    assert _split_pillar("pillar:  Ai-Take\nbody")[0] == "ai-take"


def test_split_pillar_unknown_label_keeps_whole_text():
    # A malformed tag must cost a label, never the draft itself.
    text = "PILLAR: nonsense\n\nbody"
    assert _split_pillar(text) == ("dev-perspective", text)


def test_split_pillar_missing_tag_keeps_whole_text():
    text = "Just a post with no tag line."
    assert _split_pillar(text) == ("dev-perspective", text)
