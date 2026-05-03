from __future__ import annotations

import json

from src.ai.local import LocalAI


def _make_ai() -> LocalAI:
    return LocalAI("dummy-embed-model", generation_model="dummy-gen-model")


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_not_suspended_by_default():
    ai = _make_ai()
    assert ai._generation_suspended is False


def test_generator_none_by_default():
    ai = _make_ai()
    assert ai._generator is None


# ---------------------------------------------------------------------------
# release_generator
# ---------------------------------------------------------------------------


def test_release_sets_suspended_flag():
    ai = _make_ai()
    ai.release_generator()
    assert ai._generation_suspended is True


def test_release_clears_cached_generator():
    ai = _make_ai()
    ai._generator = object()
    ai.release_generator()
    assert ai._generator is None


def test_release_is_idempotent():
    ai = _make_ai()
    ai.release_generator()
    ai.release_generator()
    assert ai._generation_suspended is True


# ---------------------------------------------------------------------------
# restore_generator
# ---------------------------------------------------------------------------


def test_restore_lifts_suspension():
    ai = _make_ai()
    ai.release_generator()
    ai.restore_generator()
    assert ai._generation_suspended is False


def test_restore_when_not_suspended_is_noop():
    ai = _make_ai()
    ai.restore_generator()
    assert ai._generation_suspended is False


def test_restore_does_not_reload_generator():
    ai = _make_ai()
    ai.release_generator()
    ai.restore_generator()
    assert ai._generator is None


# ---------------------------------------------------------------------------
# _ensure_generator respects suspension
# ---------------------------------------------------------------------------


def test_ensure_generator_returns_none_when_suspended():
    ai = _make_ai()
    ai.release_generator()
    assert ai._ensure_generator() is None


def test_ensure_generator_does_not_load_when_suspended():
    """_ensure_generator must not trigger model loading while suspended."""
    ai = _make_ai()
    ai.release_generator()
    # If suspension is ignored, this would attempt to import transformers and fail.
    # A successful None return proves the early exit is hit.
    result = ai._ensure_generator()
    assert result is None


def test_ensure_generator_returns_none_without_model_name():
    ai = LocalAI("dummy-embed-model", generation_model="")
    assert ai._ensure_generator() is None


# ---------------------------------------------------------------------------
# generate_sentence respects suspension
# ---------------------------------------------------------------------------


def test_generate_sentence_returns_empty_when_suspended():
    ai = _make_ai()
    ai.release_generator()
    text, metadata = ai.generate_sentence(["テスト"], bot_name="Bot")
    assert text == ""
    meta = json.loads(metadata)
    assert "error" in meta


# ---------------------------------------------------------------------------
# can_generate is independent of suspension
# ---------------------------------------------------------------------------


def test_can_generate_true_even_when_suspended():
    ai = _make_ai()
    ai.release_generator()
    assert ai.can_generate is True


def test_can_generate_false_without_model_name():
    ai = LocalAI("dummy-embed-model", generation_model="")
    assert ai.can_generate is False


# ---------------------------------------------------------------------------
# release / restore cycle
# ---------------------------------------------------------------------------


def test_release_then_restore_allows_future_load():
    ai = _make_ai()
    ai.release_generator()
    ai.restore_generator()
    # Not suspended; _ensure_generator would try to load on next call.
    # We can't call it without real transformers, but we verify state is correct.
    assert ai._generation_suspended is False
    assert ai._generator is None
