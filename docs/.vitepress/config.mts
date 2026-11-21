import { defineConfig } from 'vitepress'
import { BOOKS, sidebarFor } from './books.mjs'

// GitHub Pages 项目站部署在 /ozstack/ 下；本地开发仍走根路径。
// 构建时由 GitHub Actions 传入 DOCS_BASE=/ozstack/。
const base = process.env.DOCS_BASE || '/'

export default defineConfig({
  lang: 'zh-CN',
  title: 'OzStack 奥兹大力玩',
  description: '双栏理论社区。',
  base,
  appearance: false,
  markdown: {
    math: true,
  },
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: `${base}logo.svg` }],
    ['meta', { name: 'theme-color', content: '#9db5a5' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    [
      'link',
      {
        rel: 'stylesheet',
        href: 'https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400..600;1,6..72,400&family=Noto+Serif+SC:wght@400;500;600&display=swap',
      },
    ],
  ],
  themeConfig: {
    logo: '/logo.svg',
    nav: [
      { text: '古法编程大力玩', link: '/gufa/introduction/', activeMatch: '^/gufa/' },
      { text: '计算科学大力丸', link: '/jisuan/introduction/', activeMatch: '^/jisuan/' },
    ],
    search: {
      provider: 'local',
      options: {
        translations: {
          button: {
            buttonText: '搜索',
            buttonAriaLabel: '搜索',
          },
          modal: {
            noResultsText: '没有找到',
            resetButtonTitle: '清除',
            footer: {
              selectText: '选择',
              navigateText: '切换',
              closeText: '关闭',
            },
          },
        },
      },
    },
    sidebar: {
      '/gufa/': sidebarFor(BOOKS[0]),
      '/jisuan/': sidebarFor(BOOKS[1]),
    },
    outline: { level: [2, 3], label: '本页大纲' },
    docFooter: { prev: '上一篇', next: '下一篇' },
    returnToTopLabel: '回到顶部',
    sidebarMenuLabel: '目录',
  },
})
