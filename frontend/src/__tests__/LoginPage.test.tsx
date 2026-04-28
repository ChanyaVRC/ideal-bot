import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import LoginPage from '@/pages/LoginPage'

vi.mock('@/api/client', () => ({
  authApi: {
    botInfo: vi.fn().mockResolvedValue({ data: { name: 'MyBot', avatar: null } }),
  },
}))

// window.location.href is read-only in jsdom; spy on the assignment
const locationSpy = vi.fn()

beforeEach(() => {
  Object.defineProperty(window, 'location', {
    writable: true,
    value: { href: '' },
  })
  Object.assign(window.location, { href: '' })
  vi.spyOn(window.location, 'href', 'set').mockImplementation(locationSpy)
})

describe('LoginPage', () => {
  it('renders the page title', async () => {
    render(<LoginPage />)
    expect(await screen.findByText('MyBot 管理画面')).toBeInTheDocument()
  })

  it('renders the login button', () => {
    render(<LoginPage />)
    expect(screen.getByRole('button', { name: /Discord でログイン/i })).toBeInTheDocument()
  })

  it('renders the instruction text', () => {
    render(<LoginPage />)
    expect(screen.getByText(/Discord アカウントでログインしてください/i)).toBeInTheDocument()
  })

  it('navigates to /auth/login on button click', async () => {
    render(<LoginPage />)
    await userEvent.click(screen.getByRole('button', { name: /Discord でログイン/i }))
    expect(locationSpy).toHaveBeenCalledWith('/auth/login')
  })
})
