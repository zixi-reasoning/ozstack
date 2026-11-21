// 电子书结构：两栏各自的章。左栏只列章，章内小节交给右栏大纲。
// 章节目录照 Datawhale repo-template 的 chapter 文件夹结构，只有这一份源。
// 每本书没有单独主页：base 用来认路，start 是点进这本书的第一页。
// 每章一个英文标题文件夹，里面放 index.md。
// 左栏只列章，右栏留给 VitePress 自带的本页标题大纲。
export const BOOKS = [
  {
    value: 'gufa',
    no: '01',
    label: '古法编程大力玩',
    base: '/gufa/',
    start: '/gufa/introduction/',
    chapters: [
      { text: '导读', link: '/gufa/introduction/' },
      { text: '1. 字节与地址', link: '/gufa/ch1/' },
    ],
  },
  {
    value: 'jisuan',
    no: '02',
    label: '计算科学大力丸',
    base: '/jisuan/',
    start: '/jisuan/introduction/',
    chapters: [
      { text: '导读', link: '/jisuan/introduction/' },
    ],
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
