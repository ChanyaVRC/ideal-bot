from __future__ import annotations

from src.utils.normalize import get_word_reading, get_category_reading


def test_get_word_reading_mode_word_returns_original():
    assert get_word_reading("word", "りんご") == "りんご"
    assert get_word_reading("word", "Apple") == "Apple"


def test_get_word_reading_mode_reading_converts_to_hiragana():
    result = get_word_reading("reading", "東京")
    assert result == "とうきょう"


def test_get_word_reading_mode_vector_uses_reading():
    result_reading = get_word_reading("reading", "東京")
    result_vector = get_word_reading("vector", "東京")
    assert result_vector == result_reading


def test_get_word_reading_hiragana_unchanged():
    assert get_word_reading("reading", "りんご") == "りんご"


def test_get_category_reading_mode_word_returns_original():
    assert get_category_reading("word", "果物") == "果物"


def test_get_category_reading_mode_reading_converts():
    result = get_category_reading("reading", "果物")
    assert result == "くだもの"


def test_get_category_reading_mode_vector_uses_reading():
    result_reading = get_category_reading("reading", "果物")
    result_vector = get_category_reading("vector", "果物")
    assert result_vector == result_reading


def test_get_word_reading_ascii_passthrough():
    assert get_word_reading("reading", "hello") == "hello"
