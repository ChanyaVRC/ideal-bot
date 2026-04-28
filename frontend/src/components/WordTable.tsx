import { useState, useEffect } from 'react'
import { Trash2 } from 'lucide-react'
import { guildApi } from '@/api/client'
import type { Word } from '@/api/types'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from './ui/dialog'

export default function WordTable({ guildId }: { guildId: string }) {
  const [words, setWords] = useState<Word[]>([])
  const [filter, setFilter] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<Word | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    guildApi
      .getWords(guildId)
      .then((r) => setWords(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [guildId])

  const handleDelete = async () => {
    if (!deleteTarget) return
    await guildApi.deleteWord(guildId, deleteTarget.reading)
    setWords((prev) => prev.filter((w) => w.reading !== deleteTarget.reading))
    setDeleteTarget(null)
  }

  const filtered = words.filter(
    (w) =>
      w.word.includes(filter) ||
      w.reading.includes(filter) ||
      w.category.includes(filter),
  )

  return (
    <div className="space-y-4 py-4">
      <Input
        placeholder="単語・読み・カテゴリで絞り込み"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="max-w-sm"
      />

      {loading ? (
        <p className="text-muted-foreground text-sm">読み込み中…</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>単語</TableHead>
              <TableHead>読み</TableHead>
              <TableHead>カテゴリ</TableHead>
              <TableHead>登録者</TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  単語が見つかりません
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((w) => (
                <TableRow key={w.reading}>
                  <TableCell className="font-medium">{w.word}</TableCell>
                  <TableCell>{w.reading}</TableCell>
                  <TableCell>{w.category}</TableCell>
                  <TableCell className="text-muted-foreground text-xs">{w.added_by}</TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setDeleteTarget(w)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      )}

      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>単語を削除しますか？</DialogTitle>
            <DialogDescription>
              「{deleteTarget?.word}」を削除します。この操作は元に戻せません。
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              キャンセル
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              削除
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
