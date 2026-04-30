import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'ideal-bot',
  description: '教えられた語彙で自然に発言する Discord Bot',
  base: '/',

  themeConfig: {
    logo: '/logo.png',

    search: {
      provider: 'local',
    },

    nav: [
      { text: 'ガイド', link: '/guide/getting-started' },
      { text: 'コマンド', link: '/guide/commands' },
      { text: '管理画面', link: '/admin/overview' },
      { text: 'GitHub', link: 'https://github.com/your-user/ideal-bot' },
    ],

    sidebar: [
      {
        text: 'はじめに',
        items: [
          { text: 'セットアップ', link: '/guide/getting-started' },
          { text: 'アップデート', link: '/guide/update' },
          { text: '設定リファレンス', link: '/guide/config' },
        ],
      },
      {
        text: 'ボットの使い方',
        items: [
          { text: 'コマンド一覧', link: '/guide/commands' },
          { text: '発言生成の仕組み', link: '/guide/ai' },
        ],
      },
      {
        text: 'Web 管理画面',
        items: [
          { text: '概要・ログイン', link: '/admin/overview' },
          { text: 'Discord OAuth2 設定', link: '/admin/oauth2' },
        ],
      },
      {
        text: '開発・デプロイ',
        items: [
          { text: '開発環境のセットアップ', link: '/dev/setup' },
          { text: 'VPS へのデプロイ', link: '/dev/deploy' },
          {
            text: 'API エンドポイント',
            link: '/dev/api',
            items: [
              { text: '認証 (/auth/*)', link: '/dev/api-auth' },
              { text: 'ギルド (/api/guilds/*)', link: '/dev/api-guilds' },
              { text: '管理者 (/api/admin/*)', link: '/dev/api-admin' },
            ],
          },
        ],
      },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/your-user/ideal-bot' },
    ],

    footer: {
      message: 'Released under the MIT License.',
    },

    editLink: {
      pattern: 'https://github.com/your-user/ideal-bot/edit/main/docs/:path',
      text: 'このページを編集',
    },
  },
})
