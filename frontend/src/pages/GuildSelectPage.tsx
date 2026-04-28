import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@/api/client'
import type { ManagedGuild } from '@/api/types'
import { useAuthStore, guildIconUrl } from '@/store/authStore'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Layout from '@/components/Layout'

export default function GuildSelectPage() {
  const { user, setGuilds: storeSetGuilds } = useAuthStore()
  const navigate = useNavigate()
  const [guilds, setGuilds] = useState<ManagedGuild[]>([])
  const [loading, setLoading] = useState(true)

  const manageableGuilds = guilds.filter((g) => g.has_manage_guild)
  const nonManageableGuilds = guilds.filter((g) => !g.has_manage_guild)

  useEffect(() => {
    authApi
      .guilds()
      .then((r) => {
        setGuilds(r.data)
        storeSetGuilds(r.data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [storeSetGuilds])

  return (
    <Layout>
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">サーバーを選択</h1>
          {user?.is_bot_admin && (
            <Button variant="outline" onClick={() => navigate('/admin')}>
              Bot 管理者設定
            </Button>
          )}
        </div>

        {loading ? (
          <p className="text-muted-foreground">読み込み中…</p>
        ) : guilds.length === 0 ? (
          <p className="text-muted-foreground">Bot が参加しているサーバーが見つかりません。</p>
        ) : (
          <div className="space-y-8">
            <section>
              <h2 className="text-lg font-semibold mb-3">サーバー管理権限あり</h2>
              {manageableGuilds.length === 0 ? (
                <p className="text-sm text-muted-foreground">該当サーバーはありません。</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {manageableGuilds.map((guild) => (
                    <Card
                      key={guild.id}
                      className="cursor-pointer hover:bg-accent transition-colors"
                      onClick={() => navigate(`/guild/${guild.id}`)}
                    >
                      <CardContent className="flex items-center gap-3 p-4">
                        {guildIconUrl(guild) ? (
                          <img
                            src={guildIconUrl(guild)!}
                            alt={guild.name}
                            className="w-10 h-10 rounded-full shrink-0"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-bold shrink-0">
                            {guild.name.charAt(0)}
                          </div>
                        )}
                        <div className="min-w-0">
                          <div className="font-medium truncate">{guild.name}</div>
                          <div className="text-xs text-emerald-600">サーバー管理権限あり</div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </section>

            <section>
              <h2 className="text-lg font-semibold mb-3">サーバー管理権限なし</h2>
              {nonManageableGuilds.length === 0 ? (
                <p className="text-sm text-muted-foreground">該当サーバーはありません。</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {nonManageableGuilds.map((guild) => {
                    const canOpen = !!user?.is_bot_admin
                    return (
                      <Card
                        key={guild.id}
                        className={
                          canOpen
                            ? 'cursor-pointer hover:bg-accent transition-colors'
                            : 'opacity-80 cursor-not-allowed'
                        }
                        onClick={() => {
                          if (canOpen) navigate(`/guild/${guild.id}`)
                        }}
                      >
                        <CardContent className="flex items-center gap-3 p-4">
                          {guildIconUrl(guild) ? (
                            <img
                              src={guildIconUrl(guild)!}
                              alt={guild.name}
                              className="w-10 h-10 rounded-full shrink-0"
                            />
                          ) : (
                            <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-bold shrink-0">
                              {guild.name.charAt(0)}
                            </div>
                          )}
                          <div className="min-w-0">
                            <div className="font-medium truncate">{guild.name}</div>
                            <div className="text-xs text-amber-600">サーバー管理権限なし</div>
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </Layout>
  )
}
