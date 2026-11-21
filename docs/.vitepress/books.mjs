// 电子书结构：两栏各自的章。左栏只列章，章内小节交给右栏大纲。
// 章节目录照 Datawhale repo-template 的 chapter 文件夹结构，只有这一份源。
// 每本书没有单独主页：base 用来认路，start 是点进这本书的第一页。
// 书稿已清空，等目录和写作计划定下来再往 chapters 里加。
// 右栏不放目录，留给 VitePress 自带的本页标题大纲。
export const BOOKS = [
  {
    value: 'gufa',
    no: '01',
    label: '古法编程大力玩',
    base: '/gufa/',
    start: '/gufa/',
    chapters: [],
  },
  {
    value: 'jisuan',
    no: '02',
    label: '计算科学大力玩',
    base: '/jisuan/',
    start: '/jisuan/',
    chapters: [],
  },
]

export function bookOfPath(path) {
  return BOOKS.find((book) => path.startsWith(book.base)) || null
}

export function sidebarFor(book) {
  if (book.chapters.length === 0) return []
  return [
    {
      text: book.label,
      items: book.chapters.map(({ text, link }) => ({ text, link })),
    },
  ]
}
