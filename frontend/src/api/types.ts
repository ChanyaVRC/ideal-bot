export interface UserInfo {
  user_id: string
  username: string
  avatar: string | null
  managed_guilds: string[]
  is_bot_admin: boolean
  bot_name: string | null
  bot_avatar: string | null
}

export interface BotInfo {
  name: string
  avatar: string | null
}

export interface ManagedGuild {
  id: string
  name: string
  icon: string | null
  has_manage_guild: boolean
}

export interface GuildSettings {
  guild_id: string
  reply_rate: number
  bot_enabled: boolean
  llm_provider: string
  llm_model: string
  bot_persona: string | null
  context_count: number
  conversation_ttl: number
  delay_read_min: number | null
  delay_read_max: number | null
  delay_type_cps: number | null
  has_api_key: boolean
}

export interface GuildSettingsUpdate {
  reply_rate?: number
  bot_enabled?: boolean
  llm_provider?: string
  llm_model?: string
  bot_persona?: string | null
  context_count?: number
  conversation_ttl?: number
  delay_read_min?: number | null
  delay_read_max?: number | null
  delay_type_cps?: number | null
  llm_api_key?: string
}

export interface Word {
  word: string
  reading: string
  category: string
  category_reading: string
  added_by: string
  created_at: string
}

export interface AdminSettings {
  has_global_api_key: boolean
  global_llm_provider: string
  global_llm_model: string
  discord_cache_ttl: number
  cpu_only_mode: boolean
  local_system_prompt: string
  local_torch_dtype: string
  local_supported_torch_dtypes: string[]
  local_quantization_mode: string
  vllm_base_url: string
}

export interface GuildAdminInfo {
  guild_id: string
  bot_enabled: boolean
  name?: string | null
  icon?: string | null
}

export interface ConversationLogEntry {
  id: number
  guild_id: string
  channel_id: string
  author_id: string
  content: string
  is_bot: boolean
  reply_context?: string | null
  generation_metadata?: string | null
  created_at: string
}

export interface FallbackResponse {
  id: number
  response: string
  sort_order: number
  created_at: string
}
