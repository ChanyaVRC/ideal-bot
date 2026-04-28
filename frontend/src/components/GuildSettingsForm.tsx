import { useState, useEffect } from 'react'
import { guildApi } from '@/api/client'
import type { GuildSettings, GuildSettingsUpdate } from '@/api/types'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Switch } from './ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'

const LLM_PROVIDERS = ['openai', 'gemini']
const LLM_MODELS: Record<string, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini'],
  gemini: ['gemini-2.0-flash', 'gemini-2.5-pro', 'gemini-1.5-flash'],
}

export default function GuildSettingsForm({ guildId }: { guildId: string }) {
  const [settings, setSettings] = useState<GuildSettings | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    guildApi.getSettings(guildId).then((r) => setSettings(r.data)).catch(() => {})
  }, [guildId])

  if (!settings) return <p className="text-muted-foreground text-sm py-4">読み込み中…</p>

  const update = (patch: Partial<GuildSettings>) =>
    setSettings((prev) => (prev ? { ...prev, ...patch } : prev))

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    try {
      const payload: GuildSettingsUpdate = {
        reply_rate: settings.reply_rate,
        bot_enabled: settings.bot_enabled,
        llm_provider: settings.llm_provider,
        llm_model: settings.llm_model,
        bot_persona: settings.bot_persona,
        context_count: settings.context_count,
        conversation_ttl: settings.conversation_ttl,
        delay_read_min: settings.delay_read_min ?? undefined,
        delay_read_max: settings.delay_read_max ?? undefined,
        delay_type_cps: settings.delay_type_cps ?? undefined,
      }
      if (apiKey) payload.llm_api_key = apiKey
      await guildApi.updateSettings(guildId, payload)
      setApiKey('')
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  const handleProviderChange = (provider: string) => {
    const defaultModel = LLM_MODELS[provider]?.[0] ?? ''
    update({ llm_provider: provider, llm_model: defaultModel })
  }

  const models = LLM_MODELS[settings.llm_provider] ?? []

  return (
    <div className="space-y-6 py-4 max-w-lg">
      {/* Bot 有効/無効 */}
      <div className="flex items-center justify-between">
        <Label htmlFor="bot-enabled">Bot を有効にする</Label>
        <Switch
          id="bot-enabled"
          checked={settings.bot_enabled}
          onCheckedChange={(v) => update({ bot_enabled: v })}
        />
      </div>

      {/* 反応確率 */}
      <div className="space-y-1">
        <Label htmlFor="reply-rate">反応確率（%）</Label>
        <Input
          id="reply-rate"
          type="number"
          min={0}
          max={100}
          value={settings.reply_rate}
          onChange={(e) => update({ reply_rate: Number(e.target.value) })}
        />
      </div>

      {/* 会話継続時間 */}
      <div className="space-y-1">
        <Label htmlFor="ttl">会話モード継続時間（分）</Label>
        <Input
          id="ttl"
          type="number"
          min={1}
          value={settings.conversation_ttl}
          onChange={(e) => update({ conversation_ttl: Number(e.target.value) })}
        />
      </div>

      {/* コンテキスト件数 */}
      <div className="space-y-1">
        <Label htmlFor="ctx">会話コンテキスト件数（1〜20）</Label>
        <Input
          id="ctx"
          type="number"
          min={1}
          max={20}
          value={settings.context_count}
          onChange={(e) => update({ context_count: Number(e.target.value) })}
        />
      </div>

      {/* 応答遅延 */}
      <div className="space-y-2">
        <Label>応答遅延</Label>
        <div className="grid grid-cols-3 gap-2">
          <div>
            <Label className="text-xs text-muted-foreground">読み取り最小（秒）</Label>
            <Input
              type="number"
              min={0}
              step={0.1}
              value={settings.delay_read_min ?? ''}
              placeholder="1"
              onChange={(e) =>
                update({ delay_read_min: e.target.value ? Number(e.target.value) : null })
              }
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">読み取り最大（秒）</Label>
            <Input
              type="number"
              min={0}
              step={0.1}
              value={settings.delay_read_max ?? ''}
              placeholder="3"
              onChange={(e) =>
                update({ delay_read_max: e.target.value ? Number(e.target.value) : null })
              }
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">入力速度（文字/秒）</Label>
            <Input
              type="number"
              min={1}
              value={settings.delay_type_cps ?? ''}
              placeholder="15"
              onChange={(e) =>
                update({ delay_type_cps: e.target.value ? Number(e.target.value) : null })
              }
            />
          </div>
        </div>
      </div>

      {/* キャラクター設定 */}
      <div className="space-y-1">
        <Label htmlFor="persona">Bot の口調・キャラクター</Label>
        <Input
          id="persona"
          placeholder="例: 元気いっぱいで明るい口調"
          value={settings.bot_persona ?? ''}
          onChange={(e) => update({ bot_persona: e.target.value || null })}
        />
      </div>

      {/* LLM 設定 */}
      <div className="space-y-2">
        <Label>LLM プロバイダー</Label>
        <Select
          value={settings.llm_provider}
          onValueChange={handleProviderChange}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LLM_PROVIDERS.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1">
        <Label htmlFor="llm-model">LLM モデル</Label>
        <Input
          id="llm-model"
          list="model-list"
          value={settings.llm_model}
          onChange={(e) => update({ llm_model: e.target.value })}
        />
        <datalist id="model-list">
          {models.map((m) => (
            <option key={m} value={m} />
          ))}
        </datalist>
      </div>

      <div className="space-y-1">
        <Label htmlFor="api-key">
          LLM API キー
          {settings.has_api_key && (
            <span className="ml-2 text-xs text-muted-foreground">（設定済み）</span>
          )}
        </Label>
        <Input
          id="api-key"
          type="password"
          placeholder="変更する場合のみ入力"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
      </div>

      <Button onClick={handleSave} disabled={saving}>
        {saving ? '保存中…' : saved ? '保存しました ✓' : '保存'}
      </Button>
    </div>
  )
}
