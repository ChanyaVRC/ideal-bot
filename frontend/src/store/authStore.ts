import { create } from 'zustand'
import type { ManagedGuild, UserInfo } from '../api/types'

interface AuthState {
  user: UserInfo | null
  loading: boolean
  guilds: ManagedGuild[]
  setUser: (user: UserInfo | null) => void
  setLoading: (loading: boolean) => void
  setGuilds: (guilds: ManagedGuild[]) => void
  getGuild: (id: string) => ManagedGuild | undefined
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  loading: true,
  guilds: [],
  setUser: (user) => set({ user }),
  setLoading: (loading) => set({ loading }),
  setGuilds: (guilds) => set({ guilds }),
  getGuild: (id) => get().guilds.find((g) => g.id === id),
}))

export function guildIconUrl(guild: ManagedGuild, size = 64): string | null {
  if (!guild.icon) return null
  return `https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png?size=${size}`
}
