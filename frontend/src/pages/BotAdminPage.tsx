import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { adminApi } from '@/api/client'
import type {
  AdminSettings,
  ConversationLogEntry,
  FallbackResponse,
  GuildAdminInfo,
} from '@/api/types'
import Layout from '@/components/Layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

function GlobalSettings() {
  const [settings, setSettings] = useState<AdminSettings | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncDone, setSyncDone] = useState(false)
  const [reloading, setReloading] = useState(false)
  const [reloadDone, setReloadDone] = useState(false)

  useEffect(() => {
    adminApi.getSettings().then((r) => setSettings(r.data)).catch(() => {})
  }, [])

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    try {
      await adminApi.updateSettings({
        ...(apiKey ? { global_llm_api_key: apiKey } : {}),
        global_llm_provider: settings.global_llm_provider,
        global_llm_model: settings.global_llm_model,
        discord_cache_ttl: settings.discord_cache_ttl,
        local_system_prompt: settings.local_system_prompt,
        local_torch_dtype: settings.local_torch_dtype,
        local_quantization_mode: settings.local_quantization_mode,
      })
      setApiKey('')
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  if (!settings) return <p className="text-muted-foreground text-sm">読み込み中…</p>

  return (
    <div className="space-y-4 max-w-lg">
      <div className="space-y-1">
        <Label htmlFor="global-provider">LLM プロバイダー（グローバル）</Label>
        <Input
          id="global-provider"
          value={settings.global_llm_provider}
          onChange={(e) => setSettings({ ...settings, global_llm_provider: e.target.value })}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="global-model">LLM モデル（グローバル）</Label>
        <Input
          id="global-model"
          value={settings.global_llm_model}
          onChange={(e) => setSettings({ ...settings, global_llm_model: e.target.value })}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="global-api-key">
          グローバル API キー
          {settings.has_global_api_key && (
            <span className="ml-2 text-xs text-muted-foreground">（設定済み）</span>
          )}
        </Label>
        <Input
          id="global-api-key"
          type="password"
          placeholder="変更する場合のみ入力"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="discord-cache-ttl">Discord キャッシュ TTL（秒）</Label>
        <Input
          id="discord-cache-ttl"
          type="number"
          min={0}
          value={settings.discord_cache_ttl}
          onChange={(e) =>
            setSettings({ ...settings, discord_cache_ttl: Number(e.target.value) })
          }
        />
        <p className="text-xs text-muted-foreground">
          ギルド一覧などの Discord 情報をキャッシュする時間です。0 で毎回取得します。
        </p>
      </div>
      <div className="space-y-1">
        <Label htmlFor="local-system-prompt">ローカル LLM システムプロンプト</Label>
        <Textarea
          id="local-system-prompt"
          rows={5}
          value={settings.local_system_prompt}
          onChange={(e) => setSettings({ ...settings, local_system_prompt: e.target.value })}
        />
        <p className="text-xs text-muted-foreground">
          使用できる変数: <code>{'{bot_name}'}</code>（Bot名）、<code>{'{target_length}'}</code>（目標文字数）
        </p>
      </div>
      <div className="space-y-1">
        <Label>ローカル LLM torch_dtype</Label>
        <Select
          value={settings.local_torch_dtype}
          onValueChange={(v) => setSettings({ ...settings, local_torch_dtype: v })}
        >
          <SelectTrigger id="local-torch-dtype">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">auto（自動）</SelectItem>
            <SelectItem value="bfloat16">bfloat16</SelectItem>
            <SelectItem value="float16">float16</SelectItem>
            <SelectItem value="float32">float32</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          量子化モードが "none" のときに使用されます。CPU モードでは bfloat16 を推奨します。
        </p>
      </div>
      <div className="space-y-1">
        <Label>量子化モード（GPU 専用）</Label>
        <Select
          value={settings.local_quantization_mode}
          onValueChange={(v) => setSettings({ ...settings, local_quantization_mode: v })}
        >
          <SelectTrigger id="local-quantization-mode">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">none（無効）</SelectItem>
            <SelectItem value="4bit">4-bit（推奨）</SelectItem>
            <SelectItem value="8bit">8-bit</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          bitsandbytes が必要です。CPU モードでは "none" を選択してください。変更後はジェネレーターを再起動してください。
        </p>
      </div>
      <Button onClick={handleSave} disabled={saving}>
        {saving ? '保存中…' : saved ? '保存しました ✓' : '保存'}
      </Button>
      <Separator />
      <div className="space-y-1">
        <p className="text-sm font-medium">スラッシュコマンドの再同期</p>
        <p className="text-xs text-muted-foreground">
          ボットに再同期リクエストを送ります。最大30秒ほどで反映されます。
        </p>
        <Button
          variant="outline"
          onClick={async () => {
            setSyncing(true)
            try {
              await adminApi.syncCommands()
              setSyncDone(true)
              setTimeout(() => setSyncDone(false), 3000)
            } finally {
              setSyncing(false)
            }
          }}
          disabled={syncing}
        >
          {syncing ? 'リクエスト送信中…' : syncDone ? '送信しました ✓' : 'コマンドを再同期'}
        </Button>
      </div>
      <Separator />
      <div className="space-y-1">
        <p className="text-sm font-medium">ローカル AI ジェネレーターの再起動</p>
        <p className="text-xs text-muted-foreground">
          ローカル生成モデルをリロードします。モデルの再ロードには数分かかる場合があります。最大30秒ほどでリクエストが処理されます。
        </p>
        <Button
          variant="outline"
          onClick={async () => {
            setReloading(true)
            try {
              await adminApi.reloadGenerator()
              setReloadDone(true)
              setTimeout(() => setReloadDone(false), 3000)
            } finally {
              setReloading(false)
            }
          }}
          disabled={reloading}
        >
          {reloading ? 'リクエスト送信中…' : reloadDone ? '送信しました ✓' : 'ジェネレーターを再起動'}
        </Button>
      </div>
    </div>
  )
}

function GuildList() {
  const [guilds, setGuilds] = useState<GuildAdminInfo[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    adminApi.getGuilds().then((r) => setGuilds(r.data)).catch(() => {})
  }, [])

  const toggle = async (guildId: string, enabled: boolean) => {
    await adminApi.toggleGuild(guildId, enabled)
    setGuilds((prev) =>
      prev.map((g) => (g.guild_id === guildId ? { ...g, bot_enabled: enabled } : g)),
    )
  }

  if (guilds.length === 0)
    return <p className="text-muted-foreground text-sm">ギルドがありません</p>

  return (
    <div className="space-y-2 max-w-lg">
      {guilds.map((g) => {
        const iconUrl = g.icon
          ? `https://cdn.discordapp.com/icons/${g.guild_id}/${g.icon}.png?size=64`
          : null
        return (
          <Card key={g.guild_id}>
            <CardContent className="flex items-center justify-between py-3 px-4">
              <div
                className="flex items-center gap-3 cursor-pointer hover:underline min-w-0"
                onClick={() => navigate(`/guild/${g.guild_id}`)}
              >
                {iconUrl ? (
                  <img
                    src={iconUrl}
                    alt={g.name ?? g.guild_id}
                    className="w-8 h-8 rounded-full shrink-0"
                  />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0">
                    {g.name ? g.name.charAt(0) : '#'}
                  </div>
                )}
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">
                    {g.name ?? g.guild_id}
                  </div>
                  {g.name && (
                    <div className="text-xs text-muted-foreground font-mono">{g.guild_id}</div>
                  )}
                </div>
              </div>
              <Switch
                checked={g.bot_enabled}
                onCheckedChange={(v) => toggle(g.guild_id, v)}
              />
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function ConversationLogs() {
  const [logs, setLogs] = useState<ConversationLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [guildId, setGuildId] = useState('')

  const fetchLogs = () => {
    setLoading(true)
    adminApi
      .getLogs({ limit: 200, ...(guildId ? { guild_id: guildId } : {}) })
      .then((r) => setLogs(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchLogs()
  }, [])

  return (
    <div className="space-y-3">
      <div className="flex items-end gap-2">
        <div className="space-y-1">
          <Label htmlFor="log-guild-id">ギルドIDで絞り込み（任意）</Label>
          <Input
            id="log-guild-id"
            value={guildId}
            onChange={(e) => setGuildId(e.target.value)}
            placeholder="123456789012345678"
          />
        </div>
        <Button variant="outline" onClick={fetchLogs}>更新</Button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">読み込み中…</p>
      ) : logs.length === 0 ? (
        <p className="text-sm text-muted-foreground">発言ログがありません。</p>
      ) : (
        <div className="overflow-x-auto">
        <Table className="min-w-[1200px]">
          <TableHeader>
            <TableRow>
              <TableHead>時刻</TableHead>
              <TableHead>Guild</TableHead>
              <TableHead>Channel</TableHead>
              <TableHead>Author</TableHead>
              <TableHead>種別</TableHead>
              <TableHead>内容</TableHead>
              <TableHead>返信対象コンテキスト</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logs.map((log) => (
              <TableRow key={log.id}>
                <TableCell className="whitespace-nowrap">{log.created_at}</TableCell>
                <TableCell className="font-mono text-xs">{log.guild_id}</TableCell>
                <TableCell className="font-mono text-xs">{log.channel_id}</TableCell>
                <TableCell className="font-mono text-xs">{log.author_id}</TableCell>
                <TableCell>{log.is_bot ? 'Bot' : 'User'}</TableCell>
                <TableCell className="max-w-[520px] truncate" title={log.content}>
                  {log.content}
                </TableCell>
                <TableCell
                  className="min-w-[420px] whitespace-pre-wrap break-words text-xs"
                  title={log.reply_context ?? undefined}
                >
                  {log.reply_context || ' - '}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        </div>
      )}
    </div>
  )
}

function FallbackResponsesEditor() {
  const [items, setItems] = useState<FallbackResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [newResponse, setNewResponse] = useState('')
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    adminApi
      .getFallbackResponses()
      .then((r) => setItems(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const handleAdd = async () => {
    const value = newResponse.trim()
    if (!value) return
    setSaving(true)
    try {
      const r = await adminApi.addFallbackResponse(value)
      setItems((prev) => [...prev, r.data])
      setNewResponse('')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    await adminApi.deleteFallbackResponse(id)
    setItems((prev) => prev.filter((item) => item.id !== id))
  }

  if (loading) return <p className="text-sm text-muted-foreground">読み込み中…</p>

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <Label htmlFor="new-fallback-response">新しいフォールバック文言</Label>
        <div className="flex gap-2">
          <Input
            id="new-fallback-response"
            value={newResponse}
            onChange={(e) => setNewResponse(e.target.value)}
            placeholder="/teach で教えてほしい…"
          />
          <Button onClick={handleAdd} disabled={saving || !newResponse.trim()}>
            追加
          </Button>
        </div>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">文言がありません。</p>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <Card key={item.id}>
              <CardContent className="flex items-center justify-between gap-3 py-3 px-4">
                <div className="text-sm">{item.response}</div>
                <Button variant="outline" size="sm" onClick={() => handleDelete(item.id)}>
                  削除
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export default function BotAdminPage() {
  const navigate = useNavigate()

  return (
    <Layout>
      <div className="max-w-5xl mx-auto py-8 px-4">
        <div className="flex items-center gap-2 mb-6">
          <Button variant="ghost" size="sm" onClick={() => navigate('/guilds')}>
            <ChevronLeft className="h-4 w-4 mr-1" />
            サーバー一覧
          </Button>
        </div>

        <h1 className="text-2xl font-bold mb-6">Bot 管理者設定</h1>

        <Tabs defaultValue="global">
          <TabsList>
            <TabsTrigger value="global">グローバル設定</TabsTrigger>
            <TabsTrigger value="fallback">フォールバック文言</TabsTrigger>
            <TabsTrigger value="guilds">ギルド一覧</TabsTrigger>
            <TabsTrigger value="logs">発言ログ</TabsTrigger>
          </TabsList>

          <TabsContent value="global">
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-lg">グローバル LLM 設定</CardTitle>
              </CardHeader>
              <Separator />
              <CardContent className="pt-4">
                <GlobalSettings />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="fallback">
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-lg">フォールバック文言</CardTitle>
              </CardHeader>
              <Separator />
              <CardContent className="pt-4">
                <FallbackResponsesEditor />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="guilds">
            <div className="mt-4 space-y-2">
              <p className="text-sm text-muted-foreground">
                Bot が参加しているギルドの一覧です。スイッチで有効/無効を切り替えられます。
              </p>
              <GuildList />
            </div>
          </TabsContent>

          <TabsContent value="logs">
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-lg">発言ログ</CardTitle>
              </CardHeader>
              <Separator />
              <CardContent className="pt-4">
                <ConversationLogs />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  )
}
