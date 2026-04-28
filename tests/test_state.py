from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.state import BotState


def test_initially_inactive():
    state = BotState()
    assert state.is_active(1, ttl_minutes=5) is False


def test_enter_conversation_makes_active():
    state = BotState()
    state.enter_conversation(1)
    assert state.is_active(1, ttl_minutes=5) is True


def test_stop_conversation_deactivates():
    state = BotState()
    state.enter_conversation(1)
    state.stop_conversation(1)
    assert state.is_active(1, ttl_minutes=5) is False


def test_ttl_expiry_deactivates():
    state = BotState()
    state.enter_conversation(1)
    # Backdate last_message_at beyond TTL
    state.active_channels[1].last_message_at = datetime.now(UTC) - timedelta(minutes=10)
    assert state.is_active(1, ttl_minutes=5) is False


def test_touch_refreshes_ttl():
    state = BotState()
    state.enter_conversation(1)
    state.active_channels[1].last_message_at = datetime.now(UTC) - timedelta(minutes=4)
    state.touch(1)
    assert state.is_active(1, ttl_minutes=5) is True


def test_not_paused_by_default():
    state = BotState()
    state.enter_conversation(1)
    assert state.is_paused(1) is False


def test_pause_and_resume():
    state = BotState()
    state.enter_conversation(1)
    until = datetime.now(UTC) + timedelta(minutes=30)
    assert state.pause_conversation(1, until) is True
    assert state.is_paused(1) is True
    state.resume_conversation(1)
    assert state.is_paused(1) is False


def test_pause_inactive_channel_returns_false():
    state = BotState()
    result = state.pause_conversation(999, datetime.now(UTC) + timedelta(minutes=10))
    assert result is False


def test_get_lock_returns_same_lock():
    state = BotState()
    lock_a = state.get_lock(1)
    lock_b = state.get_lock(1)
    assert lock_a is lock_b


def test_stop_removes_lock():
    state = BotState()
    state.enter_conversation(1)
    state.get_lock(1)
    state.stop_conversation(1)
    assert 1 not in state._locks
