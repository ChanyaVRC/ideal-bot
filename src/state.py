from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ConversationChannelState:
    last_message_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    paused_until: datetime | None = None


class BotState:
    def __init__(self) -> None:
        self.active_channels: dict[int, ConversationChannelState] = {}
        self.processing_channels: set[int] = set()
        self._locks: dict[int, asyncio.Lock] = {}

    def get_lock(self, channel_id: int) -> asyncio.Lock:
        if channel_id not in self._locks:
            self._locks[channel_id] = asyncio.Lock()
        return self._locks[channel_id]

    def is_active(self, channel_id: int, ttl_minutes: int) -> bool:
        state = self.active_channels.get(channel_id)
        if state is None:
            return False
        elapsed = (datetime.now(UTC) - state.last_message_at).total_seconds() / 60
        if elapsed > ttl_minutes:
            del self.active_channels[channel_id]
            self._locks.pop(channel_id, None)
            return False
        return True

    def is_paused(self, channel_id: int) -> bool:
        state = self.active_channels.get(channel_id)
        if state is None:
            return False
        return state.paused_until is not None and datetime.now(UTC) < state.paused_until

    def enter_conversation(self, channel_id: int) -> None:
        state = self.active_channels.get(channel_id)
        if state is not None:
            state.last_message_at = datetime.now(UTC)
        else:
            self.active_channels[channel_id] = ConversationChannelState()

    def touch(self, channel_id: int) -> None:
        state = self.active_channels.get(channel_id)
        if state is not None:
            state.last_message_at = datetime.now(UTC)

    def stop_conversation(self, channel_id: int) -> None:
        self.active_channels.pop(channel_id, None)
        self._locks.pop(channel_id, None)

    def pause_conversation(self, channel_id: int, until: datetime) -> bool:
        state = self.active_channels.get(channel_id)
        if state is None:
            return False
        if until.tzinfo is None:
            until = until.replace(tzinfo=UTC)
        state.paused_until = until
        return True

    def resume_conversation(self, channel_id: int) -> None:
        state = self.active_channels.get(channel_id)
        if state is not None:
            state.paused_until = None

    def purge_stale(self, max_idle_minutes: int) -> None:
        now = datetime.now(UTC)
        stale = [
            ch for ch, s in self.active_channels.items()
            if (now - s.last_message_at).total_seconds() / 60 > max_idle_minutes
        ]
        for ch in stale:
            del self.active_channels[ch]
            self._locks.pop(ch, None)
