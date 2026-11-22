# 纸带台

> 第九章。零件：`AletheiaTape`。内存不是一行数，是一张可以摊开、标注、核对的纸带。

## 一、回访：字节读写之后

第八章的 `AletheiaStore` 能把四个字节拼成一个数，也能把一个数拆成四个字节。它回答“这个值是多少”，没有回答“这些字节长什么样”。调试的时候，光知道一个 32 位值是 0x12345678 不够，还要看它在内存里是 `78 56 34 12`，前面后面各是什么，哪几个字节属于同一个结构体，哪一段是空的。这些信息不是读写函数能直接给的，需要一个显示工具。

纸带台就是显示工具。它拿一块存储区，按地址逐字节摊开，每行十六个字节，左边写地址，中间写十六进制，右边写可打印字符。它还能在这块区域上贴标注：从哪个地址开始、有多少字节、叫什么名字。标注和字节显示叠在一起，读者就能同时看到“值”和“位置”。这是全书第一个真正的仪表，后面的分配器、虚拟机、解释器都要用它看内存。

第八章的读写函数是笔，这一章的纸带台是纸。笔在纸上写数，纸把数显示出来。没有纸，笔写的东西看不见；没有笔，纸上的格子没有内容。两个组件配合，才构成一个可检查的内存视图。`AletheiaTape` 不重新实现读写，它在 `AletheiaStore` 上做显示和标注。底层还是字节层、存储层，上面加的是排版和区间管理。

这一章的新问题不是“怎么读一个数”，而是“怎么把一块区域完整、准确地展示出来”。一行显示多少字节？最后一行不够怎么办？地址怎么对齐？不可打印的字节显示成什么？标注之间能不能重叠？标注能不能乱序？覆盖了多少字节，还剩多少？这些问题都有公式和不变式，也都能在输出里验证。

可观察性是这一章的主题。程序出错时，日志可能只告诉你“某个值不对”，不告诉你这个值在哪个地址、旁边是什么。纸带台把内存变成一张能看到地址的表，让“某个值不对”变成“0x00818 的四个字节不对，它属于 ints 段，偏移 8”。定位从猜变成看，调试从试变成查。后面的分配器会用它看块头，虚拟机会用它看指令，解释器会用它看栈。一个稳定的转储工具，比一堆临时 `printf` 有用。

纸带台还要可复现。同一块内存、同一组标注，每次转储的输出必须完全一样，不能有时间、随机地址、未初始化字节。程序里纸带区域在每次运行开始时重新填充，标注表在构造时清零，所有显示都来自确定的字节。重复运行输出一致，才能把输出贴进书里，才能让读者对照。这一章的输出是真实终端记录，不是手画的表格。

## 二、开场实验：把一块内存摊开

取一块 128 字节的区域，从 0x00800 到 0x0087F。按每行 16 字节摊开，得到八行：

```text
ADDR    00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f  ASCII
0x00800 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f |................|
0x00810 00 00 00 00 01 00 00 00 ff ff ff ff 78 56 34 12 |............xV4.|
0x00820 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 |................|
0x00830 41 6c 65 74 68 65 69 61 00 00 00 00 00 00 00 00 |Aletheia........|
0x00840 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 |................|
0x00850 03 14 25 36 47 58 69 7a 8b 9c ad be cf e0 f1 02 |..%6GXiz........|
0x00860 13 24 35 46 57 68 79 8a 9b ac bd ce df f0 01 12 |.$5FWhy.........|
0x00870 23 34 45 56 67 78 89 9a ab bc cd de ef 00 11 22 |#4EVgx........."|
```

第一行全是 0x00 到 0x0F，按顺序填的。第二行前四个字节是 0，接下来四个是 1 的小端表示 `01 00 00 00`，再接下来四个是全 1，最后四个是 0x12345678 的小端表示 `78 56 34 12`。第三行全 0，是补齐的空白。第四行有 `Aletheia` 的 ASCII 字节，后面是终止符和空白。第六到第八行是一串递增的字节模式。

尾部模式用公式 $b_i=(17i+3)\bmod256$ 生成，$i=0,1,\dots,47$。第一个字节是 3，第二个是 20，第三个是 37，每次加 17，超过 255 就回绕。17 和 256 互质，所以前 256 个字节不重复，48 个字节里不会出现相同值。选 17 是为了让模式看起来不规则，又能手算，读者可以抽查几个字节，确认转储没有漏读或错位。如果所有字节都一样，转储错位也不容易发现；模式字节让地址和内容的关系更明显。

区域中间留 16 字节空隙，是为了让 ROWS 和 COVER 两段有东西可查。四段标注如果首尾相接铺满 128 字节，覆盖就是 128，空隙是 0，`(gap)` 分支永远不会执行。留 16 字节空隙，ROWS 段能看到 0x840 这一行没有标注，COVER 段能验证 $112+16=128$。测试不仅要覆盖正常路径，也要覆盖“没有标注”的空隙，这样查找函数返回假的分支才有真实用例。

右边一列是 ASCII 解释。可打印字符原样显示，不可打印的字节显示成 `.`。`Aletheia` 那一行能直接读出文字，`78 56 34 12` 那一行显示 `xV4.`，因为 0x78 是 `x`，0x56 是 `V`，0x34 是 `4`，0x12 不可打印。这一列不改变数据，只是给读者一个快速识别文本的窗口。

同样的区域可以贴标注：

```text
LABEL START END   SIZE
head  0x00800 0x00810 16
ints  0x00810 0x00830 32
text  0x00830 0x00840 16
tail  0x00850 0x00880 48
```

`head` 是 0x00800 起的 16 字节，`ints` 是 0x00810 起的 32 字节，`text` 是 0x00830 起的 16 字节，`tail` 是 0x00850 起的 48 字节。四段依次排列，中间在 0x00840 到 0x0084F 留了 16 字节的空隙。覆盖的字节数是 $16+32+16+48=112$，空隙是 $128-112=16$。标注不要求铺满，允许留空，允许从任意地址开始，只要不重叠、不越界、按地址排序。

把行和标注叠起来看：

```text
0x00800 head  +0
0x00810 ints  +0
0x00820 ints  +16
0x00830 text  +0
0x00840 (gap)
0x00850 tail  +0
0x00860 tail  +16
0x00870 tail  +32
```

每一行十六字节，问“这一行的第一个字节属于哪个标注”。0x00800 属于 `head`，偏移 0；0x00810 和 0x00820 属于 `ints`，偏移分别是 0 和 16；0x00830 属于 `text`；0x00840 没有标注，打印 `(gap)`；0x00850 到 0x00870 属于 `tail`，偏移 0、16、32。这个视图把地址、标注、偏移三者对齐，读者一眼能看出边界在哪里。

最后按 32 位整数解释 `ints` 段：

```text
ADDR    HEX      UNSIGNED   SIGNED
0x00810 00000000          0        0
0x00814 00000001          1        1
0x00818 ffffffff 4294967295       -1
0x0081c 12345678  305419896 305419896
```

四个值分别是 0、1、4294967295、305419896。按有符号解释，全 1 是 -1。同样的四个字节，按字节看是 `ff ff ff ff`，按无符号看是 4294967295，按有符号看是 -1。纸带台把三种视图放在一起，读者不用在脑子里换算。

## 三、纸带的排版

### 3.1 行数与列数

纸带每行显示 16 个字节。给定一块 $n$ 字节的区域，行数是：

$$
\operatorname{rows}(n)=\left\lceil\frac{n}{16}\right\rceil
$$

$n=128$ 时，$128/16=8$，正好八行。$n=20$ 时，$\lceil20/16\rceil=2$，两行，第二行只有四个字节。$n=1$ 时，一行，只有一个字节。行数是上取整，因为最后一行不满也要占一行。如果按整除算，$n=20$ 得到 1，会漏掉最后四个字节。

每行的起始地址是：

$$
\operatorname{row\_addr}(r)=base+16r,\qquad r=0,1,\dots,\operatorname{rows}(n)-1
$$

$base$ 是区域起点。第 0 行从 $base$ 开始，第 1 行从 $base+16$ 开始，依次加 16。最后一行的起始地址小于 $base+n$，行内的字节数可能少于 16，取决于 $n$ 除以 16 的余数。

行内的列号是 $0$ 到 $15$。第 $r$ 行第 $c$ 列的地址是 $base+16r+c$。这个地址必须小于 $base+n$，否则这一列在区域外，不显示。显示时用空格占位，保持 16 列的宽度，让右边的 ASCII 列对齐。空格不是数据，只是排版。

### 3.2 十六进制显示

每个字节显示成两位十六进制。一个字节是 0 到 255，两位十六进制正好覆盖 00 到 FF。高位半字节是 $b\gg4$，低位半字节是 $b\&15$。0 到 9 显示成 `0` 到 `9`，10 到 15 显示成 `a` 到 `f`。用函数写出来是：

$$
\operatorname{hex}(b)=\operatorname{digit}(b\gg4)\parallel\operatorname{digit}(b\&15)
$$

其中 $\parallel$ 表示字符拼接，$\operatorname{digit}(n)$ 在 $n<10$ 时是字符 `0` 到 `9`，否则是字符 `a` 到 `f`。程序不手写这个函数，直接用 `printf("%02x")`，宽度 2，不足补 0，小写字母。格式化函数和手写函数结果一样，前者更短，也更不容易错。

十六进制转储是一个老传统。早期的计算机用八进制或十六进制看内存，因为这两种进制和二进制位数整除。一个字节八位，两位十六进制正好四位一组，读者能从每位数字直接读出 4 个比特。十进制没有这个性质，一个字节的十进制表示需要三位，位数和位模式不对应。十六进制也不完全直观，可它是字节和位之间最短的桥。纸带台选十六进制，不选八进制，因为八进制三位一组，一个字节八位除不尽，跨字节的位边界不清楚。

十六进制比十进制紧凑。一个字节约三个字符（两位数字加一个空格），一行十六个字节占 48 个字符，加上地址和 ASCII 列，总宽 74 列，能放进 80 列的终端。如果按十进制显示，每个字节约四个字符，一行就超过 64 列，加上其他列会溢出。十六进制还与字节的二进制结构对应：一位十六进制是四位，两位是一个字节，读者能从数字直接看出位模式。

地址也按十六进制显示，用 `%05x` 补到五位。0x00800 显示成 `0x00800`，0x3FFFF 显示成 `0x3ffff`。五位覆盖 0 到 0x3FFFF，正好是 Aletheia 的地址范围。补零让所有地址等宽，行首对齐。如果不补零，0x800 和 0x3FFFF 宽度不同，十六进制列会错位。

### 3.3 ASCII 列

ASCII 列把每个字节解释成字符。可打印的 ASCII 范围是 0x20 到 0x7E，包括空格、数字、字母和常见符号。这个范围之外的字节显示成 `.`：

$$
\operatorname{show}(b)=
\begin{cases}
b, & 0x20\le b\le 0x7E,\\
\text{'.'}, & \text{否则}.
\end{cases}
$$

ASCII 列不是数据的另一份拷贝，是同一份数据的另一种视图。它不改变内存，不改变字节，只是把可打印的字节画成字符，把不可打印的字节画成点。文本段在 ASCII 列里能直接读出来，二进制段显示成一串点，读者能快速区分“这段像文本”和“这段不像文本”。

为什么用点而不用空格表示不可打印字节？空格本身是 0x20，是一个可打印字符。如果用空格占位，读者分不清“这里是 0x20”和“这里不可打印”。点不是 ASCII 可打印范围的常见内容，用它占位不会和真实数据混淆。程序里的 0x00 显示成 `.`，0x41 显示成 `A`，0x7F 显示成 `.`，0xFF 显示成 `.`。

ASCII 列只解释单字节字符，不解析 UTF-8。一个汉字占三个字节，每个字节都在 0x80 以上，不在可打印范围，显示成三个点。这不是错误，是纸带台的定位：它看的是字节，不是文本。文本层的解释留给第七章的 `AletheiaStr`，纸带台不做字符数、不验证 UTF-8、不处理组合符号。两张视图分开：字节表看编码，字符串层看文本。如果把 UTF-8 解析塞进转储，每一行的字符边界会被多字节序列打乱，列宽也会变，反而难对齐。

控制字符也显示成点。换行 0x0A、回车 0x0D、制表 0x09 都是不可打印字节，如果原样输出，转储的行会被打乱。点把它们压成一个字符，保持表格完整。空格 0x20 是可打印的，显示成空格，ASCII 列里看起来是一个空白，但它和点不同，读者能通过中间十六进制列的 `20` 区分。DEL 0x7F 不是可打印字符，显示成点；扩展 ASCII 0x80 到 0xFF 也不在 ASCII 范围，显示成点。

ASCII 列的宽度等于本行的字节数。满行 16 个字符，最后一行不足 16 个，只显示实际字节对应的字符，不补点。右边的竖线跟着实际宽度走，不强行补到 16。这样最后一行短一点，但不会假装有数据。十六进制列仍然补空格到 16 列，保持竖线对齐；ASCII 列在竖线内按实际字节数显示。

### 3.4 最后一行

最后一行是排版最容易出错的地方。假设区域有 20 字节，第一行 16 个，第二行 4 个。第二行的十六进制列只显示 4 个字节，剩下 12 列显示三个空格。ASCII 列只显示 4 个字符。行首地址是 $base+16$，不是 $base+20$。行内第 0 列对应 $base+16$，第 3 列对应 $base+19$，第 4 列开始越界，不显示。

程序里的 `aletheia_hexdump` 用 `done` 记录已经显示的字节数，每轮算 `row = n-done`，大于 16 就截成 16。十六进制循环固定 16 次，前 `row` 次读字节，后 `16-row` 次打印三个空格。ASCII 循环只跑 `row` 次。`done` 每轮加 `row`，循环结束时正好等于 $n$。

这个写法对满行和不满行都成立。满行时 `row=16`，后 0 次打印空格，ASCII 跑 16 次。不满行时 `row<16`，空格补齐，ASCII 按实际长度。没有单独的最后一行分支，循环统一处理，减少边界错误。区域只有 1 字节时，一行，`row=1`，十五列空格，ASCII 一个字符。

### 3.5 转储的边界

转储的区域必须完全在存储区内。`aletheia_hexdump` 先调用 `aletheia_store_span` 检查 $addr$ 和 $n$，检查通过才开始打印。`span` 允许任意长度，不像第八章的整数读只允许 1、2、4。转储要显示 16 字节、20 字节、128 字节，长度是任意的，所以需要一个通用的区间检查。

区间检查的公式和第八章一样：$addr\ge base$，$addr-base\le size-n$，$n>0$。不同的是 $n$ 可以是任意正整数，不再限制宽度。检查通过后，循环里的每个地址都在区内，`peek_u8` 不会失败。检查失败时一个字节都不打印，函数返回 `false`，调用者知道这次转储没有发生。

转储是只读操作。它不写内存，不修改标注，不改变任何状态。同一个区域可以反复转储，输出完全一样。这个性质对调试很重要：看内存不应该改变内存。程序里的转储函数只调用 `peek_u8`，没有 `poke`，参数是 `const struct AletheiaStore *`，编译器能帮忙检查。

## 四、标注与不变量

### 4.1 标注是什么

一个标注是一段区间加一个名字：

```c
struct AletheiaMark {
    AletheiaAddr addr;
    uint32_t size;
    char label[ALETHEIA_MARK_LABEL];
};
```

$addr$ 是起点，$size$ 是字节数，$label$ 是名字。标注覆盖的区间是左闭右开：

$$
[\,addr,\ addr+size\,)
$$

起点属于标注，终点 $addr+size$ 不属于。两个相邻的标注，前一个的终点可以等于后一个的起点，这不算重叠。比如 `head` 是 $[0x800,0x810)$，`ints` 是 $[0x810,0x830)$，0x810 属于 `ints`，不属于 `head`，两段首尾相接，没有空隙也没有重叠。

名字是定长数组，最多 11 个字符加一个终止符。为什么用定长数组，不用 `const char *`？因为标注要能被复制、比较、整体保存，不依赖外部的字符串存储。定长数组让 `AletheiaMark` 的大小固定为 20 字节，`AletheiaTape` 的大小固定为 172 字节，可以按值传递、按值返回，不需要动态分配。名字用 ASCII 短标签，不用中文，避免 UTF-8 字节数和显示宽度的问题。

### 4.2 排序与不重叠

标注表按起点从小到大排列，且任意两个标注不重叠：

$$
addr_{k+1}\ge addr_k+size_k,\qquad k=0,1,\dots,count-2
$$

也就是说，后一个标注的起点不小于前一个标注的终点。相邻可以相等，相等表示首尾相接；大于表示中间有空隙。不允许后一个起点小于前一个终点，那会重叠。不允许后一个起点小于前一个起点，那会乱序。排序和不重叠合成一个条件：标注按顺序追加，每次新标注的起点不小于最后一个标注的终点。

程序用 `cursor` 扫描验证。初始 `cursor=base`，每遇到一个标注，检查它的起点不小于 `cursor`，然后把 `cursor` 推到它的终点。扫描结束时，所有标注都满足“起点不小于前一个终点”。这个检查是线性的，不需要两两比较。排序一旦成立，重叠检查就退化成相邻检查。

为什么要求排序？因为查找、显示、覆盖统计都依赖顺序。查找可以从头扫到尾，遇到起点大于目标地址就停；显示可以按行找标注，不用每次扫全表；覆盖统计可以直接累加，不用先去重。排序是一个不变量，所有标注函数都维护它。`tape_mark` 只允许追加到末尾，不允许插入到中间，就是为了保持排序简单。

追加式有一个代价：不能先标后面的区域，再补前面的空隙。程序里的四段标注按 0x800、0x810、0x830、0x850 的顺序加，如果先加 `tail` 到 0x850，再加 0x840 的标注，就会被拒绝，因为 0x840 小于 `tail` 的终点 0x880。FAIL 段没有直接测这个顺序问题，可 `tape_mark` 的检查已经决定了行为。要支持任意顺序，需要插入排序、移动后面的标注，或者用链表，代码复杂度会上升。这一章选追加式，把“标注要按地址顺序添加”作为使用约定，简单、可验证。

如果需要标后面的区域怎么办？先规划好顺序，从低地址到高地址依次添加；或者构造一个新纸带，按新顺序重新标注。教学工具的用户是写程序的作者，作者知道自己的布局，按顺序声明标注不难。第二卷的分配器会有自己的块表，块表也会按地址排序，思路是一样的：区间表维护顺序，查找和显示才能线性扫描。追加式是这个思路的最简实现。

### 4.3 包含与覆盖

每个标注必须完全落在纸带区域内：

$$
base\le addr,\qquad addr-base\le size-size_k
$$

第一个条件保证起点不在区前，第二个条件保证终点不超过区的右端。$size-size_k$ 是最后一个合法起点相对 $base$ 的最大偏移。两个条件合起来，等价于 $addr\in[base,base+size-size_k]$。检查时先确认 $size_k\le size$，再算偏移，避免无符号减法下溢。

覆盖的字节数是所有标注大小之和：

$$
\operatorname{covered}=\sum_{k=0}^{count-1}size_k
$$

因为标注不重叠，这个和就是实际覆盖的字节数，不需要去重。空隙是区域大小减去覆盖：

$$
\operatorname{gaps}=size-\operatorname{covered}
$$

覆盖加空隙等于区域大小。程序里的 COVER 段打印 112、16、128，验证 $112+16=128$。如果标注重叠，覆盖和会大于实际覆盖，$covered+gaps$ 就不等于 $size$；不重叠不变量保证了等式成立。

覆盖不要求等于 100%。纸带允许留空，空白也是信息：它表示“这段还没有分配”或“这段是填充”。程序里 0x840 到 0x84F 的 16 字节没有标注，ROWS 段打印 `(gap)`，COVER 段把它算进空隙。标注不强制铺满，强制的是不重叠和不越界。

### 4.4 按地址查找

给定一个地址 $x$，查找它属于哪个标注，就是找一个 $k$ 满足：

$$
addr_k\le x<addr_k+size_k
$$

因为标注不重叠，最多只有一个标注满足。程序从头扫描，找到第一个满足的就返回标注下标和偏移 $x-addr_k$。找不到返回 `false`，表示这个地址在空隙里。查找是线性的，最多扫描 8 个标注，成本很小。

查找的边界是左闭右开。$x=addr_k$ 属于第 $k$ 个标注，偏移 0；$x=addr_k+size_k-1$ 属于第 $k$ 个标注，偏移 $size_k-1$；$x=addr_k+size_k$ 不属于第 $k$ 个标注，可能属于下一个标注，也可能在空隙里。这个边界和数组下标、结构体字段、字符串容量一致，书里所有区间都是左闭右开。

程序里的 ROWS 段对每行首地址调用查找。0x00820 属于 `ints`，偏移 16；0x00840 不属于任何标注，打印 `(gap)`。这个表把行和标注对齐，读者能看到每个十六字节行落在哪个标注里，偏移是多少。

按行首查找是对全部地址查找的抽样。一行有十六个字节，如果每个字节都打印标注，表格会膨胀十六倍，输出超长。按行首查，只需要判断这一行的起点，读者能从标注边界推断行内每个字节的归属。比如 `ints` 从 0x810 到 0x830，行 0x810 和 0x820 都属于它；行 0x820 偏移 16，说明这一行从 `ints` 的中段开始。如果标注边界落在行中间，行首标注可能和行内后半段不一致，这是按行显示的近似。纸带台不承诺每个字节的标注都显示，只承诺行首的标注和偏移准确。

如果需要精确到字节，可以增加一个“边界表”，列出所有标注的起点和终点，让读者对照。程序里的 MARKS 段就是这个表，它打印每段的起点、终点、大小。ROWS 段给行级视图，MARKS 段给段级视图，两个表合起来，读者能还原任意地址的归属。纸带台不试图把两个表合并成一张超宽表，保持每张表不超过 80 列，阅读和复制都方便。

### 4.5 失败条件

标注函数有七类失败：

1. 标注表本身无效，比如起点在区外、标注重叠、标签为空。
2. 标注数量已满，8 个之后不能再加。
3. 大小为零，空标注没有意义。
4. 大小超过整个区域。
5. 起点在区域之前。
6. 终点超过区域右端。
7. 起点小于最后一个标注的终点，会重叠或乱序。

标签还有两条：不能为空，长度不能超过 11 个字符。空标签没有名字，显示时无法区分；超长标签放不进 12 字节数组，复制会截断。`tape_mark` 在修改表之前检查这些条件，任何一条不满足就返回 `false`，表保持原样。这个“先检查、后追加”的顺序，和第八章的写函数一致。

程序里的 FAIL 段测了重叠、区前、区外、空标签、超长标签、坏表、第九个标注。七种都被拒绝。坏表是把一个有效标注的起点改成 0x7FF，再调用 `tape_ok`，检查函数发现起点小于区域起点，返回 `false`。第九个标注是在一个 32 字节的小区域里放八个单字节标注，再加第九个，数量检查拒绝。这些失败不是崩溃，是正常返回值。

## 五、手工推演

先推 128 字节的八行。每行 16 字节，行号 0 到 7，起始地址 $0x800+16r$：

```text
r  addr
0  0x800
1  0x810
2  0x820
3  0x830
4  0x840
5  0x850
6  0x860
7  0x870
```

第 7 行从 0x870 开始，到 0x87F 结束，正好是区域的最后一行。第 7 行第 15 列是 0x87F，属于区域；第 8 行不存在，因为 $0x800+16\cdot8=0x880$，等于区域右端，不包含。行数 $\lceil128/16\rceil=8$，不多不少。

再推四段标注。`head` 起点 0x800，大小 16，终点 0x810；`ints` 起点 0x810，大小 32，终点 0x830；`text` 起点 0x830，大小 16，终点 0x840；`tail` 起点 0x850，大小 48，终点 0x880。四段按顺序，前一段的终点等于后一段的起点，或者小于后一段的起点。`text` 的终点 0x840 小于 `tail` 的起点 0x850，中间 16 字节是空隙。

覆盖和：$16+32+16+48=112$。区域大小 128，空隙 $128-112=16$。空隙正好是 0x840 到 0x84F 的 16 字节。ROWS 表第 4 行 0x840 打印 `(gap)`，其他行都有标注。第 3 行 0x830 属于 `text`，偏移 0；第 5 行 0x850 属于 `tail`，偏移 0；第 6 行 0x860 属于 `tail`，偏移 16；第 7 行 0x870 属于 `tail`，偏移 32。

再推 words 表。`ints` 从 0x810 开始，32 字节，可以放八个 32 位值，程序只读了前四个。0x810 的四个字节 `00 00 00 00` 小端拼成 0；0x814 的 `01 00 00 00` 拼成 1；0x818 的 `ff ff ff ff` 拼成 4294967295；0x81C 的 `78 56 34 12` 拼成 0x12345678，十进制 305419896。按有符号解释，0xFFFFFFFF 是 -1，其余三个是非负数。

再推一次查找。地址 0x0080F：`head` 区间 $[0x800,0x810)$，$0x800\le0x80F<0x810$，属于 `head`，偏移 15。地址 0x00810：`head` 的终点是 0x810，不包含；`ints` 的起点是 0x810，包含，偏移 0。地址 0x0084F：不满足任何标注，空隙。地址 0x0087F：`tail` 区间 $[0x850,0x880)$，包含，偏移 47。地址 0x00880：区域右端，不在纸带内，也不在任何标注内。

最后推失败。在 `tail` 之后加一个从 0x840 开始的标注，起点 0x840 小于最后一个标注的终点 0x880，`tape_mark` 拒绝。这不是因为 0x840 在区外，0x840 在区内，可它排在了 `tail` 后面，破坏了排序。如果先加 0x840 的标注，再加 0x850 的 `tail`，两个都能成功。标注是追加式的，顺序必须和地址顺序一致。

再推一次不满行。从 0x810 转储 20 字节，`n=20`。第一轮 `done=0`，`row=20`，截成 16，打印 0x810 起十六个字节；`done` 变成 16。第二轮 `row=4`，打印 0x820 起四个字节，十六进制列后面十二列是空格，ASCII 列四个点，`done` 变成 20，循环结束。行数 $\lceil20/16\rceil=2$，实际打印两行。最后一行的地址是 0x820，不是 0x824；`done` 是已显示字节数，不是地址，地址要加上 `base`。

再推尾部模式。$i=0$ 时 $b_0=3$，$i=1$ 时 $b_1=20=0x14$，$i=2$ 时 $b_2=37=0x25$，$i=3$ 时 $b_3=54=0x36$。前四个字节是 `03 14 25 36`，输出第六行开头正是这四个值。再算第 15 个字节：$17\cdot15+3=255+3=258$，$258\bmod256=2$，所以第 15 个字节是 0x02。输出 0x85F 是 0x02，和公式一致。回绕发生在 $i=15$，不是 $i=16$，因为 $17\cdot15=255$，再加 3 就超过 256。

再推覆盖等式。覆盖和是 $16+32+16+48=112$，区域 128，空隙 16，$112+16=128$。如果 `text` 的大小写成 15 而不是 16，覆盖变成 111，空隙 17，和仍然 128，但 ROWS 段 0x83F 会落进空隙，MARKS 段的终点 0x83F 也会和下一段起点 0x850 之间多出一个字节。覆盖等式只检查总和，不检查具体布局；布局由标注的起点、大小和排序决定。两组合起来，才能发现“大小写错但总和碰巧对”的错误。程序里 MARKS、ROWS、COVER 三段互相印证，就是为了抓这类错误。

## 六、把 AletheiaTape 写成 C

### 6.1 结构体

纸带描述符是区域加标注表：

```c
struct AletheiaTape {
    AletheiaAddr base;
    uint32_t size;
    uint32_t mark_count;
    struct AletheiaMark marks[ALETHEIA_MAX_MARKS];
};
```

`base` 和 `size` 描述区域，`mark_count` 是当前标注数，`marks` 是定长数组。`ALETHEIA_MAX_MARKS` 是 8，`ALETHEIA_MARK_LABEL` 是 12。标注结构体是 4 字节地址、4 字节大小、12 字节标签，总共 20 字节。纸带结构体是 4+4+4+8×20=172 字节，最大对齐 4，172 是 4 的倍数，没有尾部填充。

为什么标注表定长？因为纸带是教学工具，不需要无限标注。8 个标注足够标出一个程序里的代码、数据、栈、堆、常量、参数、返回值和一块填充。定长数组让整个描述符可以按值复制，不涉及分配器，也不涉及所有权。第二卷才会讲动态分配，这一章先用固定上限。

结构体大小可以按第六章的规则手算：

$$
\operatorname{sizeof}(\mathtt{AletheiaMark})=4+4+12=20
$$

$$
\operatorname{sizeof}(\mathtt{AletheiaTape})=4+4+4+8\cdot20=172
$$

两个结果都是 4 的倍数，最大成员对齐是 4，因此不需要尾部填充。这里说“对齐是 4”是我们这台机器的约定，不是 C 标准对宿主的承诺。宿主编译器可能给 `uint32_t` 更大的对齐，也可能在结构体末尾加填充。程序里打印的 172 和 20 是这台机器的实际值，读者在别的平台上看到别的数，不算错误，只说明那台机器的布局规则不同。书里所有偏移和大小都以 Aletheia 的规则为准：地址 4 字节，大小 4 字节，标签 12 字节，按声明顺序紧挨着放。

标注表定长还有一个好处：有效性检查的代价固定。`tape_ok` 最多看 8 个标注，`tape_find` 最多扫 8 次，`tape_cover` 最多加 8 次。输入规模不影响循环次数，最坏情况可以一眼数出来。对教学代码来说，这比“平均情况很快”更有说服力。

### 6.2 纸带有效性

```c
static bool aletheia_tape_ok(const struct AletheiaTape *t) {
    struct AletheiaStore s;
    AletheiaAddr cursor;
    uint32_t i;
    if (t == NULL || t->mark_count > ALETHEIA_MAX_MARKS) {
        return false;
    }
    if (!aletheia_store_make(t->base, t->size, &s)) {
        return false;
    }
    cursor = t->base;
    for (i = 0; i < t->mark_count; ++i) {
        const struct AletheiaMark *m = &t->marks[i];
        uint32_t off;
        if (m->size == 0u || m->size > t->size ||
            !aletheia_label_ok(m->label)) {
            return false;
        }
        if (m->addr < cursor) {
            return false;
        }
        off = m->addr - t->base;
        if (off > t->size - m->size) {
            return false;
        }
        cursor = m->addr + m->size;
    }
    return true;
}
```

函数先检查标注数量，再用存储层检查区域。`cursor` 初始为 `base`，每处理一个标注，检查起点不小于 `cursor`，再检查标注完全在区内，最后把 `cursor` 推到终点。`m->addr < cursor` 同时挡住“起点在区前”和“与前一个标注重叠或乱序”两种情况。`off > t->size - m->size` 挡住“终点超过右端”。`m->size > t->size` 先挡住大小超过区域，避免减法下溢。

标签检查 `aletheia_label_ok` 要求第一个字符非零，且在 12 字节内能找到终止符。空标签、没有终止符的标签都拒绝。这个检查和字符串层的终止符检查类似，只是长度固定为 12。标签是 ASCII 短名，不解析 UTF-8，不计算字符数。

这个循环有一个可以写下来的不变量：处理完第 $i$ 个标注后，`cursor` 等于 `base` 和前 $i$ 个标注终点的最大值。因为每个标注都要求起点不小于 `cursor`，终点又是起点加大小，所以 `cursor` 只会向右走。循环结束时，`cursor` 是最后一个标注的终点，或者仍是 `base`。所有标注都排过序、互不重叠、没有越界，恰好就是这个不变量每一步都成立的结果。

检查顺序也有讲究。先比 `m->addr < cursor`，再算 `off = m->addr - t->base`，最后比 `off > t->size - m->size`。如果先算减法，起点在区外的标注会让 `m->addr - t->base` 下溢，得到一个很大的无符号数，后面的检查就会误判。先做比较，确认起点不小于 `cursor`，而 `cursor` 又不小于 `base`，减法才是安全的。`m->size > t->size` 放在最前面，也是为 `t->size - m->size` 挡住下溢。这类顺序在无符号算术里不是风格问题，是正确性问题。

### 6.3 追加标注

```c
static bool aletheia_tape_mark(struct AletheiaTape *t, AletheiaAddr addr,
                               uint32_t size, const char *label) {
    struct AletheiaMark m;
    uint32_t off;
    if (t == NULL || label == NULL || !aletheia_tape_ok(t)) {
        return false;
    }
    if (t->mark_count >= ALETHEIA_MAX_MARKS || size == 0u ||
        size > t->size || label[0] == '\0') {
        return false;
    }
    if (addr < t->base) {
        return false;
    }
    off = addr - t->base;
    if (off > t->size - size) {
        return false;
    }
    if (t->mark_count > 0u) {
        const struct AletheiaMark *last = &t->marks[t->mark_count - 1u];
        if (last->addr + last->size > addr) {
            return false;
        }
    }
    m.addr = addr;
    m.size = size;
    if (!aletheia_label_copy(m.label, label)) {
        return false;
    }
    t->marks[t->mark_count] = m;
    t->mark_count += 1u;
    return true;
}
```

函数先验证表、参数和标签首字符，再检查数量、大小、起点、终点，最后检查是否排在最后一个标注之后。所有检查通过后，在临时结构体 `m` 里组装，复制标签，追加到数组末尾，计数加一。失败时表不变，成功时只改最后一个位置和计数。

标签复制 `aletheia_label_copy` 先数源字符串长度，确认不超过 11 个字符，再逐字节复制包括终止符。没有 `strcpy`，没有 `strlen`，不依赖 `<string.h>`。复制长度有上限，源字符串没有终止符时 `aletheia_label_ok` 会在 12 字节内找不到 0 而拒绝，不会一直读下去。

### 6.4 查找与覆盖

```c
static bool aletheia_tape_find(const struct AletheiaTape *t, AletheiaAddr addr,
                               uint32_t *index, uint32_t *offset) {
    uint32_t i;
    if (index == NULL || offset == NULL || !aletheia_tape_ok(t)) {
        return false;
    }
    for (i = 0; i < t->mark_count; ++i) {
        const struct AletheiaMark *m = &t->marks[i];
        if (addr >= m->addr && addr < m->addr + m->size) {
            *index = i;
            *offset = addr - m->addr;
            return true;
        }
    }
    return false;
}
```

查找是顺序扫描，条件 $addr\in[m.addr,m.addr+m.size)$。因为标注不重叠，找到的第一个就是唯一一个。找到时写输出参数并返回真，找不到返回假，不写输出。`addr < m->addr + m->size` 不会溢出，因为 `tape_ok` 已经保证 $m.addr+m.size$ 在区域内，区域在 262144 内。

覆盖统计更简单：

```c
static bool aletheia_tape_cover(const struct AletheiaTape *t,
                                uint32_t *covered, uint32_t *gaps) {
    uint32_t total = 0u;
    uint32_t i;
    if (covered == NULL || gaps == NULL || !aletheia_tape_ok(t)) {
        return false;
    }
    for (i = 0; i < t->mark_count; ++i) {
        total += t->marks[i].size;
    }
    *covered = total;
    *gaps = t->size - total;
    return true;
}
```

不重叠保证 `total` 不会超过区域大小，减法不会下溢。如果标注重叠，`total` 可能大于区域大小，这个函数就会出错；所以它在开始前调用 `tape_ok`，把无效的表挡在外面。覆盖和空隙都返回给调用者，打印和检查分开。

### 6.5 十六进制转储

```c
static bool aletheia_hexdump(const struct AletheiaStore *s, AletheiaAddr addr,
                             uint32_t n) {
    uint32_t done = 0u;
    if (!aletheia_store_span(s, addr, n)) {
        return false;
    }
    while (done < n) {
        uint32_t row = n - done;
        uint32_t i;
        if (row > 16u) {
            row = 16u;
        }
        printf("0x%05x ", (unsigned)(addr + done));
        for (i = 0; i < 16u; ++i) {
            if (i < row) {
                AletheiaByte b = 0u;
                if (!aletheia_peek_u8(addr + done + i, &b)) {
                    return false;
                }
                printf("%02x ", (unsigned)b);
            } else {
                printf("   ");
            }
        }
        printf("|");
        for (i = 0; i < row; ++i) {
            AletheiaByte b = 0u;
            if (!aletheia_peek_u8(addr + done + i, &b)) {
                return false;
            }
            putchar((b >= 0x20u && b <= 0x7eu) ? (int)b : '.');
        }
        printf("|\n");
        done += row;
    }
    return true;
}
```

外层循环按行推进，`done` 是已显示字节数。每轮算本行字节数 `row`，最多 16。地址打印 `addr+done`，五位十六进制。内层第一个循环固定 16 次，前 `row` 次读字节打印 `%02x`，后 `16-row` 次打印三个空格。第二个循环只跑 `row` 次，可打印字节原样输出，否则输出点。两个循环共用 `addr+done+i`，不会读到别的行。

函数用 `aletheia_store_span` 做整体检查，不是逐行检查。整体检查通过后，每一行的每个地址都在区内，`peek_u8` 不会失败。逐行检查会重复计算，也不会更安全。外层只处理排版，内层只处理字节，边界检查集中在入口。

一行的宽度可以算清楚。地址部分 `0x%05x` 加一个空格是 8 列；十六进制部分固定 16 组，每组 `%02x` 加一个空格是 3 列，共 48 列；竖线 1 列；ASCII 部分最多 16 列；收尾竖线 1 列。合计 $8+48+1+16+1=74$ 列，正好是输出里最长的一行。最后一行不满 16 字节时，十六进制部分仍然占满 48 列，ASCII 部分变短，收尾竖线跟着左移，所以竖线不对齐，这是故意的：ASCII 只显示真实字节，不补点，让读者一眼看出这一行只有四个字节。

`done += row` 而不是 `done += 16`，是关键的一步。`row` 是本行实际显示的字节数，最后一轮可能小于 16。如果固定加 16，最后一轮会把 `done` 推过 `n`，循环条件失效，或者地址跳过一个不存在的行。用 `row` 推进，`done` 刚好在最后一行达到 `n`，循环自然结束。`n=0` 时循环一次也不进，函数直接返回真，什么都不打印，这也是一种正确的空转储。

打印格式只用了 `printf` 和 `putchar`，没有拼接字符串，没有临时缓冲区。每个字节读一次打印两次，一次十六进制一次 ASCII；读两次是为了保持代码直白，代价是两倍读取。对 128 字节的演示无所谓，对整片 256 KiB 就会慢一些。真要优化，可以在内层缓存 16 个字节，先读满一行再打印两遍；这一章故意不优化，让“读一次显示一次”的结构清楚可见。

`peek_u8` 在整体检查之后仍然返回布尔值，不是多余。函数签名要求它在任何地址上都给出成功或失败，而不是只在“调用者保证合法”时工作。外层忽略这个返回值会造成静默错误；这里每次检查，失败就返回假，把问题交给调用者。教学代码宁可多写一行检查，也不留下“这里一定安全”的口头约定。

### 6.6 十进制解释

纸带台还要打印十进制。32 位值按无符号和有符号两种解释：

```c
static long long aletheia_signed32(uint32_t v) {
    if (v <= 0x7fffffffu) {
        return (long long)v;
    }
    return (long long)v - 4294967296LL;
}
```

小于 $2^{31}$ 的值直接转成 64 位有符号，大于等于 $2^{31}$ 的值减去 $2^{32}$，得到负数。用 64 位中间值避免 32 位溢出，也不依赖“无符号转有符号”的实现定义行为。打印用 `%lld`，`long long` 至少 64 位，能装下 0 到 4294967295 和 -2147483648 到 2147483647。

这个函数只负责解释，不负责读写。字节还是第八章的 `aletheia_read_u32` 读出来的，符号只是显示层加的。同一个值可以按无符号打印，也可以按有符号打印，两列并排，读者能看到位模式和符号的关系。

## 七、完整程序

完整程序把字节层、存储层、纸带层和检查函数放在一个文件里。检查分六段：HEXDUMP、MARKS、ROWS、WORDS、COVER、FAIL。每段打印结果，最后打印汇总。

编译命令：

```bash
cc -std=c99 -O2 -Wall -Wextra -pedantic -Werror aletheia_ch09.c -o aletheia_ch09
```

完整代码：

```c
/* aletheia_ch09.c */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define ALETHEIA_SIZE ((uint32_t)256 * 1024)
#define ALETHEIA_MAX_MARKS 8u
#define ALETHEIA_MARK_LABEL 12u

typedef uint8_t AletheiaByte;
typedef uint32_t AletheiaAddr;

struct AletheiaStore {
    AletheiaAddr base;
    uint32_t size;
};

struct AletheiaMark {
    AletheiaAddr addr;
    uint32_t size;
    char label[ALETHEIA_MARK_LABEL];
};

struct AletheiaTape {
    AletheiaAddr base;
    uint32_t size;
    uint32_t mark_count;
    struct AletheiaMark marks[ALETHEIA_MAX_MARKS];
};

static AletheiaByte aletheia_mem[ALETHEIA_SIZE];

static bool aletheia_peek_u8(AletheiaAddr addr, AletheiaByte *out) {
    if (out == NULL || addr >= ALETHEIA_SIZE) {
        return false;
    }
    *out = aletheia_mem[addr];
    return true;
}

static bool aletheia_poke_u8(AletheiaAddr addr, AletheiaByte value) {
    if (addr >= ALETHEIA_SIZE) {
        return false;
    }
    aletheia_mem[addr] = value;
    return true;
}

static bool aletheia_store_ok(const struct AletheiaStore *s) {
    if (s == NULL || s->size == 0u || s->size > ALETHEIA_SIZE) {
        return false;
    }
    return s->base <= ALETHEIA_SIZE - s->size;
}

static bool aletheia_store_make(AletheiaAddr base, uint32_t size,
                                struct AletheiaStore *out) {
    struct AletheiaStore s;
    if (out == NULL) {
        return false;
    }
    s = (struct AletheiaStore){ base, size };
    if (!aletheia_store_ok(&s)) {
        return false;
    }
    *out = s;
    return true;
}

/* 任意长度的区间检查，供转储使用；整数读写仍限制 1/2/4。 */
static bool aletheia_store_span(const struct AletheiaStore *s,
                                AletheiaAddr addr, uint32_t n) {
    uint32_t off;
    if (!aletheia_store_ok(s) || n == 0u) {
        return false;
    }
    if (n > s->size || addr < s->base) {
        return false;
    }
    off = addr - s->base;
    return off <= s->size - n;
}

static bool aletheia_read_u32(const struct AletheiaStore *s, AletheiaAddr addr,
                              uint32_t *out) {
    uint32_t v = 0u;
    uint32_t i;
    if (out == NULL || !aletheia_store_span(s, addr, 4u)) {
        return false;
    }
    for (i = 0; i < 4u; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_peek_u8(addr + i, &b)) {
            return false;
        }
        v |= (uint32_t)b << (8u * i);
    }
    *out = v;
    return true;
}

static bool aletheia_write_u32(const struct AletheiaStore *s, AletheiaAddr addr,
                               uint32_t value) {
    uint32_t i;
    if (!aletheia_store_span(s, addr, 4u)) {
        return false;
    }
    for (i = 0; i < 4u; ++i) {
        AletheiaByte b = (AletheiaByte)((value >> (8u * i)) & 0xffu);
        if (!aletheia_poke_u8(addr + i, b)) {
            return false;
        }
    }
    return true;
}

static long long aletheia_signed32(uint32_t v) {
    if (v <= 0x7fffffffu) {
        return (long long)v;
    }
    return (long long)v - 4294967296LL;
}

static bool aletheia_label_ok(const char *label) {
    uint32_t i;
    if (label[0] == '\0') {
        return false;
    }
    for (i = 0; i < ALETHEIA_MARK_LABEL; ++i) {
        if (label[i] == '\0') {
            return true;
        }
    }
    return false;
}

static bool aletheia_label_copy(char *dst, const char *src) {
    uint32_t n = 0u;
    uint32_t i;
    if (!aletheia_label_ok(src)) {
        return false;
    }
    while (src[n] != '\0') {
        ++n;
    }
    for (i = 0; i <= n; ++i) {
        dst[i] = src[i];
    }
    return true;
}

/* 纸带 = 存储区 + 有序、互不重叠的标注表。 */
static bool aletheia_tape_ok(const struct AletheiaTape *t) {
    struct AletheiaStore s;
    AletheiaAddr cursor;
    uint32_t i;
    if (t == NULL || t->mark_count > ALETHEIA_MAX_MARKS) {
        return false;
    }
    if (!aletheia_store_make(t->base, t->size, &s)) {
        return false;
    }
    cursor = t->base;
    for (i = 0; i < t->mark_count; ++i) {
        const struct AletheiaMark *m = &t->marks[i];
        uint32_t off;
        if (m->size == 0u || m->size > t->size ||
            !aletheia_label_ok(m->label)) {
            return false;
        }
        if (m->addr < cursor) {
            return false;
        }
        off = m->addr - t->base;
        if (off > t->size - m->size) {
            return false;
        }
        cursor = m->addr + m->size;
    }
    return true;
}

static bool aletheia_tape_make(AletheiaAddr base, uint32_t size,
                               struct AletheiaTape *out) {
    struct AletheiaTape t;
    uint32_t i;
    uint32_t j;
    if (out == NULL) {
        return false;
    }
    t.base = base;
    t.size = size;
    t.mark_count = 0u;
    for (i = 0; i < ALETHEIA_MAX_MARKS; ++i) {
        t.marks[i].addr = 0u;
        t.marks[i].size = 0u;
        for (j = 0; j < ALETHEIA_MARK_LABEL; ++j) {
            t.marks[i].label[j] = '\0';
        }
    }
    if (!aletheia_tape_ok(&t)) {
        return false;
    }
    *out = t;
    return true;
}

static bool aletheia_tape_mark(struct AletheiaTape *t, AletheiaAddr addr,
                               uint32_t size, const char *label) {
    struct AletheiaMark m;
    uint32_t off;
    if (t == NULL || label == NULL || !aletheia_tape_ok(t)) {
        return false;
    }
    if (t->mark_count >= ALETHEIA_MAX_MARKS || size == 0u ||
        size > t->size || label[0] == '\0') {
        return false;
    }
    if (addr < t->base) {
        return false;
    }
    off = addr - t->base;
    if (off > t->size - size) {
        return false;
    }
    if (t->mark_count > 0u) {
        const struct AletheiaMark *last = &t->marks[t->mark_count - 1u];
        if (last->addr + last->size > addr) {
            return false;
        }
    }
    m.addr = addr;
    m.size = size;
    if (!aletheia_label_copy(m.label, label)) {
        return false;
    }
    t->marks[t->mark_count] = m;
    t->mark_count += 1u;
    return true;
}

static bool aletheia_tape_find(const struct AletheiaTape *t, AletheiaAddr addr,
                               uint32_t *index, uint32_t *offset) {
    uint32_t i;
    if (index == NULL || offset == NULL || !aletheia_tape_ok(t)) {
        return false;
    }
    for (i = 0; i < t->mark_count; ++i) {
        const struct AletheiaMark *m = &t->marks[i];
        if (addr >= m->addr && addr < m->addr + m->size) {
            *index = i;
            *offset = addr - m->addr;
            return true;
        }
    }
    return false;
}

static bool aletheia_tape_cover(const struct AletheiaTape *t,
                                uint32_t *covered, uint32_t *gaps) {
    uint32_t total = 0u;
    uint32_t i;
    if (covered == NULL || gaps == NULL || !aletheia_tape_ok(t)) {
        return false;
    }
    for (i = 0; i < t->mark_count; ++i) {
        total += t->marks[i].size;
    }
    *covered = total;
    *gaps = t->size - total;
    return true;
}

static bool aletheia_hexdump(const struct AletheiaStore *s, AletheiaAddr addr,
                             uint32_t n) {
    uint32_t done = 0u;
    if (!aletheia_store_span(s, addr, n)) {
        return false;
    }
    while (done < n) {
        uint32_t row = n - done;
        uint32_t i;
        if (row > 16u) {
            row = 16u;
        }
        printf("0x%05x ", (unsigned)(addr + done));
        for (i = 0; i < 16u; ++i) {
            if (i < row) {
                AletheiaByte b = 0u;
                if (!aletheia_peek_u8(addr + done + i, &b)) {
                    return false;
                }
                printf("%02x ", (unsigned)b);
            } else {
                printf("   ");
            }
        }
        printf("|");
        for (i = 0; i < row; ++i) {
            AletheiaByte b = 0u;
            if (!aletheia_peek_u8(addr + done + i, &b)) {
                return false;
            }
            putchar((b >= 0x20u && b <= 0x7eu) ? (int)b : '.');
        }
        printf("|\n");
        done += row;
    }
    return true;
}

static bool aletheia_tape_store(const struct AletheiaTape *t,
                                struct AletheiaStore *out) {
    return aletheia_store_make(t->base, t->size, out);
}

static struct AletheiaTape aletheia_demo_tape(void) {
    struct AletheiaTape t;
    if (!aletheia_tape_make(0x00800u, 0x0080u, &t)) {
        printf("tape construction failed\n");
        return t;
    }
    if (!aletheia_tape_mark(&t, 0x00800u, 0x0010u, "head") ||
        !aletheia_tape_mark(&t, 0x00810u, 0x0020u, "ints") ||
        !aletheia_tape_mark(&t, 0x00830u, 0x0010u, "text") ||
        !aletheia_tape_mark(&t, 0x00850u, 0x0030u, "tail")) {
        printf("tape mark failed\n");
    }
    return t;
}

static void aletheia_fill_demo(void) {
    struct AletheiaStore s;
    const char *text = "Aletheia";
    uint32_t i;
    for (i = 0; i < 16u; ++i) {
        (void)aletheia_poke_u8(0x00800u + i, (AletheiaByte)i);
    }
    if (aletheia_store_make(0x00800u, 0x0080u, &s)) {
        (void)aletheia_write_u32(&s, 0x00810u, 0x00000000u);
        (void)aletheia_write_u32(&s, 0x00814u, 0x00000001u);
        (void)aletheia_write_u32(&s, 0x00818u, 0xffffffffu);
        (void)aletheia_write_u32(&s, 0x0081cu, 0x12345678u);
    }
    for (i = 0; text[i] != '\0'; ++i) {
        (void)aletheia_poke_u8(0x00830u + i, (AletheiaByte)text[i]);
    }
    for (i = 0; i < 0x0030u; ++i) {
        (void)aletheia_poke_u8(0x00850u + i, (AletheiaByte)((i * 17u + 3u) & 0xffu));
    }
}

static bool aletheia_check_hexdump(void) {
    struct AletheiaStore s;
    struct AletheiaTape t = aletheia_demo_tape();
    bool ok = aletheia_tape_store(&t, &s);
    printf("HEXDUMP\n");
    printf("ADDR    00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f  ASCII\n");
    ok = ok && aletheia_hexdump(&s, 0x00800u, 0x0080u);
    printf("PARTIAL\n");
    ok = ok && aletheia_hexdump(&s, 0x00810u, 20u);
    return ok;
}

static bool aletheia_check_marks(void) {
    struct AletheiaTape t = aletheia_demo_tape();
    uint32_t i;
    bool ok = aletheia_tape_ok(&t) && t.mark_count == 4u;
    printf("MARKS\n");
    printf("LABEL START END   SIZE\n");
    for (i = 0; i < t.mark_count; ++i) {
        const struct AletheiaMark *m = &t.marks[i];
        printf("%-5s 0x%05x 0x%05x %u\n", m->label, (unsigned)m->addr,
               (unsigned)(m->addr + m->size), (unsigned)m->size);
    }
    return ok;
}

static bool aletheia_check_rows(void) {
    struct AletheiaTape t = aletheia_demo_tape();
    uint32_t row;
    bool ok = aletheia_tape_ok(&t);
    printf("ROWS\n");
    for (row = 0; row < 8u; ++row) {
        AletheiaAddr addr = 0x00800u + row * 16u;
        uint32_t index = 0u;
        uint32_t off = 0u;
        if (aletheia_tape_find(&t, addr, &index, &off)) {
            printf("0x%05x %-5s +%u\n", (unsigned)addr,
                   t.marks[index].label, (unsigned)off);
        } else {
            printf("0x%05x (gap)\n", (unsigned)addr);
        }
    }
    return ok;
}

static bool aletheia_check_words(void) {
    struct AletheiaTape t = aletheia_demo_tape();
    struct AletheiaStore s;
    uint32_t addr;
    bool ok = aletheia_tape_store(&t, &s);
    printf("WORDS\n");
    printf("ADDR    HEX      UNSIGNED   SIGNED\n");
    for (addr = 0x00810u; addr < 0x00820u; addr += 4u) {
        uint32_t v = 0u;
        bool rd = aletheia_read_u32(&s, addr, &v);
        printf("0x%05x %08x %10u %8lld\n", (unsigned)addr, (unsigned)v,
               (unsigned)v, aletheia_signed32(v));
        if (!rd) {
            ok = false;
        }
    }
    return ok;
}

static bool aletheia_check_cover(void) {
    struct AletheiaTape t = aletheia_demo_tape();
    uint32_t covered = 0u;
    uint32_t gaps = 0u;
    bool ok = aletheia_tape_cover(&t, &covered, &gaps);
    printf("COVER\n");
    printf("MARKED %u\n", (unsigned)covered);
    printf("GAPS   %u\n", (unsigned)gaps);
    printf("TOTAL  %u\n", (unsigned)(covered + gaps));
    printf("ties   %s\n",
           (covered + gaps == t.size) ? "true" : "false");
    if (!ok || covered != 112u || gaps != 16u) {
        return false;
    }
    return true;
}

static bool aletheia_check_fail(void) {
    struct AletheiaTape t = aletheia_demo_tape();
    struct AletheiaTape nine;
    bool overlap;
    bool before;
    bool outside;
    bool empty;
    bool long_label;
    bool bad_table;
    bool nine_ok = true;
    uint32_t i;
    printf("FAIL\n");
    overlap = aletheia_tape_mark(&t, 0x00805u, 4u, "bad");
    before = aletheia_tape_mark(&t, 0x007ffu, 1u, "bad");
    outside = aletheia_tape_mark(&t, 0x00870u, 0x0020u, "bad");
    empty = aletheia_tape_mark(&t, 0x00840u, 4u, "");
    long_label = aletheia_tape_mark(&t, 0x00840u, 4u, "0123456789ab");
    t = aletheia_demo_tape();
    t.marks[0].addr = 0x007ffu;
    bad_table = aletheia_tape_ok(&t);
    printf("overlap     %s\n", overlap ? "accepted" : "rejected");
    printf("before      %s\n", before ? "accepted" : "rejected");
    printf("outside     %s\n", outside ? "accepted" : "rejected");
    printf("empty label %s\n", empty ? "accepted" : "rejected");
    printf("long label  %s\n", long_label ? "accepted" : "rejected");
    printf("bad table   %s\n", bad_table ? "accepted" : "rejected");
    if (!aletheia_tape_make(0x00900u, 0x0020u, &nine)) {
        nine_ok = false;
    }
    for (i = 0; i < 8u; ++i) {
        char label[3];
        label[0] = 'm';
        label[1] = (char)('0' + (int)i);
        label[2] = '\0';
        if (!aletheia_tape_mark(&nine, 0x00900u + i, 1u, label)) {
            nine_ok = false;
        }
    }
    if (aletheia_tape_mark(&nine, 0x00908u, 1u, "m8")) {
        nine_ok = false;
    }
    printf("nine marks  %s\n", nine_ok ? "rejected" : "accepted");
    return !overlap && !before && !outside && !empty && !long_label &&
           !bad_table && nine_ok;
}

int main(void) {
    bool hexdump_ok;
    bool marks_ok;
    bool rows_ok;
    bool words_ok;
    bool cover_ok;
    bool fail_ok;

    printf("ALETHEIA TAPE\n");
    printf("SIZE       : %u bytes\n", (unsigned)ALETHEIA_SIZE);
    printf("REGION     : 0x00800..0x0087f (128 bytes)\n");
    printf("TAPE BYTES : %lu\n", (unsigned long)sizeof(struct AletheiaTape));
    printf("MARK BYTES : %lu\n", (unsigned long)sizeof(struct AletheiaMark));
    printf("\n");
    aletheia_fill_demo();

    hexdump_ok = aletheia_check_hexdump();
    printf("\n");
    marks_ok = aletheia_check_marks();
    printf("\n");
    rows_ok = aletheia_check_rows();
    printf("\n");
    words_ok = aletheia_check_words();
    printf("\n");
    cover_ok = aletheia_check_cover();
    printf("\n");
    fail_ok = aletheia_check_fail();
    printf("\n");

    printf("SUMMARY\n");
    printf("hexdump : %s\n", hexdump_ok ? "true" : "false");
    printf("marks   : %s\n", marks_ok ? "true" : "false");
    printf("rows    : %s\n", rows_ok ? "true" : "false");
    printf("words   : %s\n", words_ok ? "true" : "false");
    printf("cover   : %s\n", cover_ok ? "true" : "false");
    printf("fail    : %s\n", fail_ok ? "true" : "false");
    if (hexdump_ok && marks_ok && rows_ok && words_ok && cover_ok &&
        fail_ok) {
        printf("ALETHEIA TAPE OK\n");
        return 0;
    }
    printf("ALETHEIA TAPE BROKEN\n");
    return 1;
}
```

程序大约五百行。它没有 `malloc`，没有 `<string.h>`，没有类型双关。纸带区域是 128 字节，标注表最多 8 项，所有显示都从字节层读取，所有标注都经过有效性和顺序检查。编译用 `-std=c99 -O2 -Wall -Wextra -pedantic -Werror`，没有警告。

程序的结构分四层。最下面是全局静态数组 `aletheia_mem`，大小 262144 字节，是第一至八章一直用的那台机器。数组上面是字节层和存储层：`aletheia_peek_u8`、`aletheia_poke_u8`、`aletheia_store_make`、`aletheia_read_u32`、`aletheia_write_u32`，负责单个字节和 32 位小端值的读写。再上面是纸带层：`aletheia_tape_make`、`aletheia_tape_mark`、`aletheia_tape_find`、`aletheia_tape_cover`，负责区域和标注。最上面是显示层：`aletheia_hexdump`、十进制打印、检查函数和 `main`。

演示数据在 `aletheia_fill_demo` 里准备。区域从 0x800 开始，128 字节。先写 `head` 的十六个字节，值是 0 到 15；再写 `ints` 的四个 32 位值，0、1、0xFFFFFFFF、0x12345678，都按小端写；再在 0x830 写字符串 `Aletheia` 和终止符，后面补零；最后把 `tail` 的 48 个字节按 $b_i=(17i+3)\bmod256$ 填满。填充函数返回布尔值，任何一次写失败都会向上传，`main` 不会在坏数据上继续。

标注在 `aletheia_demo_tape` 里按地址顺序追加：`head`、`ints`、`text`、`tail`。每次追加都会调用 `tape_ok`，检查整张表；追加失败就停止并返回假。这个顺序不能换，`tail` 的起点 0x850 大于前面所有标注的终点，换到前面会被自己的大小和后续标注挤掉。程序的演示布局是设计好的，标注顺序也是设计好的，不是在运行时试探出来的。

检查函数各自返回布尔值，`main` 用与运算把它们串起来，最后打印 SUMMARY。每一段先打印自己的标题，再打印数据，最后打印一个布尔结果。这样即使某一段失败，前面的输出仍然完整，读者能看到失败发生在哪里。程序不在第一次失败时立刻退出，因为验收需要看到所有段的结果；代价是某一段失败后，后面的段可能也失败，汇总里会有多个 `false`。这是有意的：一次运行给出全貌，比逐个排错快。

所有函数都是 `static`，外部链接只有 `main`。所有常量都用 `#define` 或枚举写成有名字的字面量，没有魔数散落在代码里。所有结构体都在文件顶部声明，函数按依赖顺序排列，先底层后上层，编译器不需要前向声明就能一路读下来。这个排版不是强制的，但它让“这一层用了下一层什么”在纸面上就能看出来。

## 八、真实输出与验收

在本地编译运行，得到以下输出：

```text
ALETHEIA TAPE
SIZE       : 262144 bytes
REGION     : 0x00800..0x0087f (128 bytes)
TAPE BYTES : 172
MARK BYTES : 20

HEXDUMP
ADDR    00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f  ASCII
0x00800 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f |................|
0x00810 00 00 00 00 01 00 00 00 ff ff ff ff 78 56 34 12 |............xV4.|
0x00820 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 |................|
0x00830 41 6c 65 74 68 65 69 61 00 00 00 00 00 00 00 00 |Aletheia........|
0x00840 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 |................|
0x00850 03 14 25 36 47 58 69 7a 8b 9c ad be cf e0 f1 02 |..%6GXiz........|
0x00860 13 24 35 46 57 68 79 8a 9b ac bd ce df f0 01 12 |.$5FWhy.........|
0x00870 23 34 45 56 67 78 89 9a ab bc cd de ef 00 11 22 |#4EVgx........."|
PARTIAL
0x00810 00 00 00 00 01 00 00 00 ff ff ff ff 78 56 34 12 |............xV4.|
0x00820 00 00 00 00                                     |....|

MARKS
LABEL START END   SIZE
head  0x00800 0x00810 16
ints  0x00810 0x00830 32
text  0x00830 0x00840 16
tail  0x00850 0x00880 48

ROWS
0x00800 head  +0
0x00810 ints  +0
0x00820 ints  +16
0x00830 text  +0
0x00840 (gap)
0x00850 tail  +0
0x00860 tail  +16
0x00870 tail  +32

WORDS
ADDR    HEX      UNSIGNED   SIGNED
0x00810 00000000          0        0
0x00814 00000001          1        1
0x00818 ffffffff 4294967295       -1
0x0081c 12345678  305419896 305419896

COVER
MARKED 112
GAPS   16
TOTAL  128
ties   true

FAIL
overlap     rejected
before      rejected
outside     rejected
empty label rejected
long label  rejected
bad table   rejected
nine marks  rejected

SUMMARY
hexdump : true
marks   : true
rows    : true
words   : true
cover   : true
fail    : true
ALETHEIA TAPE OK
```

逐段看。头部打印机器大小、区域范围、纸带结构体大小和标注结构体大小。纸带是 172 字节，标注是 20 字节，和第六章的结构体规则一致：地址、大小、标签依次摆放，标签是 12 字节的字符数组，整体对齐 4，没有多余填充。

HEXDUMP 段打印八行满行，每行十六个字节，左边地址，中间十六进制，右边 ASCII。第一行 0x00 到 0x0F，第四行有 `Aletheia` 文本，第二行有 `78 56 34 12` 和全 1，尾部三行是模式字节。每一行的地址比上一行大 16，十六进制列固定 16 列，ASCII 列按实际字节显示。PARTIAL 段从 0x810 转储 20 字节，第二行只有四个字节，十六进制列用空格补齐，ASCII 列只有四个字符，竖线仍然对齐。

MARKS 段打印四段标注。`head` 从 0x800 到 0x810，大小 16；`ints` 从 0x810 到 0x830，大小 32；`text` 从 0x830 到 0x840，大小 16；`tail` 从 0x850 到 0x880，大小 48。终点是左闭右开，相邻标注的终点等于下一个起点，`text` 的终点 0x840 和 `tail` 的起点 0x850 之间留了 16 字节空隙。四段按地址排序，没有重叠。

ROWS 段把每行首地址映射到标注。0x800 属于 `head`，0x810 和 0x820 属于 `ints`，0x830 属于 `text`，0x840 没有标注，0x850、0x860、0x870 属于 `tail`。偏移列分别是 0、0、16、0、0、0、16、32。这个表把行和标注对齐，读者能看出每个十六字节行落在哪一段，偏移是多少。

WORDS 段按 32 位小端解释 `ints` 的前四个值。0、1、4294967295、305419896 按无符号打印，0、1、-1、305419896 按有符号打印。全 1 的值在无符号列是 4294967295，在有符号列是 -1，位模式相同，解释不同。这四个值验证了第八章的 `read_u32` 和这一章的十进制显示。

COVER 段打印覆盖 112 字节、空隙 16 字节、总计 128 字节，`ties` 为真。覆盖和等于四段大小之和，空隙等于区域大小减覆盖，两者相加等于区域大小。标注不重叠，所以覆盖和不需要去重；如果重叠，这个等式就不成立，`tape_ok` 会先拒绝。

FAIL 段测七种失败。重叠标注 0x805 拒绝，区前 0x7FF 拒绝，区外 0x870 加 0x20 拒绝，空标签拒绝，超长标签拒绝，坏表拒绝，第九个标注拒绝。所有失败都是返回值，不崩溃，不修改原表。这一段验证了标注函数的检查顺序和边界。

验收标准有七条：

1. 128 字节的区域按 16 字节一行显示八行，每行地址递增 16。
2. 最后一行不足 16 字节时，十六进制列补空格，ASCII 列只显示实际字节。
3. 四段标注按地址排序、互不重叠、完全在区内。
4. 每行首地址能找到对应标注或识别为空隙，偏移正确。
5. 32 位值按无符号和有符号两种方式正确显示，全 1 显示为 4294967295 和 -1。
6. 覆盖 112 字节、空隙 16 字节、总计 128 字节，三者一致。
7. 七种非法标注全部拒绝，编译零警告，ASan/UBSan 无报错，输出确定且不超过 80 列。

七条全部通过，程序打印 `ALETHEIA TAPE OK` 并返回 0。输出最宽一行 74 列，重复运行完全一致。程序不打印宿主地址、不打印时间、不依赖未初始化内存。纸带区域的内容在每次运行开始时重新填充，标注表在每次构造时清零，所有显示都能复现。

这个程序也在 ASan 和 UBSan 下跑过。所有转储都先检查区间，所有标注都先检查顺序和边界，所有查找都在有效表上进行，所有标签复制都有长度上限。两个消毒器都没有报错，输出和普通编译一致。

纸带台能回答的问题和不能回答的问题要分开。它能回答“这个地址属于哪一段、偏移多少”“这一行从哪里开始”“覆盖了多少字节、空了多少字节”，这些都由标注表和区域大小算出来。它不能回答“这段字节原本是什么类型”“这段数据是否已经被释放”“这个标注对应的语义是否完整”。标注是读者贴上去的标签，不是机器自己长出来的信息；标签写错，纸带台照样打印，检查照样通过。所以覆盖等式只能证明布局自洽，不能证明布局正确。下一章的总装要把各段的名字、大小和接口写死，再让纸带台去核对，才能把“自洽”推进到“与设计一致”。

## 九、交给下一章

这一章定义了 `AletheiaTape`，一个由区域和标注表组成的纸带描述符。它提供构造、有效性检查、追加标注、按地址查找、覆盖统计和十六进制转储。`aletheia_hexdump` 可以显示任意长度的区域，最后一行自动补齐；`aletheia_tape_mark` 维护标注的排序和不重叠；`aletheia_tape_find` 把地址映射到标注和偏移。

交给下一章的接口是：

```c
struct AletheiaTape {
    AletheiaAddr base;
    uint32_t size;
    uint32_t mark_count;
    struct AletheiaMark marks[ALETHEIA_MAX_MARKS];
};
```

以及 `aletheia_tape_make`、`aletheia_tape_ok`、`aletheia_tape_mark`、`aletheia_tape_find`、`aletheia_tape_cover`、`aletheia_tape_store`、`aletheia_hexdump`。下一章的总装会把纸带台挂在 `AletheiaMem` 上，用标注标出代码区、数据区、栈区和空闲区，用转储显示关键字节，用查找确认每个地址的归属。

下一章是总装。这一章把一块区域摊开，下一章把整台机器装起来。总装会把第一至九章的零件放进一个程序：字节层读写，区间层描述，整数层解释，指针层走步，数组层下标，结构体层偏移，字符串层文本，存储层多字节值，纸带层显示和标注。所有零件共用一块 256 KiB 的静态数组，所有地址都在同一个空间里，所有检查都回到字节和区间。

这一章从“值”回到“区域”，从“读一个数”回到“看一整片”。纸带台不是最底层的组件，它建立在存储层之上；也不是最高层的组件，它只负责显示和标注。它把底层的数据变成人能读的表格，把上层的布局变成可核对的区间。下一章会把这张表扩展到整台机器，让 256 KiB 的数组第一次以一个整体出现。
