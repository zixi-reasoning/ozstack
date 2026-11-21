# 兔狲大力玩

> AI 时代的编程大力玩。
>
> 不用框架，不用花活，一行一行手搓。

兔狲大力玩（英文名 OzStack）是籽溪的两本书，也是这两本书的静态站点。两本书共用一台机器：**Aletheia**，中文诨名“大力丸一号”。

- **《古法编程大力玩》**：从一块 512 字节的连续数组开始，四卷、约四十章，造出一台 256 KiB 的计算机。它不加载 libc、libm、动态链接器，也不启动第二个运行时。第三卷最后，用 C 写成的机器会直接读懂一小片 C。
- **《计算科学大力丸》**：机器造好之后，搬进实验室。四卷、四十章，用同一台机器做数值实验、迭代、复杂度、概率和学习的见证。它不是第二本算法教程，而是一本计算科学实验教材。数学负责讲述，机器负责作证。

两本书都没有图。正文只有汉字、LaTeX、C 代码和终端字符输出。

## 两本书

| 书 | 导读 | 在线地址 | 状态 |
| --- | --- | --- | --- |
| 古法编程大力玩 | [导读](./docs/gufa/introduction/index.md) | [打开](https://zixi-reasoning.github.io/ozstack/gufa/introduction/) | 导读完成，正文按卷推进 |
| 计算科学大力丸 | [导读](./docs/jisuan/introduction/index.md) | [打开](https://zixi-reasoning.github.io/ozstack/jisuan/introduction/) | 导读完成，正文按卷推进 |

第一册四卷：

1. **有什么。** 内存里到底有什么？
2. **怎么放。** 同一块内存能变成什么？
3. **怎么动。** 怎么在计算机里再造一台计算机？
4. **怎么想。** 机器怎么自己找办法？

第二册四卷：

1. **数字究竟可信吗？** 从整数位宽、溢出、定点数、舍入和条件数开始，研究误差怎样产生、传播和被放大。
2. **答案是怎样逼近的？** 从迭代、不动点、收敛速度和停止准则开始，走到线性方程组、牛顿法、数值积分和梯度下降。
3. **计算究竟有多难？** 有了成本模型，再认真谈论时间、空间、搜索、归约和复杂性边界。
4. **机器究竟学到了什么？** 从概率、蒙特卡罗、信息熵走到参数估计、最小二乘、神经网络、泛化和鲁棒性。

两篇导读首尾相接。第一册问：AI 时代，程序员怎样把计算机从一块数组里造出来？第二册问：机器算出来的东西，我们凭什么相信？

## 写法规矩

这些规矩不是排版偏好，是书的一部分。

- **没有图。** 没有图片、截图、SVG、Mermaid、字符画插图，也没有误差曲线、收敛曲线和损失曲线。只有汉字、LaTeX、C 代码和电传记录。
- **纯 Markdown 和 LaTeX。** 不用 Vue 组件，不用 VitePress `:::` 容器。行内公式写 `$...$`，块级公式写 `$$...$$`，不写 `\(...\)` 或 `\[...\]`。
- **代码直接写在章节里。** 不另存 `.c` 文件，不放到 `docs/public/code`，不给下载链接。代码块第一行用注释写出建议文件名，读者复制后自己保存、编译、运行。
- **机器是封闭的。** Aletheia 的全部内存是一块静态数组，内部不加载 libc、libm、动态链接器或第二个运行时。需要什么，就自己写进机器里。
- **用 C 造机器，机器再跑 C。** 第三卷的 `AletheiaC` 直接解释一小片 C，不调用宿主编译器。变量、数组、指针、`if`、`while`、函数和递归都在同一块数组里发生。
- **证明和见证分开。** 第二册的有限实验是证据，不是证明。实验记录要写清精度、种子、步数上限、内存上限和状态，结论要回到数学条件。

## 站点

站点是纯静态 VitePress，没有登录、注册和后台。

- 左栏只管大跳：这本书有哪些章，点一下换章。
- 右栏只管小跳：当前这一章有哪些小节，点一下落到标题。
- 每本书不设单独主页。点书名直接进第一章。
- 左栏目录和首页入口都从 `docs/.vitepress/books.mjs` 取；右栏大纲由 VitePress 按当前页标题自动生成。
- 视觉是灰绿纸面、单色半调网点和 Chomsky 报头。字体、色板和版面都在 `docs/.vitepress/theme/custom.css`。

## 目录结构

章节目录照 Datawhale `repo-template`：一本书一个目录，一章一个英文标题文件夹，文件夹里放 `index.md`。

```text
docs/
  index.md                      首页
  gufa/
    introduction/
      index.md                  古法编程大力玩，导读
  jisuan/
    introduction/
      index.md                  计算科学大力丸，导读
  .vitepress/
    books.mjs                   两本书的章目录，唯一目录源
    config.mts                  导航、侧栏、搜索、公式
    theme/
      index.js
      custom.css
  public/
    logo.svg
    images/halftone-portrait.webp
    fonts/Chomsky.woff2
assets/
  portrait.jpg                  首页半色调肖像的源照片
```

- 每章一个英文标题文件夹，里面放 `index.md`。文件夹名用小写连字符，例如 `bytes-and-addresses`。
- 加一章：在书目录下建文件夹，写 `index.md`，再去 `books.mjs` 加一条。左栏只列到章。
- 加一节：直接在这一章里写 `## 2.3 ...`，右栏大纲会自动出现，不用另建文件。
- 每本书的 `start` 指向第一章。书名和首页入口直接进第一章，不设书主页。

## 本地开发

```bash
npm install
npm run docs:dev
```

打开 <http://localhost:5173>。

## 构建与发布

本地构建：

```bash
npm run docs:build
```

GitHub Pages 项目站挂在 <https://zixi-reasoning.github.io/ozstack/>。仓库名和 Pages 路径目前仍是 `ozstack`，所以旧链接不会断。工作流在 `.github/workflows/deploy.yml`，推送到 `main` 自动构建部署。构建时传入子路径：

```bash
DOCS_BASE=/ozstack/ npm run docs:build
```

仓库第一次部署前，在 GitHub 仓库的 Settings → Pages → Build and deployment 里把 Source 设成 **GitHub Actions**。之后每次推送 `main` 都会重新发布。

## 文件

| 路径 | 用途 |
| --- | --- |
| `docs/gufa/introduction/index.md` | 第一册导读：AI 时代为什么还要从字节和数组手搓 |
| `docs/jisuan/introduction/index.md` | 第二册导读：机器造好之后怎样用它做数学 |
| `docs/index.md` | 首页、两本书入口、手搓大力丸 |
| `docs/.vitepress/books.mjs` | 两本书的章目录 |
| `docs/.vitepress/config.mts` | 导航、右栏大纲、本地搜索、数学、页脚 |
| `docs/.vitepress/theme/` | 主题入口与样式 |
| `docs/public/logo.svg` | 灰绿方块标记 |
| `docs/public/images/halftone-portrait.webp` | 首页半色调肖像 |
| `docs/public/fonts/Chomsky.woff2` | 报头字体，SIL OFL，许可见同目录 |
| `assets/portrait.jpg` | 首页半色调肖像的源照片 |
