import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { authApi } from './api/client'
import { useAuthStore } from './store/authStore'
import LoginPage from './pages/LoginPage'
import GuildSelectPage from './pages/GuildSelectPage'
import GuildDashboardPage from './pages/GuildDashboardPage'
import BotAdminPage from './pages/BotAdminPage'

function App() {
  const { user, loading, setUser, setLoading } = useAuthStore()

  useEffect(() => {
    authApi
      .me()
      .then((r) => setUser(r.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [setUser, setLoading])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-muted-foreground">
        読み込み中…
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/guilds"
          element={user ? <GuildSelectPage /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/guild/:guildId/*"
          element={user ? <GuildDashboardPage /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/admin"
          element={
            user?.is_bot_admin ? <BotAdminPage /> : <Navigate to="/guilds" replace />
          }
        />
        <Route path="*" element={<Navigate to={user ? '/guilds' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
