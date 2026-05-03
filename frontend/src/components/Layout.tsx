import { useEffect } from 'react'
import { authApi } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import { Button } from './ui/button'
import { Separator } from './ui/separator'

function userAvatarUrl(userId: string, avatar: string | null): string | null {
  if (!avatar) return null
  return `https://cdn.discordapp.com/avatars/${userId}/${avatar}.png?size=64`
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, setUser } = useAuthStore()

  useEffect(() => {
    document.title = `${user?.bot_name || 'Bot'} 管理画面`
  }, [user?.bot_name])

  const handleLogout = async () => {
    await authApi.logout()
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <span className="font-bold text-lg">{user?.bot_name || 'Bot'}</span>
          {user && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                {userAvatarUrl(user.user_id, user.avatar) ? (
                  <img
                    src={userAvatarUrl(user.user_id, user.avatar)!}
                    alt={user.username}
                    className="w-7 h-7 rounded-full"
                  />
                ) : (
                  <div className="w-7 h-7 rounded-full bg-primary text-primary-foreground text-xs font-bold flex items-center justify-center">
                    {user.username.charAt(0)}
                  </div>
                )}
                <span className="text-sm text-muted-foreground">{user.username}</span>
              </div>
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                ログアウト
              </Button>
            </div>
          )}
        </div>
      </header>
      <Separator />
      <main>{children}</main>
    </div>
  )
}
