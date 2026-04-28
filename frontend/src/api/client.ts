import axios from 'axios'
import type {
  AdminSettings,
  BotInfo,
  ConversationLogEntry,
  FallbackResponse,
  GuildAdminInfo,
  GuildSettings,
  GuildSettingsUpdate,
  ManagedGuild,
  UserInfo,
  Word,
} from './types'

const api = axios.create({ withCredentials: true })

export const authApi = {
  me: () => api.get<UserInfo>('/auth/me'),
  botInfo: () => api.get<BotInfo>('/auth/bot'),
  guilds: () => api.get<ManagedGuild[]>('/auth/guilds'),
  logout: () => api.post('/auth/logout'),
}

export const guildApi = {
  getSettings: (guildId: string) =>
    api.get<GuildSettings>(`/api/guilds/${guildId}/settings`),
  updateSettings: (guildId: string, data: GuildSettingsUpdate) =>
    api.patch(`/api/guilds/${guildId}/settings`, data),
  getWords: (guildId: string) =>
    api.get<Word[]>(`/api/guilds/${guildId}/words`),
  deleteWord: (guildId: string, reading: string) =>
    api.delete(`/api/guilds/${guildId}/words/${encodeURIComponent(reading)}`),
}

export const adminApi = {
  getSettings: () => api.get<AdminSettings>('/api/admin/settings'),
  updateSettings: (data: {
    global_llm_api_key?: string
    global_llm_provider?: string
    global_llm_model?: string
    discord_cache_ttl?: number
    local_system_prompt?: string
    local_torch_dtype?: string
    local_quantization_mode?: string
  }) => api.patch('/api/admin/settings', data),
  getGuilds: () => api.get<GuildAdminInfo[]>('/api/admin/guilds'),
  toggleGuild: (guildId: string, botEnabled: boolean) =>
    api.patch(`/api/admin/guilds/${guildId}`, { bot_enabled: botEnabled }),
  getFallbackResponses: () =>
    api.get<FallbackResponse[]>('/api/admin/fallback-responses'),
  addFallbackResponse: (response: string) =>
    api.post<FallbackResponse>('/api/admin/fallback-responses', { response }),
  deleteFallbackResponse: (responseId: number) =>
    api.delete(`/api/admin/fallback-responses/${responseId}`),
  syncCommands: () => api.post('/api/admin/sync-commands'),
  reloadGenerator: () => api.post('/api/admin/reload-generator'),
  getLogs: (params?: { limit?: number; offset?: number; guild_id?: string }) =>
    api.get<ConversationLogEntry[]>('/api/admin/logs', { params }),
}
