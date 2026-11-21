# OzStack 奥兹大力玩

双栏理论社区。一句话：AI 时代的编程大力玩。电子书结构照 Datawhale `repo-template`：每本书一个目录，一章一个文件，章内小节用标题分，正文用 VitePress Markdown 写。视觉走灰绿纸面、半调网点与 Chomsky 报头。

左栏只管大跳：这本书有哪些章，点一下换章。右栏只管小跳：当前这一章有哪些小节，点一下落到标题。每本书没有单独主页，点书名直接进书的第一页。

站点是纯静态 VitePress，没有登录、注册和后台。手搓大力丸。

第一册的写法、四场结构和每章硬指标见 [`古法编程大力玩-写作计划.md`](./古法编程大力玩-写作计划.md)。

## 目录

书稿已清空，等目录和写作计划定下来再加章。

| 书 | 地址 |
| --- | --- |
| 古法编程大力玩 | `/gufa/` |
| 计算科学大力玩 | `/jisuan/` |

## 电子书结构

```
docs/
  gufa/
    index.md                  古法编程大力玩，书稿空着
  jisuan/
    index.md                  计算科学大力玩，书稿空着
  .vitepress/
    books.mjs                 两本书的章目录，唯一目录源
    config.mts                左栏、右栏、搜索、公式
```

- 加一章：在 `docs/gufa/` 或 `docs/jisuan/` 下照 `chapterN/index.md` 建文件，再去 `books.mjs` 加一条。左栏只列到章。
- 加一节：直接在这一章的文件里写 `## 2.3 ...`，右栏大纲会自动出现，不用另建文件。
- 每本书的 `start` 指向书的第一页；书名和首页小方框都从这里进。
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

- `古法编程大力玩-写作计划.md` —— 第一册四场结构、每章字数与代码约束、交接关系
- `docs/index.md` —— 首页 hero、两栏入口、手搓大力丸
- `docs/gufa/`、`docs/jisuan/` —— 两本书的空壳，目录在左栏
- `docs/.vitepress/books.mjs` —— 两本书的章目录
- `docs/.vitepress/config.mts` —— 左栏、右栏大纲、搜索、数学、文档页脚
- `docs/.vitepress/theme/` —— `index.js` 与 `custom.css`
- `docs/public/logo.svg` —— 纯灰绿方块标记
- `docs/public/images/halftone-portrait.webp` —— 首页半色调肖像
- `docs/public/fonts/Chomsky.woff2` —— 报头黑体（SIL OFL，许可见同目录）
- `scripts/make-halftone.py` + `assets/portrait.jpg` —— 网点生成脚本与源照片
- `archive/` —— 旧 PocketBase 后端和写稿前端，只作备份，不参与构建
