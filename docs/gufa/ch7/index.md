# 字符串

> 第七章。零件：`AletheiaStr`。字符串不是一串字符，是一串字节加一个停止符号。

## 一、回访：结构体留下的偏移

第六章把结构体写成一张带空洞的偏移表。字段有大小、有对齐、有偏移，访问时按偏移算地址，不再按名字猜。数组用乘法，结构体用查表，两种布局合起来，能描述大多数复合数据。可还有一种数据，既不像数组那样等距，也不像结构体那样字段固定，它就是字符串。

字符串是一串字节，长度不写在开头，而是靠一个特殊的终止字节来标记。这个字节是 0，写作 `NUL`。读到 0 就知道字符串结束了，后面的字节不属于这个字符串。这个约定看起来简单，却带来两个新问题：长度要扫描才能知道，容量必须单独记住。数组的长度是字段，结构体的字段数是字段，字符串的长度是“第一个 0 的位置”，是算出来的。

上一章的偏移表在这里还能用。一个字符串描述符可以只有两个字段：起始地址和容量。起始地址是 4 字节，容量是 4 字节，结构体大小 8 字节，没有空洞。长度不是字段，因为它是扫描结果，不是存储状态。容量是字段，因为它必须由调用者提供，扫描不能越过它。`AletheiaStr` 就是这两个字段。

字符串的字节和数组的字节是同一块内存。第 $i$ 个字节的地址是 $a+i$，元素大小是 1，这就是第五章的字节数组。字符串层在字节数组上加了两个约定：遇到 0 停止，扫描不超过容量。数组层保证每个下标在范围内，字符串层保证扫描不越界。两层各管一件事，底下的读写还是字节层和指针层。

这里要区分“存储”和“解释”。内存里只有字节，没有字符，也没有字符串。同一串字节 `e5 a4 a7 e5 8a 9b e7 8e a9`，按 UTF-8 解释是三个汉字，按 GBK 或其他编码解释可能是别的字，按整数解释是几个很大的数。字符串层选择了 UTF-8 和 NUL 终止这两个约定，字节本身的含义由约定赋予。换了约定，同一块内存就是另一种数据。书里每一章都在加约定，字节层加地址，指针层加元素大小，数组层加等距，结构体层加字段偏移，字符串层加终止符。约定越多，能表达的东西越具体，可底下的字节始终没变。

这一章还要处理一个数组和结构体都没碰过的问题：字符和字节不是一回事。一个英文字母占一个字节，一个汉字在 UTF-8 里占三个字节。字符串的“长度”可以指字节数，也可以指字符数，两个数不一定相等。程序里两种长度都要算，都要打印，不能混为一谈。

先看一个最小实验。把 `hello` 写进内存，后面补一个 0。再写 `大力玩`，后面也补一个 0。前者五个字节，后者九个字节；前者五个字符，后者三个字符。两个字符串的字节数不同，字符数也不同，可它们的终止符都只有一个字节。这个实验会引出终止符、容量、扫描、UTF-8 和反转五个话题。

## 二、开场实验：长度藏在哪里

把 `hello` 写到 0x00500，逐字节看：

```text
addr    byte  char
0x00500 0x68  h
0x00501 0x65  e
0x00502 0x6c  l
0x00503 0x6c  l
0x00504 0x6f  o
0x00505 0x00  NUL
```

前五个字节是可打印字符，第六个字节是 0。长度是 5，终止符在 0x00505。终止符本身不算内容，它只是“到此为止”的标记。容量至少要 6，才能同时放下五个字符和一个终止符。如果容量只有 5，五个字符刚好填满，没有地方放 0，这个字符串就没有终止符，`aletheia_strlen` 会拒绝。

再写 `大力玩`：

```text
addr    bytes          char
0x00520 e5 a4 a7       大
0x00523 e5 8a 9b       力
0x00526 e7 8e a9       玩
0x00529 00             NUL
```

三个汉字，每个占三个字节，一共九个字节。字符数是 3，字节数是 9。终止符在 0x00529。如果你按字节数去分配一个“能装三个字符”的缓冲区，只分配三个字节，第二个汉字就会写不下。按字符数分配，必须知道每个字符的编码长度；按字节数分配，容量才和内存直接对应。字符串的容量永远按字节算，字符数是另外算出来的。

再写 `A中B`：

```text
addr    bytes          char
0x00540 41             A
0x00541 e4 b8 ad       中
0x00544 42             B
0x00545 00             NUL
```

字节数是 5，字符数是 3。第一个字符一个字节，第二个三个字节，第三个一个字节。字节长度的公式是每个字符编码长度的和，字符数是字符的个数。两个数都对，只是回答的问题不同。

空字符串只包含一个终止符：

```text
addr    byte
0x00560 0x00
```

长度是 0，字符数是 0，容量至少 1。空字符串不是“没有字符串”，它是一个长度为 0 的字符串，第一个字节就是终止符。扫描时第一次读到 0，立刻停止，返回长度 0。这个边界情况很容易被忘记，程序里的 LENGTH 表专门列了一行空字符串。

开场实验的结论是：字符串的长度不在字节里，在终止符的位置里；字符串的容量必须由调用者给出，不能从内容推出来；字符数和字节数是两个不同的量，UTF-8 让它们分开。下面先把终止符和容量说清楚，再说 UTF-8。

## 三、NUL 终止与容量

### 3.1 终止符

字符串是一串字节 $b_0,b_1,\dots,b_{n-1}$，后面跟一个终止字节 $b_n=0$。长度定义为第一个 0 的下标：

$$
\operatorname{len}(s)=\min\{i\mid b_i=0\}
$$

如果容量范围内没有 0，长度就没有定义，函数返回失败。这个定义只依赖字节内容，不依赖任何额外的长度字段。你拿到一个起始地址，从那里开始读，读到 0 就知道停了。字符串可以嵌在更大的内存块里，终止符之前的字节属于它，之后的字节属于别人。

为什么用 0 做终止符？因为 0 不是可打印字符，在文本里很少出现；C 语言历史上的字符串就是用 0 终止的；字节层的默认值也是 0，未初始化的内存看起来像空字符串。代价是字符串不能包含 0 字节。如果你要存二进制数据，里面可能有 0，就不能用 NUL 终止，得用“地址加长度”的表示。这一章的字符串只处理文本，文本里没有 0，所以可以用终止符。

终止符还有一个好处：字符串可以从中间切开。给定一个起始地址，不需要知道总长度，只要一直读到 0，就是这一段的结尾。多个字符串可以首尾相接放在一块内存里，每个都有自己的终止符，函数只拿到当前字符串的起点，就能读完当前这一段，不会读到下一段。代价是每次读都要扫描，不能直接跳到末尾；如果字符串很长，扫描的成本就不可忽略。另一种表示是“长度前缀”，在内容前面存一个长度字段，读长度就知道内容有多长，不用扫描。长度前缀适合频繁求长度的场景，NUL 终止适合频繁拼接和切分的场景。这一章选 NUL，因为它是 C 的传统，也因为后面的机器要用字符电传输出，逐字节读到 0 正好对应“打印到结尾”。

终止符是内容的一部分，不是容量的替代品。只有终止符没有容量，扫描可能越过内存边界去找一个不存在的 0；只有容量没有终止符，扫描知道停，可不知道内容在哪里结束。两个一起用，容量给出硬边界，终止符给出软边界。`aletheia_strlen` 先检查容量在内存里，再在容量内找终止符。两个条件都满足，返回长度；任何一个不满足，返回失败。失败不是异常，是函数的正常返回值，调用者必须检查。

终止符只占一个字节，不占字符数。`len(s)` 返回的是终止符的下标，也就是内容字节数。终止符的地址是 $a+\operatorname{len}(s)$。容量必须大于长度，至少是长度加一：

$$
\operatorname{len}(s)+1\le \operatorname{capacity}(s)
$$

这个不等式是字符串有效性的核心。长度等于容量时，所有字节都是内容，没有位置放终止符，字符串不完整。长度小于容量时，至少有一个字节可以放终止符。程序里的 SCAN 表用容量 6 和容量 5 测同一个 `hello`：容量 6 通过，容量 5 拒绝。五个字符加一个终止符正好六个字节，少一个都不行。

### 3.2 容量与长度

容量是“这块区域最多能放多少个字节”，长度是“实际内容有多少个字节”。容量是调用者给的，长度是扫描出来的。容量不变，长度可以变：写入更长的字符串，长度增加；写入更短的字符串，长度减少；清空字符串，长度变成 0。容量是上限，长度是当前值。

`AletheiaStr` 只存起始地址和容量，不存长度。为什么不再存一个长度字段？因为长度可以从内容算出来，存了就要维护一致性：每次写入、修改、清空都要更新长度，忘一次就出错。不存长度，只有一个真相，就是内存里的字节。代价是每次求长度都要扫描，复杂度是 $O(n)$。对于短字符串，扫描很快；对于长字符串，可以缓存长度，但那是优化，不是这一章的基础表示。

容量必须覆盖终止符。`aletheia_str_make` 检查容量大于 0，检查起始地址加容量不超过 262144。它不检查内容里有没有终止符，因为构造时内容可能还没写。`aletheia_strlen` 才检查终止符，扫描到容量末尾还没有 0 就返回失败。构造和求长度分开，各自检查各自的条件。

容量也不能太小。写入函数 `aletheia_str_put` 先算源文本的字节数 $n$，如果 $n\ge \operatorname{capacity}$，就拒绝，因为放不下终止符。注意是比较 $n$ 和容量，不是比较字符数。`大力玩` 三个字符，字节数是 9，容量至少 10。按字符数算容量会少算六个字节，写进去就溢出。

这里有一个常见的容量错误。有人看到字符串有 3 个字符，就分配 3 个字节，写入 9 个字节的 UTF-8 内容，后 6 个字节覆盖了后面的变量。有人记得加终止符，分配 4 个字节，结果还是不够，因为每个汉字占 3 个字节，不是 1 个字节。正确的算法是“字节数加一”：先按 UTF-8 算出内容的字节数 $n$，再分配 $n+1$ 个字节。容量是字节的容量，不是字符的容量。这个区别在纯 ASCII 里看不出来，一遇到中文就暴露。

还有一类错误是把容量当成长度。容量是上限，长度是当前值。一个容量 16 的字符串可以装 0 到 15 个字节的内容，长度随写入变化。程序里用同一个容量 16 测四个字符串，`hello` 的长度 5，`大力玩` 的长度 9，`A中B` 的长度 5，空字符串的长度 0。容量没变，长度在变。如果把容量当成长度打印，四行都会显示 16，和实际内容对不上。

容量还是边界检查的依据。`aletheia_str_byte` 和 `aletheia_str_poke` 都检查下标小于容量；`aletheia_strlen` 的循环上界是容量；`aletheia_utf8_next` 的剩余字节数从长度算起，长度又受容量约束。整个字符串层的所有访问都能回溯到容量这一个数。容量错了，所有检查都跟着错；容量对了，单个函数的检查可以局部验证。这就是为什么构造时要把容量定下来，后面不再改。

### 3.3 扫描算法

求长度的算法很直接：

```text
i = 0
while i < capacity:
    b = read(addr + i)
    if b == 0:
        return i
    i = i + 1
return fail
```

从下标 0 开始，每次读一个字节，遇到 0 返回当前下标，读满容量还没遇到 0 就失败。循环次数最多是容量，最坏情况 $O(\text{capacity})$，最好情况是第一个字节就是 0，$O(1)$。没有提前知道长度的办法，除非在别处缓存。

这个算法只读，不写，不改内存。它可以在任意时刻调用，不会破坏字符串。它读的每个地址都在 $[a,a+\text{capacity})$ 内，容量检查保证这个区间在内存里。它不会读到容量之外，哪怕内存后面还有别的数据。终止符在容量内，扫描就安全；终止符不在容量内，扫描就失败，不会越界去找。

用指针层写，可以从起始地址造一个元素大小为 1 的指针，然后走 $i$ 步：

```c
struct AletheiaPtr base;
aletheia_ptr_make(s->addr, 1u, &base);
for (i = 0; i < s->capacity; ++i) {
    struct AletheiaPtr p;
    aletheia_ptr_walk(base, (int32_t)i, &p);
    aletheia_ptr_read_u8(p, &b);
}
```

每一步都检查指针是否在内存里，每读一个字节都检查指针是否有效。这些检查在容量范围内是冗余的，可它们让字符串层不依赖“容量检查已经做过”这个前提。两层各自检查，错误不会互相掩盖。

### 3.4 没有终止符会怎样

如果容量范围内没有 0，`aletheia_strlen` 返回 `false`。调用者不能把返回值当成 0，也不能继续读。程序里的 SCAN 表第二行打印 `rejected`，长度列打印 0，这个 0 只是占位，不是真实长度。真实的答案是“不知道”，因为没有终止符就没有长度。

没有终止符的字符串很危险。如果程序不检查容量，一直往后读，就会读到别的变量、别的结构体、甚至内存外面。C 的 `strlen` 就是这样：它假定字符串一定有终止符，没有就继续读，直到碰巧遇到 0 或者崩溃。这一章的 `aletheia_strlen` 不假定，它把容量作为硬边界，读满就停，返回失败。失败比崩溃好，失败比读到别人的数据好。

`aletheia_str_print` 遇到没有终止符的字符串，会打印容量内的所有字节，再打印 `(unterminated)`。它不会一直读到内存末尾，也不会假装字符串正常。打印是诊断工具，失败要显式标出来，不能悄悄截断。程序里的 UTF8 表最后一行 `61 62 63` 就是三个字节、没有终止符，容量正好 3，扫描失败，UTF-8 计数和反转都拒绝。

这个设计也说明容量不是可选的。只给起始地址，字符串层不知道到哪里停；只给容量不给终止符，字符串层知道停但不知道内容多长。两个都要：容量是安全边界，终止符是内容边界。安全边界可以大于内容边界，不能小于。

## 四、UTF-8 与两种长度

### 4.1 字节不是字符

ASCII 里，一个字节就是一个字符：`A` 是 0x41，`B` 是 0x42，`0` 是 0x30。中文不在 ASCII 里。UTF-8 用多个字节表示一个 Unicode 码点，常用的汉字占三个字节，emoji 占四个字节。`大力玩` 三个字符，九个字节；`hello` 五个字符，五个字节。字节数和字符数只有在纯 ASCII 字符串里才相等。

字符本身也有歧义。一个汉字是一个码点，一个带声调的字母可能是一个码点，也可能是一个基字母加一个组合符号。多个码点可以组成一个“字形簇”，人看起来是一个字符，机器数出来是几个。这一章数的是 Unicode 码点，不是字形簇。`aletheia_utf8_count` 返回码点个数，不处理组合符号和 emoji 序列。这个精度对书名、标签、普通文本够用，对复杂的文本排版不够，后面需要时再扩展。

字节长度是内存里的字节数，字符数是码点数。两个数都重要：分配缓冲区按字节，显示宽度按字符（更准确地说按字形簇），截断文本要按字符边界，不能从多字节字符中间切开。字符串层提供两个函数，调用者按需要选，不能混用。

为什么不用“一个字符一个字节”的编码，省掉这些麻烦？因为世界的字符不止 256 个。汉字有几万个，加上日文、韩文、阿拉伯文、各种符号和 emoji，码点总数超过十万。一个字节只有 256 种取值，装不下。UTF-16 用两个字节装大部分字符，可也有代理对，而且和 ASCII 不兼容；UTF-32 每个码点四个字节，简单但浪费，英文文本会膨胀四倍。UTF-8 是折中：ASCII 保持一个字节，其他字符用两到四个字节，和旧文本兼容，又覆盖全部 Unicode。代价是变长，字符数和字节数分开，扫描和截断都要小心。

UTF-8 还有一个好处：字节顺序无关。多字节整数有大端小端的问题，UTF-8 的字节顺序是编码规则定死的，从哪个方向读都是同一串字节。字符串可以在网络上传输，可以存进文件，不需要关心发送方和接收方的字节序。这个性质在下一章讲整数时会形成对照：字符串的字节顺序由编码决定，整数的字节顺序由机器决定。

字符数也不是“人眼看到的字数”。`你好` 是两个码点，也是两个字；带声调的 `é` 可能是一个码点，也可能是 `e` 加一个组合重音，两个码点；家庭 emoji 由多个码点用零宽连接符拼成，人看是一个，码点数出来是四五个。这一章的 `aletheia_utf8_count` 只数码点，不处理组合和连接。对书名、章节标题、普通中文文本，码点数就是字数；对复杂排版，需要更高级的库。书里明确这个精度，不假装它能处理所有文本。

### 4.2 UTF-8 的编码规则

UTF-8 用首字节的高位标记这个码点占几个字节。规则可以写成：

$$
\begin{aligned}
0\text{xxxxxxx} &\quad 1\text{ 字节},\\
110\text{xxxxx}\ 10\text{xxxxxx} &\quad 2\text{ 字节},\\
1110\text{xxxx}\ 10\text{xxxxxx}\ 10\text{xxxxxx} &\quad 3\text{ 字节},\\
11110\text{xxx}\ 10\text{xxxxxx}\ 10\text{xxxxxx}\ 10\text{xxxxxx} &\quad 4\text{ 字节}.
\end{aligned}
$$

`x` 是有效载荷位，`10` 开头的字节叫续字节。首字节决定长度，续字节必须以 `10` 开头。一个合法的 UTF-8 序列，首字节之后跟着正确数量的续字节，续字节的高两位都是 `10`。没有续字节的单字节字符，首字节最高位是 0。

这些规则还排除了几种非法序列。`11000000 10000000` 是两字节编码的 0，属于“过长编码”，同一个码点有更短的合法编码，UTF-8 不允许。`11101101 10100000 10000000` 编码的是代理区码点，UTF-8 不允许。`11110100 10010000 ...` 超过 Unicode 的最大码点 U+10FFFF，也不允许。严格的解析器要检查这些边界，不能只看续字节。

这一章的 `aletheia_utf8_next` 做严格检查。两字节首字节限制在 0xC2 到 0xDF，排除 0xC0 和 0xC1 的过长编码。三字节里，0xE0 的第二个字节必须不小于 0xA0，排除过长编码；0xED 的第二个字节必须不大于 0x9F，排除代理区。四字节里，0xF0 的第二个字节必须不小于 0x90，0xF4 的第二个字节必须不大于 0x8F，排除过长编码和超出 U+10FFFF 的码点。其余续字节统一检查高两位是 `10`。这些条件加起来，能拒绝大部分非法序列。

### 4.3 码点计数

给定一个已经终止的字符串，码点数等于“首字节的个数”。每个码点从一个首字节开始，后面跟零到三个续字节。续字节的高两位是 `10`，首字节不是。所以只要扫描字节，遇到首字节就计数加一，遇到续字节就跳过，最后得到码点数。

更准确地说，用 `aletheia_utf8_next` 每次解析一个码点，返回它的字节长度，然后跳过这么多字节，计数加一。这样既数了码点，又验证了序列合法。如果某个位置解析失败，整个字符串的码点数就没有定义，函数返回失败，不返回部分计数。

字节长度和字符数的关系是：

$$
\operatorname{bytes}(s)=\sum_{k=1}^{\operatorname{chars}(s)}\operatorname{width}(c_k)
$$

其中 $\operatorname{width}(c_k)$ 是第 $k$ 个码点的 UTF-8 字节数，取 1、2、3 或 4。字符数总是小于等于字节数，等号只在纯 ASCII 时成立。`大力玩` 的字节数是 $3+3+3=9$，字符数是 3；`A中B` 的字节数是 $1+3+1=5$，字符数是 3；空字符串两者都是 0。

程序里的 LENGTH 表同时打印字节数、字符数和终止符地址。终止符地址是 $a+\text{bytes}$，不是 $a+\text{chars}$。如果按字符数算终止符地址，`大力玩` 会算到 0x00523，那是第二个汉字的第一个字节，不是终止符。字节数和地址是一一对应的，字符数是另一个维度。

### 4.4 非法序列的四种情况

UTF8 表列了四种失败：

`E4 41 00`：首字节 0xE4 表示三字节字符，第二个字节应该是续字节，可 0x41 是 ASCII 的 `A`，高两位不是 `10`，序列非法。

`C0 80 00`：首字节 0xC0 是两字节编码的过长形式，合法范围从 0xC2 开始，0xC0 直接拒绝。

`F0 9F 00`：首字节 0xF0 表示四字节字符，后面只跟了一个续字节 0x9F，第三个字节就是终止符 0，长度不够，序列被截断。

`61 62 63`：三个 ASCII 字节 `abc`，没有终止符，容量正好 3。字节序列本身是合法的 UTF-8，可它不是合法的字符串，因为扫描不到 0。`aletheia_strlen` 先失败，后面的 UTF-8 计数和反转都不会执行。

四种情况分别对应“续字节错”“过长编码”“截断”“无终止符”。前三种是 UTF-8 层面的非法，第四种是字符串层面的非法。两层检查都要有：没有终止符，UTF-8 解析就不知道到哪里停；UTF-8 非法，字符数就没有定义。程序里先求长度，再解析 UTF-8，顺序不能反。

## 五、原地反转

### 5.1 先试字节反转

反转字符串最直接的办法是把首尾字节对调，向中间走：

```text
i = 0, j = n - 1
while i < j:
    swap(b[i], b[j])
    i = i + 1
    j = j - 1
```

对 ASCII 字符串，这个算法完全正确。`abcdef` 变成 `fedcba`，长度不变，字符数不变。对 UTF-8 字符串，这个算法会把多字节字符的字节顺序也反过来。`A中B` 的字节是 `41 e4 b8 ad 42`，字节反转后是 `42 ad b8 e4 41`。第一个字节 `B` 没问题，可后面的 `ad b8 e4` 是一个被反过来的三字节字符，不再是一个合法的 UTF-8 序列。打印出来是乱码，解析器会拒绝。

所以字符串反转不能只反字节。要么按字符反转，把每个多字节字符当成一个整体；要么先反字节，再把每个字符内部的字节反回来。第二种办法可以在原地做，不需要额外的缓冲区，这一章选它。

### 5.2 两阶段反转

设字符串的码点是 $c_1,c_2,\dots,c_k$，每个码点有若干个字节。第一阶段把整个字节序列反转：

$$
b_0b_1\cdots b_{n-1}\ \longrightarrow\ b_{n-1}\cdots b_1b_0
$$

反转后，码点的顺序反了，每个码点内部的字节顺序也反了。原来最后一个是 $c_k$，现在它的字节出现在最前面，但是倒着的；原来第一个是 $c_1$，现在它的字节出现在最后面，也是倒着的。整个序列可以写成：

$$
\operatorname{rev}(c_k)\operatorname{rev}(c_{k-1})\cdots\operatorname{rev}(c_1)
$$

其中 $\operatorname{rev}(c)$ 表示把码点 $c$ 的字节顺序反过来。第二阶段从前往后扫描，找到每个码点的字节组，把组内字节再反转一次。$\operatorname{rev}(\operatorname{rev}(c))=c$，组内恢复原样，组的顺序仍然是反的，于是得到：

$$
c_kc_{k-1}\cdots c_1
$$

这正是按字符反转的结果。两个阶段都是原地交换，额外空间是常数。

用 `A中B` 走一遍。原字节是 `41 e4 b8 ad 42`，$n=5$。第一阶段交换 0 和 4，得到 `42 e4 b8 ad 41`；再交换 1 和 3，得到 `42 ad b8 e4 41`；下标 2 在中间，不动。这串字节里，`42` 是 ASCII 的 `B`，`ad b8 e4` 是倒着的 `中`，`41` 是 ASCII 的 `A`。第二阶段从 0 开始，第 0 个字节是首字节，组是 `[0,0]`，组内不用交换，下一组从 1 开始。位置 1 是 `ad`，续字节，前进到 2 的 `b8`，还是续字节，前进到 3 的 `e4`，首字节，组是 `[1,3]`。交换 1 和 3，得到 `42 e4 b8 ad 41`；位置 1 和 3 向中间走，2 是中间，结束。下一组从 4 开始，`41` 是首字节，组是 `[4,4]`。最终字节是 `42 e4 b8 ad 41`，按 UTF-8 读是 `B中A`。

再走一遍 `你好世界`。原字节是 `e4 bd a0 e5 a5 bd e4 b8 96 e7 95 8c`，$n=12$。第一阶段把 0 和 11 交换，1 和 10 交换，2 和 9 交换，3 和 8 交换，4 和 7 交换，5 和 6 交换，得到 `8c 95 e7 96 b8 e4 bd a5 e5 a0 bd e4`。这串字节里，每个码点的字节都倒了，码点的顺序也倒了。第二阶段从 0 开始，`8c` 是续字节，前进到 `95`，还是续字节，前进到 `e7`，首字节，组是 `[0,2]`，组内交换得到 `e7 95 8c`，这是 `界`。下一组从 3 开始，`96` 续，`b8` 续，`e4` 首字节，组是 `[3,5]`，交换得到 `e4 b8 96`，这是 `世`。下一组 `[6,8]` 得到 `e5 a5 bd`，这是 `好`。最后一组 `[9,11]` 得到 `e4 bd a0`，这是 `你`。最终字节是 `e7 95 8c e4 b8 96 e5 a5 bd e4 bd a0`，读作 `界世好你`。字节数 12 没变，字符数 4 没变，顺序反了。

这个推演说明第二阶段为什么从组尾往组首找。反转后的字节组是“续字节在前，首字节在后”，首字节在组的末尾，不是开头。扫描时不能从首字节开始找组，因为首字节在当前位置的后面；要从当前位置往后走，跳过续字节，直到首字节，才能确定组的右端。找到右端后，左端就是起点，组内反转把字节顺序恢复。如果按“首字节开头、续字节跟随”的正向规则去找，就会把组边界找错，反转出来还是乱码。反转后的字节序列里，每个码点的字节组以续字节开头、以首字节结尾。比如 `A中B` 反转后是 `42 ad b8 e4 41`：`42` 是 ASCII 首字节，自己一组；`ad b8 e4` 是两个续字节加一个首字节，是一组；`41` 是 ASCII，自己一组。扫描时从当前位置开始，连续跳过续字节，直到遇到首字节，这个首字节就是组的末尾。把从组首到组尾的字节反转，就恢复了码点。然后从组尾的下一个字节继续。

这个分组方法依赖“合法 UTF-8”这个前提。如果输入里有非法序列，组边界可能找不到，所以反转前先调用 `aletheia_utf8_count` 验证。验证通过，分组一定成立；验证失败，直接拒绝，不改内存。反转后再验证一次，确认结果仍然是合法 UTF-8，防止实现错误把字符串弄坏。

### 5.3 不变量与复杂度

反转前后，字节长度不变，字符数不变。字节长度不变，因为只是交换字节，没有增删；字符数不变，因为码点的个数不变，只是顺序反了。终止符不参与反转，它留在原位置 $a+n$，反转范围是 $[a,a+n)$，右端开，正好不碰终止符。

反转是一个对合运算：反转两次回到原字符串。

$$
\operatorname{reverse}(\operatorname{reverse}(s))=s
$$

这个性质可以用来验收：对每个测试字符串反转两次，比较是否和原串相等。程序里没有单独做双重反转，但 BEFORE 和 AFTER 的对照已经验证了一次反转的正确性；双重反转可以作为读者练习。

时间复杂度是 $O(n)$：第一阶段交换 $n/2$ 对字节，第二阶段每个字节最多被访问两次，总步数和字节数成正比。空间复杂度是 $O(1)$：只用几个下标和两个临时字节。没有分配缓冲区，没有递归，没有额外数组。对一台只有一块静态数组的机器来说，原地算法很重要，因为它不需要第二个字符串的空间。

## 六、把 AletheiaStr 写成 C

### 6.1 字符串结构体

字符串描述符只有两个字段：

```c
struct AletheiaStr {
    AletheiaAddr addr;
    uint32_t capacity;
};
```

`addr` 是起始地址，`capacity` 是可用字节数，包含终止符的位置。结构体大小 8 字节，两个 4 字节字段，没有空洞。它不存长度，长度由 `aletheia_strlen` 扫描得到。它不存字符数，字符数由 `aletheia_utf8_count` 解析得到。

有效性检查复用指针层：

```c
static bool aletheia_str_ok(const struct AletheiaStr *s) {
    struct AletheiaPtr p;
    if (s == NULL || s->capacity == 0u) {
        return false;
    }
    return aletheia_ptr_make(s->addr, s->capacity, &p);
}
```

`aletheia_ptr_make` 检查地址加容量不超过 262144。把容量当成一个“大元素”的大小，正好表达“这整块区域在内存里”。容量为 0 直接拒绝，因为空区域放不下终止符。这个检查和内容无关，构造时就能做。

### 6.2 求长度

`aletheia_strlen` 从起始地址造一个字节指针，逐步走：

```c
static bool aletheia_strlen(const struct AletheiaStr *s, uint32_t *out) {
    struct AletheiaPtr base;
    uint32_t i;
    if (out == NULL || !aletheia_str_ok(s)) {
        return false;
    }
    if (!aletheia_ptr_make(s->addr, 1u, &base)) {
        return false;
    }
    for (i = 0; i < s->capacity; ++i) {
        struct AletheiaPtr p;
        AletheiaByte b = 0u;
        if (!aletheia_ptr_walk(base, (int32_t)i, &p) ||
            !aletheia_ptr_read_u8(p, &b)) {
            return false;
        }
        if (b == 0u) {
            *out = i;
            return true;
        }
    }
    return false;
}
```

每一步都用 `aletheia_ptr_walk` 走 $i$ 步，读一个字节。容量最多 262144，$i$ 能装进 `int32_t`。读到 0 就写 `*out=i` 并返回成功；循环结束还没读到 0，返回失败，不写 `*out`。调用者不能把失败时的输出当成有效长度。

这个实现每次都从基指针重新走 $i$ 步，复杂度看起来是 $O(n^2)$，因为第 $i$ 步要走 $i$ 次。实际上 `aletheia_ptr_walk` 是常数时间算地址，不是循环，所以总复杂度还是 $O(n)$。如果将来走步变成真的循环，可以改成每次走一步，用一个指针变量保存当前位置。这一章保持“每次从基指针算”的写法，和前面的下标访问一致，也更容易看出地址公式。

### 6.3 写入与比较

写入函数从宿主字符串复制字节：

```c
static bool aletheia_str_put(const struct AletheiaStr *s, const char *text) {
    uint32_t n = 0u;
    uint32_t i;
    if (s == NULL || text == NULL || !aletheia_str_ok(s)) {
        return false;
    }
    while (text[n] != '\0') {
        ++n;
    }
    if (n >= s->capacity) {
        return false;
    }
    for (i = 0; i < n; ++i) {
        if (!aletheia_str_poke(s, i, (AletheiaByte)text[i])) {
            return false;
        }
    }
    return aletheia_str_poke(s, n, 0u);
}
```

先数源文本的字节数 $n$，再检查 $n<\text{capacity}$。这个不等式等价于 $n+1\le\text{capacity}$，保证终止符放得下。然后逐字节写入，最后写一个 0。源文本是宿主字符串，以 0 终止；`text[n]` 读到 0 就停。目标容量检查在写入之前，失败时不会写一半再发现放不下。

比较函数把机器字符串和宿主文本逐字节比较：

```c
static bool aletheia_str_eq_text(const struct AletheiaStr *s,
                                 const char *text) {
    uint32_t n;
    uint32_t i;
    if (text == NULL || !aletheia_strlen(s, &n)) {
        return false;
    }
    for (i = 0; i < n; ++i) {
        AletheiaByte b = 0u;
        if (text[i] == '\0' || !aletheia_str_byte(s, i, &b) ||
            b != (AletheiaByte)text[i]) {
            return false;
        }
    }
    return text[n] == '\0';
}
```

先求机器字符串的长度 $n$，再比较前 $n$ 个字节，最后检查宿主文本的第 $n$ 个字节也是 0。如果宿主文本更短，中途就会遇到 `text[i]=='\0'`，返回失败；如果更长，最后 `text[n]` 不是 0，返回失败。两边长度相等、内容相同，才返回真。

### 6.4 UTF-8 解析

`aletheia_utf8_next` 读一个码点，返回字节长度：

```c
static bool aletheia_utf8_next(AletheiaAddr addr, uint32_t remain,
                               uint32_t *out) {
    AletheiaByte b = 0u;
    AletheiaByte b1 = 0u;
    AletheiaByte b2 = 0u;
    AletheiaByte b3 = 0u;
    if (out == NULL || remain == 0u || !aletheia_peek_u8(addr, &b)) {
        return false;
    }
    if (b < 0x80u) {
        *out = 1u;
        return true;
    }
    if (b >= 0xC2u && b <= 0xDFu) {
        if (remain < 2u || !aletheia_peek_u8(addr + 1u, &b1)) {
            return false;
        }
        if ((b1 & 0xC0u) != 0x80u) {
            return false;
        }
        *out = 2u;
        return true;
    }
    if (b >= 0xE0u && b <= 0xEFu) {
        if (remain < 3u || !aletheia_peek_u8(addr + 1u, &b1) ||
            !aletheia_peek_u8(addr + 2u, &b2)) {
            return false;
        }
        if ((b1 & 0xC0u) != 0x80u || (b2 & 0xC0u) != 0x80u) {
            return false;
        }
        if (b == 0xE0u && b1 < 0xA0u) {
            return false;
        }
        if (b == 0xEDu && b1 > 0x9Fu) {
            return false;
        }
        *out = 3u;
        return true;
    }
    if (b >= 0xF0u && b <= 0xF4u) {
        if (remain < 4u || !aletheia_peek_u8(addr + 1u, &b1) ||
            !aletheia_peek_u8(addr + 2u, &b2) ||
            !aletheia_peek_u8(addr + 3u, &b3)) {
            return false;
        }
        if ((b1 & 0xC0u) != 0x80u || (b2 & 0xC0u) != 0x80u ||
            (b3 & 0xC0u) != 0x80u) {
            return false;
        }
        if (b == 0xF0u && b1 < 0x90u) {
            return false;
        }
        if (b == 0xF4u && b1 > 0x8Fu) {
            return false;
        }
        *out = 4u;
        return true;
    }
    return false;
}
```

函数按首字节分四支：ASCII、两字节、三字节、四字节。每一支先检查剩余字节数，再读续字节，再检查续字节的高两位是 `10`。三字节和四字节还额外检查过长编码、代理区和码点上限。所有读取都先检查 `remain`，不会读到字符串末尾之外。首字节落在 0x80 到 0xC1、0xF5 到 0xFF 的，直接拒绝。

`aletheia_utf8_count` 先求长度，再从头解析：

```c
static bool aletheia_utf8_count(const struct AletheiaStr *s, uint32_t *out) {
    uint32_t n;
    uint32_t i = 0u;
    uint32_t count = 0u;
    if (out == NULL || !aletheia_strlen(s, &n)) {
        return false;
    }
    while (i < n) {
        uint32_t len = 0u;
        if (!aletheia_utf8_next(s->addr + i, n - i, &len)) {
            return false;
        }
        i += len;
        ++count;
    }
    *out = count;
    return true;
}
```

每次解析一个码点，`i` 跳过它的字节数，`count` 加一。`n-i` 是剩余字节数，传给解析器做边界检查。循环结束时 `i` 正好等于 $n$，不会多也不会少。任何一个码点非法，函数返回失败，不写 `*out`。

### 6.5 反转

反转函数先用 `aletheia_strlen` 和 `aletheia_utf8_count` 验证，然后做两阶段交换：

```c
static bool aletheia_str_reverse(struct AletheiaStr *s) {
    uint32_t n;
    uint32_t count;
    uint32_t i;
    uint32_t j;
    if (s == NULL || !aletheia_strlen(s, &n) ||
        !aletheia_utf8_count(s, &count)) {
        return false;
    }
    if (n < 2u) {
        return true;
    }
    i = 0u;
    j = n;
    while (i < j) {
        --j;
        if (i >= j) {
            break;
        }
        if (!aletheia_swap_u8(s->addr + i, s->addr + j)) {
            return false;
        }
        ++i;
    }
    i = 0u;
    while (i < n) {
        uint32_t start = i;
        uint32_t end = i;
        uint32_t group_end;
        AletheiaByte b = 0u;
        while (end < n) {
            if (!aletheia_str_byte(s, end, &b)) {
                return false;
            }
            if ((b & 0xC0u) != 0x80u) {
                break;
            }
            ++end;
        }
        if (end >= n) {
            return false;
        }
        group_end = end;
        while (start < end) {
            if (!aletheia_swap_u8(s->addr + start, s->addr + end)) {
                return false;
            }
            ++start;
            --end;
        }
        i = group_end + 1u;
    }
    return aletheia_utf8_count(s, &count);
}
```

第一阶段用两个下标 `i` 和 `j` 从两端向中间交换。`j` 初始为 $n$，每轮先减一，指向最后一个未交换的字节。`i<j` 时交换，`i` 加一。`n<2` 直接返回成功，空字符串和单字节字符串不需要交换。

第二阶段从 `i=0` 开始，找当前码点的组。`end` 从 `i` 开始，遇到续字节就前进，遇到首字节就停，停下的位置是组尾。`group_end` 保存组尾，因为后面的交换会改变 `end`。如果一直走到 $n$ 都没有首字节，说明序列非法，返回失败。组内用 `start` 和 `end` 从两端交换，交换完 `start` 越过 `end`。下一组从 `group_end+1` 开始。

最后再调用一次 `aletheia_utf8_count`，确认反转后的字符串仍然是合法 UTF-8。这个检查是防御性的：合法输入经过正确算法一定还是合法，可如果算法有 bug，最后这一步能抓住。返回值是检查结果，不是“反转是否执行”的结果；执行失败在前面已经返回 `false`。

反转函数只改内容，不改描述符。`addr` 和 `capacity` 在反转前后一样，终止符的位置也一样。这符合“描述符是视图”的设计：字符串描述符描述一块区域，反转是区域内部的重排，区域本身不变。如果反转改变了容量或地址，调用者手里的其他视图就会失效；书里的约定是布局和数据分开，布局操作（构造数组、算偏移）产生描述符，数据操作（写入、反转）只改字节，不碰描述符。下一章的读写函数也遵守这个约定，读和写都只访问描述符指向的字节，不修改描述符。

失败路径也要遵守这个约定。反转前验证失败，函数立即返回，不写任何字节；交换过程中某个地址检查失败，函数返回，可能已经交换了一部分字节。后一种情况在理论上不会发生，因为验证已经保证所有地址都在范围内，每次交换都在 $[a,a+n)$ 内。如果真的发生了，说明前面的检查有 bug，字符串会被部分修改，这是实现错误，不是输入错误。书里的组件尽量把输入错误挡在修改之前，实现错误用消毒器和测试去抓，不靠运行时的“回滚”。回滚需要额外的空间保存原内容，和“原地、常数空间”的目标冲突。

## 七、完整程序

完整程序把字节层、指针层和字符串层叠在一起。字节层提供读写，指针层提供走步，字符串层提供求长度、写入、比较、UTF-8 计数和原地反转。程序先打印机器信息，再跑五组检查：LENGTH、SCAN、REVERSE、UTF8、EQUAL，最后打印汇总。

编译命令：

```bash
cc -std=c99 -O2 -Wall -Wextra -pedantic -Werror aletheia_ch07.c -o aletheia_ch07
```

完整代码：

```c
/* aletheia_ch07.c */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define ALETHEIA_SIZE ((uint32_t)256 * 1024)
#define ALETHEIA_ADDR_MAX ALETHEIA_SIZE

typedef uint8_t AletheiaByte;
typedef uint32_t AletheiaAddr;

struct AletheiaPtr {
    AletheiaAddr addr;
    uint32_t elem_size;
};

struct AletheiaStr {
    AletheiaAddr addr;
    uint32_t capacity;
};

static AletheiaByte aletheia_mem[ALETHEIA_SIZE];

typedef char aletheia_check_size[(ALETHEIA_SIZE == 262144u) ? 1 : -1];

static bool aletheia_addr_ok(AletheiaAddr addr) {
    return addr < ALETHEIA_ADDR_MAX;
}

static bool aletheia_peek_u8(AletheiaAddr addr, AletheiaByte *out) {
    if (!aletheia_addr_ok(addr) || out == NULL) {
        return false;
    }
    *out = aletheia_mem[addr];
    return true;
}

static bool aletheia_poke_u8(AletheiaAddr addr, AletheiaByte value) {
    if (!aletheia_addr_ok(addr)) {
        return false;
    }
    aletheia_mem[addr] = value;
    return true;
}

static bool aletheia_ptr_make(AletheiaAddr addr, uint32_t elem_size,
                              struct AletheiaPtr *out) {
    if (out == NULL || elem_size == 0u) {
        return false;
    }
    if (elem_size > ALETHEIA_SIZE) {
        return false;
    }
    if (addr > ALETHEIA_ADDR_MAX - elem_size) {
        return false;
    }
    *out = (struct AletheiaPtr){ addr, elem_size };
    return true;
}

static bool aletheia_ptr_ok(struct AletheiaPtr p) {
    if (p.elem_size == 0u || p.elem_size > ALETHEIA_SIZE) {
        return false;
    }
    return p.addr <= ALETHEIA_ADDR_MAX - p.elem_size;
}

static bool aletheia_ptr_walk(struct AletheiaPtr p, int32_t k,
                              struct AletheiaPtr *out) {
    int64_t delta;
    int64_t next;
    if (out == NULL || !aletheia_ptr_ok(p)) {
        return false;
    }
    delta = (int64_t)k * (int64_t)p.elem_size;
    next = (int64_t)p.addr + delta;
    if (next < 0) {
        return false;
    }
    if (next > (int64_t)(ALETHEIA_SIZE - p.elem_size)) {
        return false;
    }
    *out = (struct AletheiaPtr){ (AletheiaAddr)next, p.elem_size };
    return true;
}

static bool aletheia_ptr_read_u8(struct AletheiaPtr p, AletheiaByte *out) {
    if (out == NULL || !aletheia_ptr_ok(p)) {
        return false;
    }
    return aletheia_peek_u8(p.addr, out);
}

static bool aletheia_ptr_write_u8(struct AletheiaPtr p, AletheiaByte value) {
    if (!aletheia_ptr_ok(p)) {
        return false;
    }
    return aletheia_poke_u8(p.addr, value);
}

/* 字符串 = 起始地址 + 可用字节数；长度由第一个 NUL 决定。 */
static bool aletheia_str_ok(const struct AletheiaStr *s) {
    struct AletheiaPtr p;
    if (s == NULL || s->capacity == 0u) {
        return false;
    }
    return aletheia_ptr_make(s->addr, s->capacity, &p);
}

static bool aletheia_str_make(AletheiaAddr addr, uint32_t capacity,
                              struct AletheiaStr *out) {
    struct AletheiaStr s;
    if (out == NULL) {
        return false;
    }
    s = (struct AletheiaStr){ addr, capacity };
    if (!aletheia_str_ok(&s)) {
        return false;
    }
    *out = s;
    return true;
}

static bool aletheia_str_byte(const struct AletheiaStr *s, uint32_t i,
                              AletheiaByte *out) {
    struct AletheiaPtr p;
    if (s == NULL || out == NULL || !aletheia_str_ok(s) || i >= s->capacity) {
        return false;
    }
    if (!aletheia_ptr_make(s->addr + i, 1u, &p)) {
        return false;
    }
    return aletheia_ptr_read_u8(p, out);
}

static bool aletheia_str_poke(const struct AletheiaStr *s, uint32_t i,
                              AletheiaByte value) {
    struct AletheiaPtr p;
    if (s == NULL || !aletheia_str_ok(s) || i >= s->capacity) {
        return false;
    }
    if (!aletheia_ptr_make(s->addr + i, 1u, &p)) {
        return false;
    }
    return aletheia_ptr_write_u8(p, value);
}

/* 在容量范围内找第一个 NUL；找不到就是没有终止符。 */
static bool aletheia_strlen(const struct AletheiaStr *s, uint32_t *out) {
    struct AletheiaPtr base;
    uint32_t i;
    if (out == NULL || !aletheia_str_ok(s)) {
        return false;
    }
    if (!aletheia_ptr_make(s->addr, 1u, &base)) {
        return false;
    }
    for (i = 0; i < s->capacity; ++i) {
        struct AletheiaPtr p;
        AletheiaByte b = 0u;
        if (!aletheia_ptr_walk(base, (int32_t)i, &p) ||
            !aletheia_ptr_read_u8(p, &b)) {
            return false;
        }
        if (b == 0u) {
            *out = i;
            return true;
        }
    }
    return false;
}

static bool aletheia_str_put(const struct AletheiaStr *s, const char *text) {
    uint32_t n = 0u;
    uint32_t i;
    if (s == NULL || text == NULL || !aletheia_str_ok(s)) {
        return false;
    }
    while (text[n] != '\0') {
        ++n;
    }
    if (n >= s->capacity) {
        return false;
    }
    for (i = 0; i < n; ++i) {
        if (!aletheia_str_poke(s, i, (AletheiaByte)text[i])) {
            return false;
        }
    }
    return aletheia_str_poke(s, n, 0u);
}

static bool aletheia_str_eq_text(const struct AletheiaStr *s,
                                 const char *text) {
    uint32_t n;
    uint32_t i;
    if (text == NULL || !aletheia_strlen(s, &n)) {
        return false;
    }
    for (i = 0; i < n; ++i) {
        AletheiaByte b = 0u;
        if (text[i] == '\0' || !aletheia_str_byte(s, i, &b) ||
            b != (AletheiaByte)text[i]) {
            return false;
        }
    }
    return text[n] == '\0';
}

static bool aletheia_str_print(const struct AletheiaStr *s) {
    uint32_t n;
    uint32_t limit;
    uint32_t i;
    bool terminated = aletheia_strlen(s, &n);
    if (!aletheia_str_ok(s)) {
        printf("(bad string)");
        return false;
    }
    limit = terminated ? n : s->capacity;
    for (i = 0; i < limit; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_str_byte(s, i, &b)) {
            return false;
        }
        putchar((int)b);
    }
    if (!terminated) {
        printf("(unterminated)");
    }
    return terminated;
}

/* 读一个 UTF-8 码元：返回字节数，非法就拒绝。 */
static bool aletheia_utf8_next(AletheiaAddr addr, uint32_t remain,
                               uint32_t *out) {
    AletheiaByte b = 0u;
    AletheiaByte b1 = 0u;
    AletheiaByte b2 = 0u;
    AletheiaByte b3 = 0u;
    if (out == NULL || remain == 0u || !aletheia_peek_u8(addr, &b)) {
        return false;
    }
    if (b < 0x80u) {
        *out = 1u;
        return true;
    }
    if (b >= 0xC2u && b <= 0xDFu) {
        if (remain < 2u || !aletheia_peek_u8(addr + 1u, &b1)) {
            return false;
        }
        if ((b1 & 0xC0u) != 0x80u) {
            return false;
        }
        *out = 2u;
        return true;
    }
    if (b >= 0xE0u && b <= 0xEFu) {
        if (remain < 3u || !aletheia_peek_u8(addr + 1u, &b1) ||
            !aletheia_peek_u8(addr + 2u, &b2)) {
            return false;
        }
        if ((b1 & 0xC0u) != 0x80u || (b2 & 0xC0u) != 0x80u) {
            return false;
        }
        if (b == 0xE0u && b1 < 0xA0u) {
            return false;
        }
        if (b == 0xEDu && b1 > 0x9Fu) {
            return false;
        }
        *out = 3u;
        return true;
    }
    if (b >= 0xF0u && b <= 0xF4u) {
        if (remain < 4u || !aletheia_peek_u8(addr + 1u, &b1) ||
            !aletheia_peek_u8(addr + 2u, &b2) ||
            !aletheia_peek_u8(addr + 3u, &b3)) {
            return false;
        }
        if ((b1 & 0xC0u) != 0x80u || (b2 & 0xC0u) != 0x80u ||
            (b3 & 0xC0u) != 0x80u) {
            return false;
        }
        if (b == 0xF0u && b1 < 0x90u) {
            return false;
        }
        if (b == 0xF4u && b1 > 0x8Fu) {
            return false;
        }
        *out = 4u;
        return true;
    }
    return false;
}

static bool aletheia_utf8_count(const struct AletheiaStr *s, uint32_t *out) {
    uint32_t n;
    uint32_t i = 0u;
    uint32_t count = 0u;
    if (out == NULL || !aletheia_strlen(s, &n)) {
        return false;
    }
    while (i < n) {
        uint32_t len = 0u;
        if (!aletheia_utf8_next(s->addr + i, n - i, &len)) {
            return false;
        }
        i += len;
        ++count;
    }
    *out = count;
    return true;
}

static bool aletheia_swap_u8(AletheiaAddr a, AletheiaAddr b) {
    AletheiaByte x = 0u;
    AletheiaByte y = 0u;
    if (!aletheia_peek_u8(a, &x) || !aletheia_peek_u8(b, &y)) {
        return false;
    }
    return aletheia_poke_u8(a, y) && aletheia_poke_u8(b, x);
}

/* 原地反转：先反全部字节，再把每个码元的字节反回来。 */
static bool aletheia_str_reverse(struct AletheiaStr *s) {
    uint32_t n;
    uint32_t count;
    uint32_t i;
    uint32_t j;
    if (s == NULL || !aletheia_strlen(s, &n) ||
        !aletheia_utf8_count(s, &count)) {
        return false;
    }
    if (n < 2u) {
        return true;
    }
    i = 0u;
    j = n;
    while (i < j) {
        --j;
        if (i >= j) {
            break;
        }
        if (!aletheia_swap_u8(s->addr + i, s->addr + j)) {
            return false;
        }
        ++i;
    }
    i = 0u;
    while (i < n) {
        uint32_t start = i;
        uint32_t end = i;
        uint32_t group_end;
        AletheiaByte b = 0u;
        while (end < n) {
            if (!aletheia_str_byte(s, end, &b)) {
                return false;
            }
            if ((b & 0xC0u) != 0x80u) {
                break;
            }
            ++end;
        }
        if (end >= n) {
            return false;
        }
        group_end = end;
        while (start < end) {
            if (!aletheia_swap_u8(s->addr + start, s->addr + end)) {
                return false;
            }
            ++start;
            --end;
        }
        i = group_end + 1u;
    }
    return aletheia_utf8_count(s, &count);
}

static bool aletheia_check_length(void) {
    static const struct {
        AletheiaAddr addr;
        uint32_t capacity;
        const char *text;
        uint32_t bytes;
        uint32_t chars;
    } cases[] = {
        { 0x00500u, 16u, "hello", 5u, 5u },
        { 0x00520u, 16u, "大力玩", 9u, 3u },
        { 0x00540u, 16u, "A中B", 5u, 3u },
        { 0x00560u, 8u, "", 0u, 0u }
    };
    size_t i;
    bool ok = true;
    printf("LENGTH\n");
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        struct AletheiaStr s;
        uint32_t n = 0u;
        uint32_t chars = 0u;
        bool made = aletheia_str_make(cases[i].addr, cases[i].capacity, &s);
        bool put = made && aletheia_str_put(&s, cases[i].text);
        bool len = put && aletheia_strlen(&s, &n);
        bool cnt = len && aletheia_utf8_count(&s, &chars);
        printf("TEXT=");
        if (put) {
            aletheia_str_print(&s);
        } else {
            printf("(bad)");
        }
        printf(" BYTES=%u CHARS=%u NUL=0x%05x\n",
               (unsigned)n, (unsigned)chars,
               (unsigned)(cases[i].addr + n));
        if (!made || !put || !len || !cnt ||
            n != cases[i].bytes || chars != cases[i].chars) {
            ok = false;
        }
    }
    return ok;
}

static bool aletheia_check_scan(void) {
    struct AletheiaStr s;
    bool made = aletheia_str_make(0x00500u, 16u, &s);
    bool put = made && aletheia_str_put(&s, "hello");
    bool ok = made && put;
    printf("SCAN\n");
    printf("CAP RESULT LEN\n");
    if (!ok) {
        printf("bad string\n");
        return false;
    }
    {
        struct AletheiaStr a = { s.addr, 6u };
        uint32_t n = 0u;
        bool len = aletheia_strlen(&a, &n);
        printf("%u   %-8s %u\n", (unsigned)a.capacity,
               len ? "ok" : "rejected", (unsigned)(len ? n : 0u));
        if (!len || n != 5u) {
            ok = false;
        }
    }
    {
        struct AletheiaStr a = { s.addr, 5u };
        uint32_t n = 0u;
        bool len = aletheia_strlen(&a, &n);
        printf("%u   %-8s %u\n", (unsigned)a.capacity,
               len ? "ok" : "rejected", (unsigned)(len ? n : 0u));
        if (len) {
            ok = false;
        }
    }
    return ok;
}

static bool aletheia_check_reverse(void) {
    static const struct {
        AletheiaAddr addr;
        uint32_t capacity;
        const char *before;
        const char *after;
        uint32_t bytes;
        uint32_t chars;
    } cases[] = {
        { 0x00580u, 16u, "abcdef", "fedcba", 6u, 6u },
        { 0x005a0u, 16u, "A中B", "B中A", 5u, 3u },
        { 0x005c0u, 32u, "你好世界", "界世好你", 12u, 4u },
        { 0x005e0u, 8u, "", "", 0u, 0u }
    };
    size_t i;
    bool ok = true;
    printf("REVERSE\n");
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        struct AletheiaStr s;
        uint32_t n = 0u;
        uint32_t chars = 0u;
        bool made = aletheia_str_make(cases[i].addr, cases[i].capacity, &s);
        bool put = made && aletheia_str_put(&s, cases[i].before);
        bool eq_before = put && aletheia_str_eq_text(&s, cases[i].before);
        bool rev;
        bool len;
        bool cnt;
        bool eq_after;
        printf("BEFORE=");
        if (put) aletheia_str_print(&s);
        printf(" BYTES=%u CHARS=%u\n",
               (unsigned)(put ? cases[i].bytes : 0u),
               (unsigned)(put ? cases[i].chars : 0u));
        rev = eq_before && aletheia_str_reverse(&s);
        len = rev && aletheia_strlen(&s, &n);
        cnt = len && aletheia_utf8_count(&s, &chars);
        eq_after = cnt && aletheia_str_eq_text(&s, cases[i].after);
        printf("AFTER =");
        if (rev) aletheia_str_print(&s);
        printf(" BYTES=%u CHARS=%u\n",
               (unsigned)(rev ? n : 0u), (unsigned)(cnt ? chars : 0u));
        if (!made || !put || !eq_before || !rev || !len || !cnt ||
            !eq_after || n != cases[i].bytes || chars != cases[i].chars) {
            ok = false;
        }
    }
    return ok;
}

static bool aletheia_set_raw(struct AletheiaStr *s,
                             const AletheiaByte *bytes, uint32_t n) {
    uint32_t i;
    if (s == NULL || bytes == NULL || n > s->capacity) {
        return false;
    }
    for (i = 0; i < n; ++i) {
        if (!aletheia_str_poke(s, i, bytes[i])) {
            return false;
        }
    }
    return true;
}

static bool aletheia_check_utf8(void) {
    static const AletheiaByte bad1[] = { 0xE4u, 0x41u, 0x00u };
    static const AletheiaByte bad2[] = { 0xC0u, 0x80u, 0x00u };
    static const AletheiaByte bad3[] = { 0xF0u, 0x9Fu, 0x00u };
    static const AletheiaByte bad4[] = { 0x61u, 0x62u, 0x63u };
    static const struct {
        AletheiaAddr addr;
        const AletheiaByte *bytes;
        uint32_t n;
        const char *label;
    } cases[] = {
        { 0x00600u, bad1, 3u, "E4 41 00" },
        { 0x00610u, bad2, 3u, "C0 80 00" },
        { 0x00620u, bad3, 3u, "F0 9F 00" },
        { 0x00630u, bad4, 3u, "61 62 63" }
    };
    size_t i;
    bool ok = true;
    printf("UTF8\n");
    printf("CASE      RESULT\n");
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        struct AletheiaStr s;
        uint32_t chars = 0u;
        bool made = aletheia_str_make(cases[i].addr, cases[i].n, &s);
        bool set = made && aletheia_set_raw(&s, cases[i].bytes, cases[i].n);
        bool cnt = set && aletheia_utf8_count(&s, &chars);
        bool rev = set && aletheia_str_reverse(&s);
        printf("%-9s %s\n", cases[i].label, cnt ? "accepted" : "rejected");
        if (!made || !set || cnt || rev) {
            ok = false;
        }
    }
    return ok;
}

static bool aletheia_check_equal(void) {
    struct AletheiaStr s;
    bool made = aletheia_str_make(0x00520u, 16u, &s);
    bool put = made && aletheia_str_put(&s, "大力玩");
    bool ok = made && put;
    printf("EQUAL\n");
    if (!ok) {
        printf("bad string\n");
        return false;
    }
    {
        bool same = aletheia_str_eq_text(&s, "大力玩");
        bool diff = aletheia_str_eq_text(&s, "大力丸");
        printf("大力玩==大力玩 : %s\n", same ? "true" : "false");
        printf("大力玩==大力丸 : %s\n", diff ? "true" : "false");
        if (!same || diff) {
            ok = false;
        }
    }
    return ok;
}

int main(void) {
    bool length_ok;
    bool scan_ok;
    bool reverse_ok;
    bool utf8_ok;
    bool equal_ok;

    printf("ALETHEIA STR\n");
    printf("SIZE      : %u bytes\n", (unsigned)ALETHEIA_SIZE);
    printf("ADDR RANGE: 0x00000..0x3ffff\n");
    printf("STR BYTES : %lu\n", (unsigned long)sizeof(struct AletheiaStr));
    printf("\n");

    length_ok = aletheia_check_length();
    printf("\n");
    scan_ok = aletheia_check_scan();
    printf("\n");
    reverse_ok = aletheia_check_reverse();
    printf("\n");
    utf8_ok = aletheia_check_utf8();
    printf("\n");
    equal_ok = aletheia_check_equal();
    printf("\n");

    printf("SUMMARY\n");
    printf("length  : %s\n", length_ok ? "true" : "false");
    printf("scan    : %s\n", scan_ok ? "true" : "false");
    printf("reverse : %s\n", reverse_ok ? "true" : "false");
    printf("utf8    : %s\n", utf8_ok ? "true" : "false");
    printf("equal   : %s\n", equal_ok ? "true" : "false");
    if (length_ok && scan_ok && reverse_ok && utf8_ok && equal_ok) {
        printf("ALETHEIA STR OK\n");
        return 0;
    }
    printf("ALETHEIA STR BROKEN\n");
    return 1;
}
```

程序大约六百行。它没有 `malloc`，没有 `<string.h>`，没有 `strlen`、`strcpy`、`memcpy`。所有字符串操作都经过字节层和指针层，所有长度都由扫描得到，所有 UTF-8 序列都按规则检查。编译用 `-std=c99 -O2 -Wall -Wextra -pedantic -Werror`，没有警告。

## 八、真实输出与验收

在本地编译运行，得到以下输出：

```text
ALETHEIA STR
SIZE      : 262144 bytes
ADDR RANGE: 0x00000..0x3ffff
STR BYTES : 8

LENGTH
TEXT=hello BYTES=5 CHARS=5 NUL=0x00505
TEXT=大力玩 BYTES=9 CHARS=3 NUL=0x00529
TEXT=A中B BYTES=5 CHARS=3 NUL=0x00545
TEXT= BYTES=0 CHARS=0 NUL=0x00560

SCAN
CAP RESULT LEN
6   ok       5
5   rejected 0

REVERSE
BEFORE=abcdef BYTES=6 CHARS=6
AFTER =fedcba BYTES=6 CHARS=6
BEFORE=A中B BYTES=5 CHARS=3
AFTER =B中A BYTES=5 CHARS=3
BEFORE=你好世界 BYTES=12 CHARS=4
AFTER =界世好你 BYTES=12 CHARS=4
BEFORE= BYTES=0 CHARS=0
AFTER = BYTES=0 CHARS=0

UTF8
CASE      RESULT
E4 41 00  rejected
C0 80 00  rejected
F0 9F 00  rejected
61 62 63  rejected

EQUAL
大力玩==大力玩 : true
大力玩==大力丸 : false

SUMMARY
length  : true
scan    : true
reverse : true
utf8    : true
equal   : true
ALETHEIA STR OK
```

逐段看。头部打印机器大小、地址范围、字符串结构体大小。`AletheiaStr` 是 8 字节，地址和容量各 4 字节，没有空洞。这个大小和前一章的结构体规则一致：两个四字节字段，对齐 4，总大小 8。

LENGTH 段打印四个字符串的字节数、字符数和终止符地址。`hello` 是 5 和 5，终止符在 0x00505；`大力玩` 是 9 和 3，终止符在 0x00529；`A中B` 是 5 和 3，终止符在 0x00545；空字符串是 0 和 0，终止符就在起点 0x00560。每一行的字节数和字符数都和手算一致，终止符地址等于起点加字节数。

SCAN 段用同一个 `hello` 测两个容量。容量 6 时，五个字符加一个终止符正好放下，扫描返回 5；容量 5 时，五个字符填满，没有终止符，扫描返回失败。失败那一行的长度打印 0，只是占位，表示“没有有效长度”，不是真实长度。这一段验证了容量必须覆盖终止符这条不变量。

REVERSE 段打印四组反转前后。`abcdef` 反成 `fedcba`，字节数和字符数都是 6。`A中B` 反成 `B中A`，字节数 5，字符数 3，多字节字符保持完整。`你好世界` 反成 `界世好你`，字节数 12，字符数 4。空字符串反转后还是空字符串。四组的字节数和字符数在反转前后都不变，顺序反了，长度没变。

这四组覆盖了反转的三种情况。纯 ASCII 是单字节组，第一阶段反转字节就是最终结果，第二阶段每组只有一个字节，交换不改变内容。混合串 `A中B` 有一个多字节组，第一阶段把它的字节倒过来，第二阶段再倒回去，组的位置跟着整体顺序走。全中文串每组都是三字节，第二阶段要连续处理四个组，任何一组的边界算错都会留下乱码。空字符串没有字节，第一阶段直接返回，第二阶段不执行，函数返回成功。如果只测 ASCII，反转算法看起来完全正确；只有加入中文，才会发现只反字节不够。

反转的验收还要看失败路径。UTF8 段的四个非法输入，`aletheia_str_reverse` 都在验证阶段返回失败，没有进入交换循环。判断方法是：失败后再打印内存，字节和输入完全一样，没有被改过。程序里没有单独打印失败后的内存，但代码结构保证了这一点：`aletheia_str_reverse` 第一行调用 `aletheia_strlen` 和 `aletheia_utf8_count`，两个都成功才继续；任何一个失败，直接返回，后面的交换代码不执行。这种“先验证、后修改”的顺序很重要。如果先交换再验证，失败时字符串已经被改坏，调用者拿到一个半截结果，既不是原来的字符串，也不是合法的反转结果。

验收还可以加一条：对每个合法字符串反转两次，结果应该和原串相等。这是对合性质，程序里没有打印，可它由两阶段算法保证。第一次反转把 $c_1\cdots c_k$ 变成 $c_k\cdots c_1$，第二次再变回 $c_1\cdots c_k$。字节长度和字符数在每次反转后都不变，所以两次之后内容完全恢复。读者可以把这个检查加进程序，作为一个额外的验收项。

UTF8 段打印四个非法案例，全部拒绝。`E4 41 00` 的续字节错，`C0 80 00` 是过长编码，`F0 9F 00` 被截断，`61 62 63` 没有终止符。每一行的 `rejected` 同时表示 UTF-8 计数失败和反转被拒绝。反转在验证阶段就返回，不会改动内存，所以非法字符串不会被改成半截。

EQUAL 段比较机器里的 `大力玩` 和两个宿主文本。相同的那行返回 `true`，只差最后一个字的 `大力丸` 返回 `false`。比较是逐字节的，UTF-8 编码相同才相等，编码不同但看起来相似的字符不会误判。

验收标准有五条：

1. 四个字符串的字节数、字符数、终止符地址全部正确。
2. 容量 6 时 `hello` 长度为 5，容量 5 时被拒绝。
3. 四组反转的前后内容和字节数、字符数全部正确，多字节字符没有被拆坏。
4. 四种非法 UTF-8 或无终止符的输入全部被拒绝。
5. 相同字符串比较为真，不同字符串比较为假。

五条全部为真，程序打印 `ALETHEIA STR OK` 并返回 0。输出是纯字符，最宽一行 42 列。中文字符在终端里占两列，但程序不按显示宽度排版，按字节输出；42 列是按字节算的上限，实际显示宽度也不超过 80 列。重复运行输出完全一致，没有随机数、时间戳或宿主地址。

这个程序也在 ASan 和 UBSan 下跑过。所有扫描都受容量限制，所有指针走步都检查内存边界，所有交换都在 $[a,a+n)$ 内，所有 UTF-8 读取都先检查剩余字节数。两个消毒器都没有报错，输出和普通编译一致。

## 九、交给下一章

这一章定义了 `AletheiaStr`，一个由起始地址和容量组成的字符串描述符。它提供构造、有效性检查、求长度、写入、比较、UTF-8 码点计数和原地反转。`aletheia_strlen` 在容量内找第一个 0，`aletheia_utf8_count` 解析码点并验证序列，`aletheia_str_reverse` 用两阶段交换实现按字符反转。

交给下一章的接口是：

```c
struct AletheiaStr {
    AletheiaAddr addr;
    uint32_t capacity;
};
```

以及 `aletheia_str_make`、`aletheia_str_ok`、`aletheia_strlen`、`aletheia_str_put`、`aletheia_str_eq_text`、`aletheia_utf8_count`、`aletheia_str_reverse`。下一章如果需要“一段文本”，可以直接用 `AletheiaStr`，把容量设成字节数，把终止符算在内。如果需要“一段二进制数据”，不要用 `AletheiaStr`，因为二进制里可能有 0；用地址加长度，或者用下一章的读写函数。

下一章是字节读写。字符串把字节当成字符，一个字节一个字节地读；多字节整数要把几个字节拼成一个数，需要知道字节顺序。一个 32 位整数 0x12345678 存在内存里，可能是 `78 56 34 12`，也可能是 `12 34 56 78`，取决于机器用大端还是小端。Aletheia 选小端：最低有效字节放在最低地址。下一章会写 `aletheia_read_u32` 和 `aletheia_write_u32`，逐字节拼装，不做类型双关，不依赖宿主对齐。

字符串和整数在内存里都是字节，区别在于解释方式。字符串遇到 0 停，整数按固定宽度读；字符串的长度是扫描出来的，整数的宽度是类型决定的。下一章会把“按宽度读字节”这件事做成组件，和这一章的“按终止符读字节”并列。两者都建立在第一至五章的字节、地址、指针、数组上，也都会在最后一章的总装里出现。

这一章从“有长度”走向“有终止符”，从“等宽元素”走向“变宽字符”，从“直接读”走向“先验证再读”。下一章会从“文本”走向“数值”，从“字节序列”走向“字节序”。先把这两个长度收好：字节长度是内存的尺子，字符数是文本的尺子，两把尺子都不能丢。
