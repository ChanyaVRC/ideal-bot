import { useEffect, useState } from 'react'
import { authApi } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function LoginPage() {
  const [botName, setBotName] = useState('Bot')

  useEffect(() => {
    authApi
      .botInfo()
      .then((r) => {
        const name = r.data.name || 'Bot'
        setBotName(name)
        document.title = `${name} 管理画面`
      })
      .catch(() => {})
  }, [])

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-center text-xl">{botName} 管理画面</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-center text-muted-foreground text-sm">
            Discord アカウントでログインしてください
          </p>
          <Button className="w-full" onClick={() => (window.location.href = '/auth/login')}>
            Discord でログイン
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
