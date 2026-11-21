# OzStack 奥兹大力玩

双栏理论社区。一句话：AI 时代的编程大力玩。电子书结构照 Datawhale `repo-template`：每本书一个目录，每章一个英文标题文件夹，文件夹里放 `index.md`，章内小节用标题分，正文用 VitePress Markdown 写。视觉走灰绿纸面、半调网点与 Chomsky 报头。

左栏只管大跳：这本书有哪些章，点一下换章。右栏只管小跳：当前这一章有哪些小节，点一下落到标题。每本书不设单独主页，有第一章时点书名直接进第一章。

站点是纯静态 VitePress，没有登录、注册和后台。手搓大力丸。

两篇导读首尾相接：第一册见 [`docs/gufa/introduction/index.md`](./docs/gufa/introduction/index.md)，第二册见 [`docs/jisuan/introduction/index.md`](./docs/jisuan/introduction/index.md)。第一册四卷结构、每卷十章、每章硬指标、零件交接、Aletheia 的 256 KiB 内存表和第三卷末的 `AletheiaC` 见 [`AGENT.md`](./AGENT.md)；第二册四卷四十章的计算科学实验计划见 [`AGENT-JISUAN.md`](./AGENT-JISUAN.md)。全书没有图，只有汉字、LaTeX、C 代码和终端字符输出。所有完整代码直接写进章节 Markdown 的代码块，不另存 `.c` 文件。

## 目录

两篇导读已写好。第一册正文按四卷、每卷约十章推进，每一章一个可验收的零件，最后一卷最后一章总装。第二册按四卷、每卷十章推进，每一章一个计算科学实验。

| 书 | 地址 |
| --- | --- |
| 古法编程大力玩 | `/gufa/introduction/` |
| 计算科学大力丸 | `/jisuan/introduction/` |

## 电子书结构

```
docs/
  gufa/
    introduction/
      index.md                古法编程大力玩，导读
  jisuan/
    introduction/
      index.md                计算科学大力丸，导读
  .vitepress/
    books.mjs                 两本书的章目录，唯一目录源
    config.mts                左栏、右栏、搜索、公式
```

- 完整代码不另存：每章的完整程序直接写在该章 `index.md` 的代码块里，代码块第一行用注释写出建议文件名，读者复制后自己保存即可编译。
- 加一章：在书目录下建一个英文标题文件夹，里面放 `index.md`，再去 `books.mjs` 加一条。文件夹名用小写连字符，例如 `bytes-and-addresses`。左栏只列到章。
- 加一节：直接在这一章的文件里写 `## 2.3 ...`，右栏大纲会自动出现，不用另建文件。
- 每本书的 `start` 指向第一章；书名和首页小方框直接进第一章，不设书主页。
- 左栏目录和首页入口都从 `books.mjs` 取；右栏大纲由 VitePress 按当前页标题自动生成，不手写。
- 行内公式 `$...$`，块级公式 `$$...$$`。

## 站务

- 站内不设登录、注册和后台。

## 本地启动

```bash
npm install
npm run docs:dev
```

前台 http://localhost:5173

## 构建与发布

本地构建：

```bash
npm run docs:build
```

GitHub Pages 项目站挂在 `zixi-reasoning.github.io/ozstack/`。工作流在 `.github/workflows/deploy.yml`，推送到 `main` 自动构建部署。构建时传入子路径：

```bash
DOCS_BASE=/ozstack/ npm run docs:build
```

仓库第一次部署前，在 GitHub 仓库的 Settings → Pages → Build and deployment 里把 Source 设成 **GitHub Actions**。之后每次推送 `main` 都会重新发布。

## 文件

- `AGENT.md`：第一册四卷结构、每卷十章、每章字数与代码约束、零件交接、Aletheia 的 256 KiB 内存表
- `AGENT-JISUAN.md`：第二册四卷四十章的计算科学实验计划
- `docs/gufa/introduction/index.md`：第一册导读，AI 时代为什么还要从字节和数组手搓
- `docs/jisuan/introduction/index.md`：第二册导读，机器造好之后怎样用它做数学
- `docs/index.md`：首页 hero、两栏入口、手搓大力丸
- `docs/gufa/introduction/`：第一册导读；后续章节各建一个英文标题文件夹
- `docs/jisuan/introduction/`：第二册导读；后续章节各建一个英文标题文件夹
- `docs/.vitepress/books.mjs`：两本书的章目录
- `docs/.vitepress/config.mts`：左栏、右栏大纲、搜索、数学、文档页脚
- `docs/.vitepress/theme/`：`index.js` 与 `custom.css`
- `docs/public/logo.svg`：纯灰绿方块标记
- `docs/public/images/halftone-portrait.webp`：首页半色调肖像
- `docs/public/fonts/Chomsky.woff2`：报头黑体（SIL OFL，许可见同目录）
- `assets/portrait.jpg`：首页半色调肖像的源照片
- `archive/`：旧 PocketBase 后端和写稿前端，只作备份，不参与构建
