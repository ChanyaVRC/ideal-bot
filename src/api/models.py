from __future__ import annotations

from pydantic import BaseModel


class UserInfo(BaseModel):
    user_id: str
    username: str
    avatar: str | None
    managed_guilds: list[str]
    is_bot_admin: bool
    bot_name: str | None
    bot_avatar: str | None


class BotInfo(BaseModel):
    name: str
    avatar: str | None


class ManagedGuild(BaseModel):
    id: str
    name: str
    icon: str | None
    has_manage_guild: bool


class GuildSettingsResponse(BaseModel):
    guild_id: str
    reply_rate: int
    bot_enabled: bool
    llm_provider: str
    llm_model: str
    bot_persona: str | None
    context_count: int
    conversation_ttl: int
    delay_read_min: float | None
    delay_read_max: float | None
    delay_type_cps: float | None
    has_api_key: bool


class GuildSettingsUpdate(BaseModel):
    reply_rate: int | None = None
    bot_enabled: bool | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    bot_persona: str | None = None
    context_count: int | None = None
    conversation_ttl: int | None = None
    delay_read_min: float | None = None
    delay_read_max: float | None = None
    delay_type_cps: float | None = None
    llm_api_key: str | None = None  # plaintext; encrypted before storage


class WordResponse(BaseModel):
    word: str
    reading: str
    category: str
    category_reading: str
    added_by: str
    created_at: str


class AdminSettingsResponse(BaseModel):
    has_global_api_key: bool
    global_llm_provider: str
    global_llm_model: str
    discord_cache_ttl: int
    cpu_only_mode: bool
    local_system_prompt: str
    local_torch_dtype: str
    local_supported_torch_dtypes: list[str]
    local_quantization_mode: str
    vllm_base_url: str


class AdminSettingsUpdate(BaseModel):
    global_llm_api_key: str | None = None
    global_llm_provider: str | None = None
    global_llm_model: str | None = None
    discord_cache_ttl: int | None = None
    local_system_prompt: str | None = None
    local_torch_dtype: str | None = None
    local_quantization_mode: str | None = None
    vllm_base_url: str | None = None


class GuildAdminInfo(BaseModel):
    guild_id: str
    bot_enabled: bool
    name: str | None = None
    icon: str | None = None


class GuildToggle(BaseModel):
    bot_enabled: bool


class ConversationLogEntry(BaseModel):
    id: int
    guild_id: str
    channel_id: str
    author_id: str
    content: str
    is_bot: bool
    reply_context: str | None = None
    generation_metadata: str | None = None
    created_at: str


class FallbackResponse(BaseModel):
    id: int
    response: str
    sort_order: int
    created_at: str


class FallbackResponseCreate(BaseModel):
    response: str


class ServerLogResponse(BaseModel):
    lines: list[str]
    log_file: str
    available: bool
    size_bytes: int = 0
