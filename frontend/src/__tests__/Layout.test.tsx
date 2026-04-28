import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Layout from '@/components/Layout'
import { useAuthStore } from '@/store/authStore'

// Mock auth store
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

// Mock API client
vi.mock('@/api/client', () => ({
  authApi: { logout: vi.fn().mockResolvedValue({}) },
}))

describe('Layout', () => {
  it('renders children', () => {
    vi.mocked(useAuthStore).mockReturnValue({ user: null, setUser: vi.fn(), loading: false, setLoading: vi.fn() })
    render(<Layout><p>Test content</p></Layout>)
    expect(screen.getByText('Test content')).toBeInTheDocument()
  })

  it('renders bot name in header', () => {
    vi.mocked(useAuthStore).mockReturnValue({ user: null, setUser: vi.fn(), loading: false, setLoading: vi.fn() })
    render(<Layout><span /></Layout>)
    expect(screen.getByText('Bot')).toBeInTheDocument()
  })

  it('shows username when user is logged in', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: {
        user_id: '123',
        username: 'TestUser',
        avatar: null,
        is_bot_admin: false,
        managed_guilds: [],
        bot_name: 'MyBot',
        bot_avatar: null,
      },
      setUser: vi.fn(),
      loading: false,
      setLoading: vi.fn(),
    })
    render(<Layout><span /></Layout>)
    expect(screen.getByText('TestUser')).toBeInTheDocument()
  })

  it('shows logout button when user is logged in', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      user: {
        user_id: '123',
        username: 'TestUser',
        avatar: null,
        is_bot_admin: false,
        managed_guilds: [],
        bot_name: 'MyBot',
        bot_avatar: null,
      },
      setUser: vi.fn(),
      loading: false,
      setLoading: vi.fn(),
    })
    render(<Layout><span /></Layout>)
    expect(screen.getByRole('button', { name: /ログアウト/i })).toBeInTheDocument()
  })
})
