import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import GuildDashboardPage from '@/pages/GuildDashboardPage'
import { useAuthStore } from '@/store/authStore'

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(),
  guildIconUrl: vi.fn(() => null),
}))

vi.mock('@/api/client', () => ({
  authApi: {
    guilds: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

// Stub heavy child components to keep tests focused on the page shell
vi.mock('@/components/WordTable', () => ({
  default: () => <div data-testid="word-table" />,
}))

vi.mock('@/components/GuildSettingsForm', () => ({
  default: () => <div data-testid="settings-form" />,
}))

vi.mock('@/components/Layout', () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const GUILD_ID = '123456789012345678'

function renderPage(guildId = GUILD_ID) {
  return render(
    <MemoryRouter initialEntries={[`/guild/${guildId}`]}>
      <Routes>
        <Route path="/guild/:guildId" element={<GuildDashboardPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

function makeStore(overrides: Record<string, unknown> = {}) {
  return {
    guilds: [],
    getGuild: vi.fn(() => undefined),
    setGuilds: vi.fn(),
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('GuildDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders tabs for words and settings', () => {
    vi.mocked(useAuthStore).mockReturnValue(makeStore())
    renderPage()
    expect(screen.getByRole('tab', { name: '単語一覧' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '設定' })).toBeInTheDocument()
  })

  it('renders word table by default', () => {
    vi.mocked(useAuthStore).mockReturnValue(makeStore())
    renderPage()
    expect(screen.getByTestId('word-table')).toBeInTheDocument()
  })

  it('shows guild name and icon placeholder when guild is known', () => {
    const guild = { id: GUILD_ID, name: 'My Server', icon: null, has_manage_guild: true }
    vi.mocked(useAuthStore).mockReturnValue(
      makeStore({ guilds: [guild], getGuild: vi.fn(() => guild) }),
    )
    renderPage()
    expect(screen.getByText('My Server')).toBeInTheDocument()
    // No icon URL → shows first-letter fallback
    expect(screen.getByText('M')).toBeInTheDocument()
  })

  it('does not render guild header when guild is unknown', () => {
    vi.mocked(useAuthStore).mockReturnValue(makeStore())
    renderPage()
    expect(screen.queryByText('My Server')).not.toBeInTheDocument()
  })

  describe('direct navigation fallback fetch', () => {
    it('calls authApi.guilds() when guilds store is empty', async () => {
      const { authApi } = await import('@/api/client')
      vi.mocked(authApi.guilds).mockResolvedValue({ data: [] } as never)

      const setGuilds = vi.fn()
      vi.mocked(useAuthStore).mockReturnValue(makeStore({ setGuilds }))

      renderPage()

      await waitFor(() => {
        expect(authApi.guilds).toHaveBeenCalledTimes(1)
      })
    })

    it('populates store with fetched guilds', async () => {
      const { authApi } = await import('@/api/client')
      const fetchedGuilds = [
        { id: GUILD_ID, name: 'Fetched Server', icon: null, has_manage_guild: true },
      ]
      vi.mocked(authApi.guilds).mockResolvedValue({ data: fetchedGuilds } as never)

      const setGuilds = vi.fn()
      vi.mocked(useAuthStore).mockReturnValue(makeStore({ setGuilds }))

      renderPage()

      await waitFor(() => {
        expect(setGuilds).toHaveBeenCalledWith(fetchedGuilds)
      })
    })

    it('does not call authApi.guilds() when guilds are already loaded', async () => {
      const { authApi } = await import('@/api/client')
      const existingGuild = { id: GUILD_ID, name: 'Existing', icon: null, has_manage_guild: true }

      vi.mocked(useAuthStore).mockReturnValue(
        makeStore({ guilds: [existingGuild], getGuild: vi.fn(() => existingGuild) }),
      )

      renderPage()

      // Give effect time to run if it incorrectly fires
      await new Promise((r) => setTimeout(r, 50))
      expect(authApi.guilds).not.toHaveBeenCalled()
    })

    it('fetches only once even if guilds remain empty after fetch', async () => {
      const { authApi } = await import('@/api/client')
      vi.mocked(authApi.guilds).mockResolvedValue({ data: [] } as never)

      vi.mocked(useAuthStore).mockReturnValue(makeStore())

      renderPage()

      await waitFor(() => expect(authApi.guilds).toHaveBeenCalled())
      // Wait a tick and confirm no second call
      await new Promise((r) => setTimeout(r, 50))
      expect(authApi.guilds).toHaveBeenCalledTimes(1)
    })
  })
})
