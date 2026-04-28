import { useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import Layout from '@/components/Layout'
import WordTable from '@/components/WordTable'
import GuildSettingsForm from '@/components/GuildSettingsForm'
import { authApi } from '@/api/client'
import { useAuthStore, guildIconUrl } from '@/store/authStore'

export default function GuildDashboardPage() {
  const { guildId } = useParams<{ guildId: string }>()
  const navigate = useNavigate()
  const { guilds, getGuild, setGuilds } = useAuthStore()
  const fetchedRef = useRef(false)

  // Direct navigation to /guild/:id bypasses GuildSelectPage, so guilds may be empty.
  // Use a ref to ensure we only attempt the fetch once per mount.
  useEffect(() => {
    if (guilds.length === 0 && !fetchedRef.current) {
      fetchedRef.current = true
      authApi.guilds().then((r) => setGuilds(r.data)).catch(() => {})
    }
  }, [guilds.length, setGuilds])

  if (!guildId) return null

  const guild = getGuild(guildId)
  const iconUrl = guild ? guildIconUrl(guild) : null

  return (
    <Layout>
      <div className="max-w-5xl mx-auto py-8 px-4">
        <div className="flex items-center gap-2 mb-6">
          <Button variant="ghost" size="sm" onClick={() => navigate('/guilds')}>
            <ChevronLeft className="h-4 w-4 mr-1" />
            サーバー一覧
          </Button>
        </div>

        {guild && (
          <div className="flex items-center gap-3 mb-6">
            {iconUrl ? (
              <img
                src={iconUrl}
                alt={guild.name}
                className="w-10 h-10 rounded-full shrink-0"
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-bold shrink-0">
                {guild.name.charAt(0)}
              </div>
            )}
            <h1 className="text-xl font-bold">{guild.name}</h1>
          </div>
        )}

        <Tabs defaultValue="words">
          <TabsList>
            <TabsTrigger value="words">単語一覧</TabsTrigger>
            <TabsTrigger value="settings">設定</TabsTrigger>
          </TabsList>

          <TabsContent value="words">
            <WordTable guildId={guildId} />
          </TabsContent>

          <TabsContent value="settings">
            <GuildSettingsForm guildId={guildId} />
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  )
}
