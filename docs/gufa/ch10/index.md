# 总装

> 第十章。零件：`AletheiaMem`。九种看法，一块内存。

## 一、回访：九种看法

前九章各造了一个零件。第一章定义字节和地址，内存是一张从地址到字节的映射。第二章把变量看成区间，起点加大小，左闭右开。第三章把负数放进字节，用补码把减法变成加法。第四章让指针走步，一个指针加一个整数，地址按元素大小移动。第五章把数组拉直，下标和地址之间只差一次乘法。第六章把结构体拆开，字段之间有偏移，偏移之间可能有空洞。第七章给字符串找尽头，终止符之前的字节都是内容。第八章统一多字节读写，小端把最低有效字节放在最低地址。第九章把内存摊开，十六进制行、ASCII 列、区间标注、覆盖统计。

九个零件，九种看法，看的却是同一块内存。第一章看一个字节，第二章看一段区间，第三章看一个负数，第四章看一个指针，第五章看一排元素，第六章看一个记录，第七章看一句话，第八章看一个整数，第九章看一整片。每一种看法都建立在前一种之上，每一种看法都有自己的检查函数。问题是，前九章的检查各自为政：字节层检查地址，存储层检查区间，纸带层检查标注，谁也没有对整台机器负责。

这一章不造新零件。这一章把九个零件装进一个程序，让它们共用一块 256 KiB 的静态数组、一套地址、一条访问路径。装完以后，读者拿到的是一个可以检查的内存描述符 `AletheiaMem`，以及由它派生的七种视图：`AletheiaSpan`、`AletheiaPtr`、`AletheiaArr`、`AletheiaStruct`、`AletheiaStr`、`AletheiaStore`、`AletheiaTape`。每种视图的第一个参数都是 `const struct AletheiaMem *m`，所有字节访问最终落到 `aletheia_peek_u8` 和 `aletheia_poke_u8`。第二卷会在这个描述符上盖分配器，第三卷会在分配器上盖机器，第四卷会在机器上跑算法。地基就在这一章打完。

## 二、开场实验：九个零件，一块数组

先做一次思想实验。假设前九章的程序各带一块 256 KiB 数组。第一章的 `aletheia_mem` 在文件 A，第八章的 `aletheia_mem` 在文件 B，第九章的纸带又指向文件 C 的一块区域。三个数组内容不同，地址相同。读者从文件 A 里拿到地址 0x00800，把它交给文件 B 的读函数，读出来的是文件 B 的 0x00800，不是文件 A 的。地址没有变，内存变了。这不是指针错误，是机器错误：一台机器只能有一块内存，不能有九块。

总装的第一步是删掉多余的数组，只留一块。所有章节的零件改成接收同一个描述符，描述符指向同一块数组。地址不再属于某个文件的局部数组，地址属于整台机器。第二步是删掉多余的边界检查，只留一层。字节层不再自己判断地址是否合法，它把判断交给 `AletheiaMem`；存储层不再自己判断区间，它也交给 `AletheiaMem`；纸带层把标注放进一个 `AletheiaStore`，再由存储层交给机器。第三步是把九种看法串起来，让一个程序从头到尾跑一遍，最后打印一个总结果。

装完后的机器有这样一张启动图：

```text
BOOT  : 0x00000..0x0003f
CODE  : 0x00100..0x002ff
DATA  : 0x01000..0x010ff
STACK : 0x3f000..0x3f1ff
FREE  : 0x3f200..0x3ffff
```

启动区放签名，代码区留 512 字节，数据区放演示值，栈区在机器高处，空闲区接在栈区后面。区域之间有大段空隙，那些空隙没有标注，也没有内容。启动图不是整块内存的转储，是整块内存的目录。目录告诉读者每一段从哪里开始、到哪里结束、有多大；转储告诉读者每一段里到底有哪些字节。两个合起来，才是一台机器的完整画像。

这一章的程序会打印这些内容：启动图、标注表、地址查找、纸带表、指针算术表、数组表、结构体布局表、记录字段、字符串、启动签名、栈顶、区间表、十六进制转储、覆盖统计、失败检查和汇总。每一段都来自同一块数组，每一次读写都经过 `AletheiaMem`。程序最后打印 `ALETHEIA MEM OK`，表示九种看法在同一块内存上达成一致。

看一次写入的完整路径。调用者想把值 7 写到记录的第一个字段，地址 0x01020，宽度 4。它先通过 `aletheia_field_ptr` 拿到字段指针，再调用 `aletheia_store_write_u32`，传入机器描述符、存储窗口、地址、值。存储层调用 `aletheia_store_write_le`，宽度 4。`store_write_le` 调用 `store_has`，检查地址落在记录的存储窗口内；通过后调用 `aletheia_mem_write_le`。机器层调用 `mem_has`，再检查地址落在整台机器内；通过后 `mem_write_le` 进入循环，取出最低字节 0x07，调用 `poke_u8` 写到 0x01020；再取下一个字节 0x00，写到 0x01021；再取两个 0x00，写到 0x01022 和 0x01023。四次 `poke_u8`，每次都要再查一次 `mem_has`。最后 `mem_write_le` 返回真，存储层返回真，调用者看到成功。整条路径上，数组只被 `poke_u8` 碰了四次，边界被存储层和机器层各查了一遍，没有任何一层跳过检查。

这条路径看起来重复：外层已经检查过区间，内层每次 `poke_u8` 又检查一遍。重复是有意的。存储层检查保证整个记录窗口合法，机器层检查保证整台机器合法，内层检查保证每个单字节访问也合法；三层都通过，才能排除“外层算错但内层碰巧挡住”和“内层放宽但外层没发现”的情况。教学代码宁可多查几次，也不把正确性寄托在“调用者已经检查过”的口头约定上。真要优化，可以把内层检查合并成一次区间检查加四次无检查写入，但那要引入一个新的内部入口；这一章不引入，保持只有 `peek_u8` 和 `poke_u8` 两个入口。

## 三、一台机器的地址空间

### 3.1 一块数组

Aletheia 的全部内存是一个静态数组：

```c
static AletheiaByte aletheia_mem[ALETHEIA_SIZE];
```

`ALETHEIA_SIZE` 是 $256\cdot1024=262144$。数组下标从 0 到 262143，地址也用同一套编号。地址空间可以写成：

$$
\mathcal{A}=\{0,1,\dots,2^{18}-1\}
$$

$2^{18}=262144$，所以最大地址是 $2^{18}-1=262143$，十六进制写作 `0x3ffff`。数组右端是地址 262144，也就是 `0x40000`，它不是合法地址，是“末尾之后”的位置。任何读写都必须满足 $a<2^{18}$，任何宽度为 $w$ 的读写还必须满足 $a+w\le2^{18}$。这两个条件看起来只差一个等号，实际差一条边界：最后一字节可以读，末尾之后不能读。

为什么是 $2^{18}$？因为 $256\text{ KiB}=2^8\cdot2^{10}=2^{18}$ 字节。这个数不是随便选的：它足够放下一台教学机器的代码、数据、栈和空闲区，又足够小，整个数组可以静态分配，不需要堆。数组是 `static`，存放在宿主程序的数据段，程序启动时全零，程序结束时消失。Aletheia 不向宿主申请内存，不调用 `malloc`，不在运行时扩大自己。机器的边界在编译时就定死了。

地址是整数，不是宿主指针。宿主的指针是一个 64 位值，可能指向栈、堆、数据段，打印出来是一串宿主地址；Aletheia 的地址是 0 到 262143 的整数，和数组下标一一对应。两者不能混用：把宿主指针存进 32 位地址会截断，把机器地址当宿主指针解引用会崩溃。总装程序从始至终不把机器地址转成宿主指针，也不把宿主指针转成机器地址。打印地址时统一用 `%05x`，读起来是机器地址，不是宿主地址。这个纪律让输出可复现，也让程序不依赖地址空间布局随机化。

地址用 `uint32_t` 存储，虽然 18 位就够。为什么不用 18 位或 24 位？因为 32 位是宿主能直接提供的精确无符号整数类型，运算不会溢出到宿主字长之外，打印也方便。18 位节省不了多少，反而在每次加减时都要手动掩码，增加出错机会。32 位地址的上限是 4294967295，机器大小是 262144，地址检查保证任何合法地址都远小于上限。多出来的位数不浪费内存，`AletheiaAddr` 只是寄存器里的一个值，不是数组里的一格。

地址空间和数组是两层。数组是具体的存储，地址空间是抽象的编号。`aletheia_mem[a]` 是具体访问，`a` 是抽象地址。总装把两层对齐：数组下标就是地址，地址就是下标，中间没有偏移。如果描述符的 `base` 不是 0，数组下标仍然是地址，因为整个数组从 0 开始编号，窗口只是限制可见范围。这个对齐是这台机器的简化，也是它容易检查的原因：读者看到 `0x01000`，既知道它是地址，也知道它对应数组的第 4096 个字节。

### 3.2 描述符

光有一个数组还不够。数组本身不会说自己有多大，也不会说自己从哪个地址开始。函数拿到一个数组，只能靠外部约定知道边界；约定一多，边界就会漂。总装用一个描述符把边界写进类型：

```c
struct AletheiaMem {
    AletheiaAddr base;
    uint32_t size;
};
```

描述符描述一个左闭右开区间：

$$
M=[b,b+s)
$$

其中 $b$ 是 `base`，$s$ 是 `size`。字节 0x01000 属于 $[0x00000,0x40000)$，属于这台机器；字节 0x40000 不属于，因为右端不包含。描述符不是指针，它不保存宿主地址，只保存机器地址和大小。宿主数组的地址由实现自己保管，调用者看不到，也不需要看到。

本章的机器描述符是 `base=0`、`size=262144`，覆盖整个数组。描述符类型本身允许别的窗口：`base=0x01000`、`size=256` 就是一个只覆盖数据区的窗口。窗口不是第二块内存，它仍然是同一块数组的一段。第二卷做分配器时，会把大块切成小块，每个小块都可以用一个窗口描述；第三卷做栈时，会用窗口检查栈指针；第四卷做张量时，会用窗口描述一块权重。窗口换来的是“只能看见这一段”的约束，代价是每次访问多一次边界比较。

有的实现把描述符的起点写成宿主指针 `uint8_t *base`，大小写成 `size_t size`。那是宿主视角：指针指向数组开头，大小是数组字节数。本书不采用这个写法，因为 Aletheia 的地址是机器整数，不是宿主指针；描述符里一旦出现宿主指针，打印、复制、比较都会泄漏宿主地址，第二卷的块头也不容易存进同一块数组。本书用 `AletheiaAddr base`，地址和数组下标同一套编号，描述符可以整体复制，可以写进内存，可以和纸带标注直接比较。宿主数组仍然存在，但它只在 `peek` 和 `poke` 里出现，不出现在接口里。

### 3.3 为什么还要描述符

有人会问：既然只有一块数组，为什么不让所有函数直接用全局数组和全局常量，省掉描述符？答案是，全局数组能表达“内存在哪里”，不能表达“这一次操作允许看多大”。一个函数拿到全局数组，可以读写 0 到 262143 的任何字节；它没有义务只碰自己那一段。描述符把“允许看多大”变成参数，调用者传进来，函数就必须遵守。传一个 256 字节的窗口，函数就只能在这 256 字节里工作；传整台机器，函数才能在整台机器里工作。

描述符还让同一份代码可以服务不同的区域。第九章的 `aletheia_hexdump` 接收一个存储描述符，总装给它再加一个机器描述符：存储窗口负责“这一段”，机器描述符负责“这台机器”。同一份转储代码可以转储数据区，也可以转储栈区，还可以转储第二卷的某一块。函数不关心区域里装的是什么，只关心区域从哪里开始、有多大。总装把这种“区域无关”的思路推到整台机器：`AletheiaMem` 是最大的窗口，也是所有窗口的模板。

描述符是契约，不是装饰。契约写在函数签名里：`const struct AletheiaMem *m`。`const` 表示函数不修改描述符，只读它的边界。调用者可以放心把同一个描述符传给多个检查函数，不必担心其中一个把 `base` 或 `size` 改掉。描述符按值传递也可以，但传指针更省，也更清楚：所有函数看的是同一份边界，不是各自的副本。

### 3.4 边界

一次访问由三个量决定：描述符 $M$、地址 $a$、宽度 $w$。合法的条件是：

$$
b\le a,\qquad a-b\le s-w
$$

第一个条件挡住地址落在区间左边。第二个条件用减法避免加法溢出：$a+w\le b+s$ 等价于 $a-b\le s-w$，但右边只做一次减法，左边要做一次加法，加法可能溢出 32 位。先做减法，再比较，地址再大也不会回绕。

第二个条件还要求 $w\le s$。如果宽度比整个区间还大，$s-w$ 在无符号算术里会下溢成一个巨大的数，任何地址都会被误判为合法。所以检查顺序必须是：先确认 $w>0$，再确认 $w\le s$，再确认 $a\ge b$，最后比较 $a-b$ 和 $s-w$。顺序不是风格，是正确性。第八章已经踩过一次类似的坑：宽度检查没和读写函数对齐，导致 `has` 接受 3 字节而 `read_le` 拒绝 3 字节。这一章让 `store_has` 和 `mem_has` 使用同一组宽度 1、2、4：读写先过 `store_has`，再过 `mem_has`，两层检查的是同一个宽度，不再各写一份。

用一张表看边界：

```text
M = [0x00000, 0x40000)
a=0x3ffff w=1  ok   最后一字节
a=0x3ffff w=4  bad  越过右端
a=0x40000 w=1  bad  末尾之后
a=0x00000 w=4  ok   开头四字节
a=0x3fffc w=4  ok   最后四字节
a=0x3fffd w=4  bad  只差一个字节
```

这张表会在程序的 FAIL 段被重新验证。`read tail` 和 `write tail` 都从 0x3FFFF 读四字节，必须拒绝；`addr overflow` 用一个巨大的下标算地址，必须拒绝。失败不是异常，失败是返回值。所有入口在失败时返回假，不写输出，不修改内存。

## 四、统一读写

### 4.1 字节入口

整台机器只有两个函数直接碰数组：

```c
static bool aletheia_peek_u8(const struct AletheiaMem *m, AletheiaAddr addr,
                              AletheiaByte *out) {
    if (out == NULL || !aletheia_mem_has(m, addr, 1u)) {
        return false;
    }
    *out = aletheia_mem[addr];
    return true;
}
```

```c
static bool aletheia_poke_u8(const struct AletheiaMem *m, AletheiaAddr addr,
                              AletheiaByte value) {
    if (!aletheia_mem_has(m, addr, 1u)) {
        return false;
    }
    aletheia_mem[addr] = value;
    return true;
}
```

`peek_u8` 读一个字节，`poke_u8` 写一个字节。两个函数都先检查，再访问。数组下标只用 `addr`，因为描述符的 `base` 是 0；如果描述符是窗口，地址仍然是全局地址，`peek_u8` 先确认它落在窗口内，再访问全局数组。地址减去 `base` 再加 `base` 抵消了，但检查没有抵消：`addr` 必须落在窗口内。这一层抵消是有意的，它让窗口描述符和整机描述符共用同一套入口。

`out == NULL` 放在最前面。空指针不是地址错误，是调用错误；两种错误都返回假，但检查顺序不同。先查空指针，再查边界，可以避免在空指针上做任何运算。`poke_u8` 没有输出参数，只查边界。两个函数都不打印，不记录日志，不设置全局错误码。错误通过返回值传给调用者，调用者决定是打印、重试还是终止。

为什么只有这两个函数碰数组？因为所有上层都建立在这两个函数上。机器层的整数读写循环调用 `peek_u8` 和 `poke_u8`，存储层再包一层窗口检查；字符串扫描、十六进制转储、记录字段读取最终都落到这两个函数。只要这两个函数的边界正确，上层就不需要重复实现数组访问；只要这两个函数不越界，整台机器就不会越界。这是总装的核心：把信任集中在一个地方，而不是散在九个地方。

### 4.2 小端整数

32 位值在内存里是四个字节，最低有效字节放在最低地址。读的公式是：

$$
v=\sum_{i=0}^{w-1} b_i\,2^{8i}
$$

写的公式是：

$$
b_i=(v\gg8i)\ \&\ 255
$$

`aletheia_store_read_le` 先检查存储窗口，再调用 `aletheia_mem_read_le`；后者检查宽度必须是 1、2、4，再检查区间，再循环拼值。写入走同一条路：`store_write_le` 查窗口，`mem_write_le` 查宽度和区间，再循环拆字节。两个机器层函数都只接受这三种宽度，因为机器的基本整数类型是 8 位、16 位、32 位；3 字节不是标准宽度，允许它会诱导读者写出无法对齐的结构体字段。

宽度检查放在区间检查之前，理由和边界一样：宽度不合法时，`s-w` 可能下溢。先拒绝 3，再算边界，顺序固定。`mem_read_le` 和 `store_read_le` 都检查 `out != NULL`，因为写输出参数之前必须确认指针有效；写入路径没有输出参数，不需要这一条。

小端不是唯一的选择，大端也能定义一套完整读写。选小端是因为这台机器的地址从低到高、字节从低到高，数组下标增长的方向和数值权重增长的方向一致。读者在纸带上看到 `78 56 34 12`，从左往右读是低字节到高字节，从右往左读才是常见的十六进制写法 `0x12345678`。这个“反过来”不是错误，是小端的定义。第八章已经解释过，这一章只需要确认：总装没有换字节序，所有整数仍然走小端。

读写满足往返律：

$$
\operatorname{read}_{w}(\operatorname{write}_{w}(v))=v
$$

对任意 32 位 $v$ 和 $w\in\{1,2,4\}$ 成立。$w=1$ 时只保留最低 8 位，严格说往返的是 $v\bmod256$，不是任意 $v$。程序对 $w=4$ 验证完整值，对 `flags` 的 $w=2$ 验证 3，对 `kind` 和 `tag` 的 $w=1$ 验证 1 和 2，都是截断之后仍然相等的值。这个区别要在验收里写清楚，不能笼统说“所有宽度都往返”。

### 4.3 地址算术

数组元素地址由起点、下标、元素大小决定：

$$
\operatorname{addr}(a_0,i)=a_0+i\cdot e
$$

`aletheia_addr_of` 接收描述符、起点、下标、元素大小，算出地址。下标和元素大小都可能很大，乘积可能超过 32 位，所以中间用 64 位：

```c
delta = (uint64_t)index * elem_size;
if (delta > (uint64_t)(m->size - off)) {
    return false;
}
```

先算 64 位乘积，再和剩余空间比较，最后才转回 32 位。如果先算 32 位乘积，$index\cdot e$ 会回绕，一个巨大的下标可能算出一个小地址，边界检查就会放行。64 位中间值是这类乘法的标准做法：输入是 32 位，乘积最多 64 位，比较在 64 位里做，转换只在确认不溢出之后发生。

函数允许 `base` 等于区间右端，条件是 `index=0`。这时算出的地址是“末尾之后”，可以用于构造尾指针，不能用于读写。C 的指针算术允许尾指针，不允许解引用尾指针；Aletheia 用同样的规则：地址可以算出来，读写会拒绝。`addr_of` 只负责算地址，不负责判断这个地址能不能读写；能不能读写由 `mem_has` 决定。两个函数分工明确，调用者要传对。

程序用两段表验证这条公式。`PTR` 段从起点 0x01000、元素大小 4 出发，用 `ptr_walk` 走 0 到 7 步，再用 `ptr_diff` 反算下标，最后和 `addr_of` 的结果三方对照，八行全部为真。`ARRAY` 段用 `arr_at` 取第 7 个元素，用 `grid_addr` 取 3 行 4 列网格的 `(1,2)`，两个地址也逐项对照。这两张表就是第一卷验收里的 `&arr[i] == &arr[0] + i`，只不过地址是机器地址，不是宿主指针。

### 4.4 结构体偏移

结构体布局由字段顺序、字段大小、字段对齐决定。设第 $i$ 个字段的大小为 $s_i$，对齐为 $g_i$，偏移为 $o_i$。递推是：

$$
o_0=0,\qquad o_i=\left\lceil\frac{o_{i-1}+s_{i-1}}{g_i}\right\rceil g_i
$$

结构体总大小是：

$$
S=\left\lceil\frac{o_{n-1}+s_{n-1}}{G}\right\rceil G
$$

其中 $G=\max_i g_i$ 是最大对齐。每个字段的起点先按自己的对齐向上取整，最后一个字段结束后再按最大对齐向上取整。向上取整用整数写法：

$$
\left\lceil\frac{x}{g}\right\rceil g=\frac{x+g-1}{g}\,g
$$

这个公式只在 $g$ 是 2 的幂时好用，因为除法和乘法可以写成位运算。`aletheia_align_pow2` 要求对齐非零且是 2 的幂，`aletheia_align_up` 用 64 位中间值算向上取整，超过 32 位就拒绝。`aletheia_offset_table` 逐字段调用这两个函数，把偏移写进 `AletheiaField`，最后按最大对齐补齐总大小。

演示记录有五个字段：`id` 是 4 字节、对齐 4；`flags` 是 2 字节、对齐 2；`kind` 是 1 字节、对齐 1；`tag` 是 1 字节、对齐 1；`next` 是 4 字节、对齐 4。手算偏移：

```text
id     o=0  0..3
flags  o=4  4..5
kind   o=6  6
tag    o=7  7
next   o=8  8..11
total  12
```

`id` 之后偏移是 4，正好是 `flags` 的对齐；`flags` 之后偏移是 6，`kind` 对齐 1，不需要补；`kind` 之后是 7，`tag` 对齐 1；`tag` 之后是 8，`next` 对齐 4，正好对齐。最后总大小是 12，12 是 4 的倍数，不需要尾部补齐。程序把这张表和手算表逐项比较，五项偏移和总大小全部相等，`LAYOUT` 段返回真。

注意，这张表是 Aletheia 的布局规则，不是宿主 C 编译器的布局规则。宿主可能给 `uint32_t` 更大的对齐，也可能在结构体末尾加填充；程序不依赖宿主布局，只依赖自己的字段表和递推公式。记录的实际写入用这套偏移：`field_ptr` 把字段下标变成 `AletheiaPtr`，`store_write_u32` 和 `store_write_le` 通过存储窗口写入。`id` 在 0x01020，`flags` 在 0x01024，`kind` 在 0x01026，`tag` 在 0x01027，`next` 在 0x01028。所有写入都通过 `AletheiaMem`，读回的值和写进去的值一致。

### 4.5 字符串与纸带

字符串仍然是一串字节加终止符。总装直接复用第七章的 `AletheiaStr`，容量设成 32 字节。`str_put` 从起点写入文本，再写一个 0；`aletheia_strlen` 从起点扫描，遇到 0 停止，读满容量也停止；`str_eq_text` 把内存里的字节和字面量逐字节比较。上限防止没有终止符的字符串把扫描带出数据区。演示字符串是 `Aletheia`，八个字节，第九个字节是 0，扫描得到长度 8。

纸带仍然由区域和标注组成。总装直接复用第九章的 `AletheiaTape`，标注从区域表生成，不再手写五个 `tape_mark` 调用。标注的地址是机器地址，不是宿主地址；标注的大小是字节数，不是元素数；标注的顺序必须按地址递增。总装用五个标注描述启动图：`boot`、`code`、`data`、`stack`、`free`。五个标注覆盖 4928 字节，剩下 257216 字节是空隙。空隙不是浪费，是留给第二卷分配器、第三卷栈帧和第四卷权重的空间。

纸带层还提供按地址查找。给定一个机器地址，顺序扫描标注，找到第一个满足 $a\in[m.\text{addr},m.\text{addr}+m.\text{size})$ 的标注，返回它的下标和偏移。因为标注不重叠且按地址排序，找到的第一个就是唯一一个。找不到就是空隙。启动图、数据区和栈区的地址都能查到归属；0x00040 和 0x3E000 落在空隙里，查找返回假，程序打印 `(gap)`。

## 五、总装的布局

### 5.1 启动、代码、数据、栈、空闲

总装给机器划分五段：

```text
boot   0x00000..0x0003f    64
code   0x00100..0x002ff   512
data   0x01000..0x010ff   256
stack  0x3f000..0x3f1ff   512
free   0x3f200..0x3ffff  3584
```

启动区从 0 开始，64 字节，放八个字节的签名 `ALETHEIA`。代码区从 0x00100 开始，512 字节，留给第三卷的指令。数据区从 0x01000 开始，256 字节，放演示数组、记录和字符串。栈区从 0x3F000 开始，512 字节，栈顶在 0x3F200，栈向下增长。空闲区从 0x3F200 开始，3584 字节，紧接栈区，留给后面的分配器。

这些地址不是随手写的。启动区放在最低地址，因为机器上电时从 0 开始取指。代码区放在 0x00100，和启动区之间留 192 字节，给启动代码和中断向量留余地。数据区放在 0x01000，和代码区之间留 3328 字节，给代码增长留余地。栈区放在 0x3F000，靠近机器顶端，栈向下增长时不会撞到数据区。空闲区接在栈区后面，一直到 0x3FFFF，是整块内存里最后一段连续空间。

每段的终点是起点加大小：

$$
\operatorname{end}(r)=r.\text{addr}+r.\text{size}
$$

启动区终点 $0x00000+0x40=0x00040$，代码区终点 $0x00100+0x200=0x00300$，数据区终点 $0x01000+0x100=0x01100$，栈区终点 $0x3F000+0x200=0x3F200$，空闲区终点 $0x3F200+0xE00=0x40000$。五个终点都在 $[0,0x40000]$ 内，最后一个正好等于机器右端。空闲区之所以是 0xE00 字节，是因为 $0x40000-0x3F200=0xE00=3584$。这个减法不是估算，是总装时算出来的。

### 5.2 标注

五个标注按地址顺序追加。`tape_mark` 是追加式的，每次追加都检查新标注的起点不小于上一个标注的终点。启动区终点 0x40 小于代码区起点 0x100，可以追加；代码区终点 0x300 小于数据区起点 0x1000，可以追加；数据区终点 0x1100 小于栈区起点 0x3F000，可以追加；栈区终点 0x3F200 等于空闲区起点，也可以追加。五个标注排成一行，没有重叠。

标注表打印五列：标签、起点、终点、大小。标签是 ASCII 短名，最长五个字符；起点和终点是五位十六进制；大小是十进制。表的每一行都能和启动图对上。`boot` 的终点 0x00040 和 `code` 的起点 0x00100 之间有一段空隙；`code` 的终点 0x00300 和 `data` 的起点 0x01000 之间有一大段空隙；`data` 的终点 0x01100 和 `stack` 的起点 0x3F000 之间有一段更大的空隙。这些空隙没有标注，也没有内容，查找时返回假。

覆盖统计把五个标注的大小加起来：

$$
C=64+512+256+512+3584=4928
$$

空隙是：

$$
G=262144-4928=257216
$$

两者相加正好是机器大小：

$$
C+G=262144
$$

这个等式是纸带层的不变量。标注不重叠，所以大小可以直接相加；如果重叠，相加会把同一字节算两次，等式就不成立。`tape_ok` 在统计之前先检查排序和不重叠，`tape_cover` 在统计之前再检查一次。两次检查看起来重复，实际上是两层保护：一层防止坏表进入统计，一层防止调用者绕过检查直接调用统计。

### 5.3 检查

总装程序有十四段检查：`MARKS`、`FIND`、`PAPER TAPE`、`PTR`、`ARRAY`、`LAYOUT`、`RECORD`、`STRING`、`BOOT`、`STACK`、`SPAN`、`HEXDUMP`、`COVER`、`FAIL`。每段打印自己的数据，返回一个布尔值；`main` 收集十四个布尔值，再加上描述符自身的 `mem`，最后打印 `SUMMARY`。

`MARKS` 检查标注表本身：数量、顺序、大小、标签。`FIND` 检查地址查找：区内地址返回正确的标签和偏移，空隙返回假。`PAPER TAPE` 检查八个 32 位值的字节、无符号解释和有符号解释。`PTR` 检查 `ptr_walk`、`ptr_diff`、`addr_of` 三方算出的八个元素地址是否一致。`ARRAY` 检查 12 字节数组的和、第 7 个元素的地址、3 行 4 列网格 `(1,2)` 的地址。`LAYOUT` 检查五个字段偏移和总大小是否等于手算表。`RECORD` 检查写入的五个字段能否按偏移读回，`struct_at` 能否算出下一个记录实例。`STRING` 检查长度、内容和逐字节比较。`BOOT` 检查启动签名。`STACK` 检查栈顶两个字。`SPAN` 检查五段区间的有效性、顺序、不重叠、包含关系和一次 8 字节复制。`HEXDUMP` 检查五行十六进制转储。`COVER` 检查覆盖等式。`FAIL` 检查十四种非法操作是否被拒绝。

十四段检查不是十四个独立的程序，是同一台机器的十四个侧面。`MARKS` 和 `FIND` 看纸带，`PAPER TAPE` 和 `HEXDUMP` 看字节，`PTR` 和 `ARRAY` 看地址算术，`LAYOUT` 和 `RECORD` 看结构体，`STRING` 看终止符，`BOOT` 和 `STACK` 看启动图和栈，`SPAN` 看区间代数，`COVER` 看总量，`FAIL` 看边界。每一段都通过 `AletheiaMem` 访问内存，没有一段绕过描述符直接碰数组。

汇总表打印十五个布尔值：`mem`、`marks`、`find`、`paper`、`ptr`、`array`、`layout`、`record`、`string`、`boot`、`stack`、`span`、`hexdump`、`cover`、`fail`。十五个全为真，程序打印 `ALETHEIA MEM OK` 并返回 0；任何一个为假，程序打印 `ALETHEIA MEM BROKEN` 并返回 1。返回码和最后一行一致，脚本可以直接用返回码判断，不必解析文本。

### 5.4 第一卷公式汇总

总装也是公式的总装。第一卷九个零件，每个零件有一个核心公式：

| 章 | 零件 | 公式 |
| --- | --- | --- |
| 1 | 字节 | $\mathcal{M}:A\rightharpoonup\mathbb{B}$ |
| 2 | 区间 | $[a,a+s)$ |
| 3 | 补码 | $-x\equiv2^n-x\pmod{2^n}$ |
| 4 | 指针 | $\operatorname{addr}(p+k)=\operatorname{addr}(p)+k\cdot s$ |
| 5 | 数组 | $\operatorname{addr}(a,i)=a+i\cdot s$ |
| 6 | 结构体 | $o_i=\lceil(o_{i-1}+s_{i-1})/g_i\rceil g_i$ |
| 7 | 字符串 | $s=\text{bytes before }0$ |
| 8 | 小端 | $v=\sum b_i2^{8i}$ |
| 9 | 纸带 | $C+G=S$ |

这张表不是装饰。每一个公式都能落到一行 C，每一行 C 都能在总装程序里找到对应的检查。字节公式落到 `peek_u8`，区间公式落到 `mem_has`，补码公式落到 `signed32`，指针公式落到 `ptr_walk`，数组公式落到 `arr_at`，结构体公式落到 `offset_table`，字符串公式落到 `check_string`，小端公式落到 `mem_read_le`，纸带公式落到 `tape_cover`。公式和代码不是两套东西，是同一件事的两种写法。

## 六、把九个零件装成一台机器

### 6.1 装法

总装不是把九个程序粘在一起，是让九个类型指向同一个描述符。层次如下：

```text
main
  AletheiaTape     纸带：整机目录与标注
  AletheiaStore    存储：一段有窗口的字节
  AletheiaStruct   结构：字段偏移表
  AletheiaStr      字符串：容量和终止符
  AletheiaArr      数组：起点、元素大小、个数
  AletheiaPtr      指针：起点、元素大小
  AletheiaSpan     区间：起点、大小
        |
    AletheiaMem    机器：整块数组的边界
        |
  peek_u8 / poke_u8
        |
  aletheia_mem[262144]
```

每种视图都保留前九章的结构体定义，只把函数签名改成接收 `const struct AletheiaMem *m`。迁移表如下：

| 章 | 类型 | 总装里的构造与检查 |
| --- | --- | --- |
| 2 | `AletheiaSpan` | `span_new`、`span_ok`、`span_end`、`span_contains`、`span_overlap`、`span_fill`、`span_copy` |
| 4 | `AletheiaPtr` | `ptr_make`、`ptr_ok`、`ptr_walk`、`ptr_diff`、`ptr_read_u8`、`ptr_write_u8` |
| 5 | `AletheiaArr` | `arr_ok`、`arr_make`、`arr_at`、`arr_addr`、`arr_sum`、`grid_index`、`grid_addr` |
| 6 | `AletheiaFieldSpec`、`AletheiaField`、`AletheiaStruct` | `align_pow2`、`align_up`、`offset_table`、`struct_ok`、`field_ptr`、`struct_at` |
| 7 | `AletheiaStr` | `str_ok`、`str_make`、`str_byte`、`str_poke`、`aletheia_strlen`、`str_put`、`str_eq_text`、`str_print` |
| 8 | `AletheiaStore` | `store_ok`、`store_make`、`store_has`、`store_span`、`store_read_le`、`store_write_le`、`store_read_u32`、`store_write_u32` |
| 9 | `AletheiaMark`、`AletheiaTape` | `label_ok`、`label_copy`、`tape_ok`、`tape_make`、`tape_mark`、`tape_find`、`tape_cover`、`tape_store` |

迁移有三条硬规矩。

第一条，所有视图函数的第一个参数是机器描述符，视图自己不保存第二块数组。`AletheiaSpan`、`AletheiaPtr`、`AletheiaArr`、`AletheiaStruct`、`AletheiaStr`、`AletheiaStore`、`AletheiaTape` 都只保存地址、大小、个数、偏移这类整数，不保存宿主指针，也不保存数组的拷贝。视图是看内存的眼镜，不是内存本身。

第二条，同名类型只保留一个定义。第六章的 `AletheiaField` 是 `{offset, size, align}`，总装原样使用；字段名 `id`、`flags`、`kind`、`tag`、`next` 不放进类型，而是放在 `check_layout` 里的 `names` 表。这样同一个 `AletheiaStruct` 可以描述任意记录，名字只在打印时出现。上一版总装把 `AletheiaField` 写成 `{name, size, align}`，和第六章同名不同义，读者把两章的代码接起来就会撞类型；这一版删掉了那个定义。

第三条，同名函数加前缀分层。机器层叫 `mem_read_le`、`mem_write_le`，存储层叫 `store_read_le`、`store_write_le`。两层都叫 `read_le` 会让读者分不清手里的是哪一层；加了前缀，调用处一眼就能看出检查了几次窗口。

### 6.2 一张表管五个区域

总装只有一张区域表：

```c
static const struct AletheiaRegion aletheia_regions[REGION_COUNT] = {
    { "boot",  { 0x00000u, 0x0040u } },
    { "code",  { 0x00100u, 0x0200u } },
    { "data",  { 0x01000u, 0x0100u } },
    { "stack", { 0x3f000u, 0x0200u } },
    { "free",  { 0x3f200u, 0x0e00u } }
};
```

头部的启动图、纸带的五个标注、`SPAN` 段的五段区间、启动区清零、数据区清零、栈区清零、栈顶字的地址，全部从这张表取值。改一个区域的起点或大小，只需要改这一行，不会出现“头部写 0x3F000、栈检查写 0x3EFF8”这类漂移。前九章各写各的常量，总装把常量收成一张表，这是“状态管理变成一块铁板”的具体做法。

区域表是 `static const`，编译后就固定，运行时不修改。`REGION_BOOT` 到 `REGION_FREE` 是下标，不是地址；代码里需要启动区时写 `aletheia_regions[REGION_BOOT].span.addr`，不写 `0x00000u`。唯一的例外是 `check_find` 和 `check_fail` 里的探测地址，那些地址是用来测试查找和越界的输入，不是区域定义本身。

### 6.3 唯一访问路径

整个程序只有 `aletheia_peek_u8` 和 `aletheia_poke_u8` 两处下标 `aletheia_mem`。其余函数都通过描述符调用这两个入口。完整路径是：

```text
tape_mark / tape_find / tape_cover
  -> tape_ok
    -> store_make
      -> mem_has
store_read_u32
  -> store_has
    -> mem_has
  -> mem_read_le
    -> peek_u8
      -> mem_has
        -> aletheia_mem[addr]
```

路径有三层边界检查：存储层检查窗口，机器层检查整台机器，字节层检查单个地址。三层检查的不是同一件事：存储层回答“这个地址属于这段记录吗”，机器层回答“这个地址属于这台机器吗”，字节层回答“这个字节的地址合法吗”。三个问题都回答是，访问才发生。

这条路径也解释了为什么 `AletheiaStore` 不是多余的。纸带覆盖整台机器，它的存储窗口就是 `[0, 262144)`；记录只覆盖 12 字节，它的窗口是 `[0x01020, 0x0102C)`。同一个 `store_read_u32` 既能读纸带，也能读记录，区别只在传进去的窗口。窗口把“允许看多大”变成参数，这正是第三章描述符的想法，第八章把它做成了类型，第十章把它接到了整台机器上。

### 6.4 七种视图

**区间。** `AletheiaSpan` 是最薄的一层，只有起点和大小。`span_ok` 调用 `mem_has(m, s.addr, s.size)`；`span_end` 在有效的前提下算起点加大小；`span_contains` 用减法判断内区间是否落在外区间里；`span_overlap` 用两个终点判断是否相交。`SPAN` 段先验证五段区域都在机器内、按地址排序、互不重叠，再把启动签名的前八个字节复制到数据区的 8 字节暂存区。复制之前先清零，复制之后逐字节读回，确认 `span_copy` 没有碰错字节。

**指针。** `AletheiaPtr` 是起点加元素大小。`ptr_make` 要求整个元素落在机器内；`ptr_walk` 用 64 位中间值算 `addr + k * elem_size`，再检查结果加元素大小不超过机器右端；`ptr_diff` 要求两个指针元素大小相同、差值能整除元素大小、商在 `int32_t` 范围内。`PTR` 段对每个下标做三件事：`ptr_walk` 从基指针走出第 $i$ 个元素，`ptr_diff` 把第 $i$ 个元素减回基指针，`addr_of` 用下标直接算地址，三者必须相等。

**数组。** `AletheiaArr` 是指针加个数。`arr_ok` 用 64 位乘法算 `elem_size * count`，先确认总大小不超过机器，再确认起点加总大小不越过机器右端。`arr_at` 先用 `ptr_make` 造基指针，再用 `ptr_walk` 走下标，所以数组的地址计算和指针的地址计算是同一条代码路径，不是两套公式。`arr_sum` 只接受元素大小为 1 的字节数组，用 `arr_at` 取每个元素，再用 `ptr_read_u8` 读值。`ARRAY` 段验证 12 个字节 1 到 12 的和是 78，第 7 个元素（下标 7，值 8）在 `0x01067`，3 行 4 列网格的 `(1,2)` 在 `0x01066`。

**结构体。** 输入是 `AletheiaFieldSpec` 数组，每项只有大小和对齐；输出是 `AletheiaStruct`，里面是 `AletheiaField` 数组，每项有偏移、大小、对齐。`offset_table` 按 6.1 的递推逐字段对齐，最后按最大对齐补齐总大小，并确认整块结构落在机器内。`struct_ok` 反过来检查：首字段偏移为 0，每个偏移按自己的对齐，字段之间不重叠，总大小按最大对齐。`field_ptr` 把字段下标变成 `AletheiaPtr`，字段大小就是元素大小；`struct_at` 用 `addr + i * size` 算第 $i$ 个实例，并确认整个实例不越过机器右端。`LAYOUT` 段验证五个字段的偏移 0、4、6、7、8 和总大小 12；`RECORD` 段用 `field_ptr` 加 `store_write_*` 写入，再用同样的路径读回，最后用 `struct_at` 算出 0x01020 和 0x0102C 两个实例地址。

**字符串。** `AletheiaStr` 是起点加容量。`str_make` 要求整段容量落在机器内；`str_byte` 把第 $i$ 个字节包成元素大小为 1 的 `AletheiaPtr`，再用 `ptr_read_u8` 读；`str_poke` 走同一条路写。`aletheia_strlen` 从基指针逐字节扫描，遇到 0 返回下标，读满容量返回假；`str_put` 先量文本长度，确认小于容量，再逐字节写入，最后写 0；`str_eq_text` 先求长度，再逐字节比较文本，最后确认字面量也在同一位置结束；`str_print` 把每个字节交给 `putchar`，没有终止符时打印标记。`STRING` 段打印 `Aletheia`，长度 8，并用 `str_eq_text` 和字面量比较。

**存储。** `AletheiaStore` 是起点加窗口大小。`store_ok` 要求窗口落在机器内；`store_has` 检查宽度是 1、2、4，地址在窗口内，且宽度放得下；`store_span` 检查一段连续字节在窗口内；`store_read_le` 和 `store_write_le` 先过 `store_has`，再调用机器层的 `mem_read_le` 和 `mem_write_le`。`PAPER TAPE` 用覆盖整机的存储窗口读八个 32 位值；`RECORD` 用 12 字节的存储窗口读写字段；`STACK` 用 `tape_store` 拿到整机窗口，再从栈顶两个字读出 42 和 0x00100；`HEXDUMP` 用数据区窗口转储前 80 字节。

**纸带。** `AletheiaTape` 是存储窗口加标注数组。`tape_ok` 先确认整个纸带能做成存储窗口，再逐条检查标注大小、标签、顺序和边界；`tape_mark` 是追加式，要求新标注的起点不小于上一条的终点；`tape_find` 顺序扫描，返回第一个包含目标地址的标注下标和偏移；`tape_cover` 把标注大小相加，用纸带大小减去总和得到空隙；`tape_store` 把纸带变成一个 `AletheiaStore`，交给 `hexdump`、`PAPER TAPE` 和 `STACK` 使用。`MARKS`、`FIND`、`COVER` 三段分别检查标注表、地址查找和覆盖等式。

### 6.5 构造顺序

`main` 的构造顺序是固定的：

1. `mem_make` 造整机描述符，失败就直接打印 `BROKEN` 并返回。
2. `fill_boot` 把启动区清零，再写八个字节的签名。
3. `fill_data` 把数据区清零，再写八个 32 位值和 12 个字节的数组。
4. `fill_stack` 把栈区清零，再从栈区末尾倒着写两个 32 位值。
5. `build_record` 用字段规格表算偏移，`fill_record` 用字段指针和存储窗口写五个字段。
6. `build_string` 在数据区造一个容量 32 的字符串并写入 `Aletheia`。
7. `build_tape` 造整机纸带，按区域表追加五个标注。

顺序不能乱。`fill_data` 必须先把整个数据区清零，否则记录和字符串之间的填充字节可能保留上一次运行的旧值，十六进制转储就不可复现。`build_record` 必须在 `fill_record` 之前，因为写入需要字段偏移。`build_tape` 必须在区域表可用之后，因为它要读五段区域的起点和大小；它不依赖数据区的内容，放在最后只是为了让构造阶段和检查阶段分开。

七步全部成功，才打印头部并开始十四段检查。任何一步失败，程序打印 `ALETHEIA MEM BROKEN` 并返回 1。构造失败和检查失败是两种失败：构造失败时连一台完整的机器都没有，后续检查没有意义；检查失败时机器还在，只是某一种看法不同意，程序会继续跑完剩下的段，让读者看到坏的范围。

### 6.6 失败也是返回值

`FAIL` 段在每一层都放一个非法输入：

| 层 | 非法输入 | 期望 |
| --- | --- | --- |
| 机器 | 描述符 `[0x3F000, 0x3F000+0x2000)` 越过机器右端 | `mem_make` 拒绝 |
| 存储 | 同样的窗口做成 `AletheiaStore` | `store_make` 拒绝 |
| 存储 | 从 `0x3FFFF` 读 4 字节 | `store_read_u32` 拒绝 |
| 存储 | 往 `0x3FFFF` 写 4 字节 | `store_write_u32` 拒绝 |
| 存储 | 宽度 3 | `store_read_le` 拒绝 |
| 机器 | 下标 `0x40000000`、元素大小 4 | `addr_of` 拒绝 |
| 指针 | 从数据区走 `0x40000000` 步 | `ptr_walk` 拒绝 |
| 指针 | 两个元素大小相同但对不齐的指针求差 | `ptr_diff` 拒绝 |
| 数组 | 元素大小 4、个数 `0x40000000` | `arr_make` 拒绝 |
| 数组 | 12 个元素的数组取下标 12 | `arr_at` 拒绝 |
| 结构体 | 对齐 3 | `offset_table` 拒绝 |
| 结构体 | 手工构造对齐为 3 的字段表 | `struct_ok` 拒绝 |
| 字符串 | 起点 `0x3FFFF`、容量 4 | `str_make` 拒绝 |
| 纸带 | 第二条标注压在第一条上 | `tape_mark` 拒绝 |

十四种全部拒绝，`FAIL` 段返回真。这里没有异常、没有 `longjmp`、没有全局错误码；每一层用返回值报告失败，调用者用 `&&` 串起来。失败时不修改内存，不打印半行数据，不把坏状态留给下一层。

## 七、完整程序

把下面的代码保存为 `aletheia_ch10.c`，用 C99 编译：

```bash
cc -std=c99 -O2 -Wall -Wextra -pedantic aletheia_ch10.c -o aletheia_ch10
```

程序一共 1816 行，只包含 `<stdbool.h>`、`<stddef.h>`、`<stdint.h>`、`<stdio.h>` 四个头文件。它不使用 `malloc`，不使用宿主指针算术，不依赖任何外部文件。

```c
/* aletheia_ch10.c */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define ALETHEIA_SIZE ((uint32_t)256 * 1024)
#define ALETHEIA_MAX_MARKS 8u
#define ALETHEIA_MAX_FIELDS 8u
#define ALETHEIA_LABEL 12u

typedef uint8_t AletheiaByte;
typedef uint32_t AletheiaAddr;

struct AletheiaSpan {
    AletheiaAddr addr;
    uint32_t size;
};

struct AletheiaPtr {
    AletheiaAddr addr;
    uint32_t elem_size;
};

struct AletheiaArr {
    AletheiaAddr addr;
    uint32_t elem_size;
    uint32_t count;
};

struct AletheiaFieldSpec {
    uint32_t size;
    uint32_t align;
};

struct AletheiaField {
    uint32_t offset;
    uint32_t size;
    uint32_t align;
};

struct AletheiaStruct {
    AletheiaAddr addr;
    uint32_t size;
    uint32_t field_count;
    struct AletheiaField fields[ALETHEIA_MAX_FIELDS];
};

struct AletheiaStr {
    AletheiaAddr addr;
    uint32_t capacity;
};

struct AletheiaStore {
    AletheiaAddr base;
    uint32_t size;
};

struct AletheiaMark {
    AletheiaAddr addr;
    uint32_t size;
    char label[ALETHEIA_LABEL];
};

struct AletheiaTape {
    AletheiaAddr base;
    uint32_t size;
    uint32_t mark_count;
    struct AletheiaMark marks[ALETHEIA_MAX_MARKS];
};

struct AletheiaMem {
    AletheiaAddr base;
    uint32_t size;
};

struct AletheiaRegion {
    const char *label;
    struct AletheiaSpan span;
};

enum {
    REGION_BOOT,
    REGION_CODE,
    REGION_DATA,
    REGION_STACK,
    REGION_FREE,
    REGION_COUNT
};

static const struct AletheiaRegion aletheia_regions[REGION_COUNT] = {
    { "boot",  { 0x00000u, 0x0040u } },
    { "code",  { 0x00100u, 0x0200u } },
    { "data",  { 0x01000u, 0x0100u } },
    { "stack", { 0x3f000u, 0x0200u } },
    { "free",  { 0x3f200u, 0x0e00u } }
};

static AletheiaByte aletheia_mem[ALETHEIA_SIZE];

static bool aletheia_mem_ok(const struct AletheiaMem *m) {
    if (m == NULL || m->size == 0u) {
        return false;
    }
    if (m->base > ALETHEIA_SIZE) {
        return false;
    }
    return m->size <= ALETHEIA_SIZE - m->base;
}

static bool aletheia_mem_make(struct AletheiaMem *m, AletheiaAddr base,
                              uint32_t size) {
    struct AletheiaMem trial;
    if (m == NULL) {
        return false;
    }
    trial.base = base;
    trial.size = size;
    if (!aletheia_mem_ok(&trial)) {
        return false;
    }
    *m = trial;
    return true;
}

static bool aletheia_mem_has(const struct AletheiaMem *m, AletheiaAddr addr,
                             uint32_t width) {
    uint32_t off;
    if (!aletheia_mem_ok(m) || width == 0u || width > m->size) {
        return false;
    }
    if (addr < m->base) {
        return false;
    }
    off = addr - m->base;
    return off <= m->size - width;
}

static bool aletheia_peek_u8(const struct AletheiaMem *m, AletheiaAddr addr,
                             AletheiaByte *out) {
    if (out == NULL || !aletheia_mem_has(m, addr, 1u)) {
        return false;
    }
    *out = aletheia_mem[addr];
    return true;
}

static bool aletheia_poke_u8(const struct AletheiaMem *m, AletheiaAddr addr,
                             AletheiaByte value) {
    if (!aletheia_mem_has(m, addr, 1u)) {
        return false;
    }
    aletheia_mem[addr] = value;
    return true;
}

static bool aletheia_mem_read_le(const struct AletheiaMem *m,
                                 AletheiaAddr addr, uint32_t width,
                                 uint32_t *out) {
    uint32_t value = 0u;
    uint32_t i;
    if (out == NULL || (width != 1u && width != 2u && width != 4u)) {
        return false;
    }
    if (!aletheia_mem_has(m, addr, width)) {
        return false;
    }
    for (i = 0u; i < width; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_peek_u8(m, addr + i, &b)) {
            return false;
        }
        value |= (uint32_t)b << (8u * i);
    }
    *out = value;
    return true;
}

static bool aletheia_mem_write_le(const struct AletheiaMem *m,
                                  AletheiaAddr addr, uint32_t width,
                                  uint32_t value) {
    uint32_t i;
    if (width != 1u && width != 2u && width != 4u) {
        return false;
    }
    if (!aletheia_mem_has(m, addr, width)) {
        return false;
    }
    for (i = 0u; i < width; ++i) {
        AletheiaByte b = (AletheiaByte)((value >> (8u * i)) & 0xffu);
        if (!aletheia_poke_u8(m, addr + i, b)) {
            return false;
        }
    }
    return true;
}

static bool aletheia_write_u32(const struct AletheiaMem *m, AletheiaAddr addr,
                               uint32_t value) {
    return aletheia_mem_write_le(m, addr, 4u, value);
}

static bool aletheia_addr_of(const struct AletheiaMem *m, AletheiaAddr base,
                             uint32_t index, uint32_t elem_size,
                             AletheiaAddr *out) {
    uint32_t off;
    uint64_t delta;
    if (out == NULL || elem_size == 0u || !aletheia_mem_ok(m)) {
        return false;
    }
    if (base < m->base) {
        return false;
    }
    off = base - m->base;
    if (off > m->size) {
        return false;
    }
    delta = (uint64_t)index * elem_size;
    if (delta > (uint64_t)(m->size - off)) {
        return false;
    }
    *out = base + (AletheiaAddr)delta;
    return true;
}

static struct AletheiaSpan aletheia_span_new(AletheiaAddr addr,
                                             uint32_t size) {
    struct AletheiaSpan s;
    s.addr = addr;
    s.size = size;
    return s;
}

static bool aletheia_span_ok(const struct AletheiaMem *m,
                             struct AletheiaSpan s) {
    return s.size != 0u && aletheia_mem_has(m, s.addr, s.size);
}

static bool aletheia_span_end(const struct AletheiaMem *m,
                              struct AletheiaSpan s, AletheiaAddr *out) {
    if (out == NULL || !aletheia_span_ok(m, s)) {
        return false;
    }
    *out = s.addr + s.size;
    return true;
}

static bool aletheia_span_contains(const struct AletheiaMem *m,
                                   struct AletheiaSpan outer,
                                   struct AletheiaSpan inner) {
    uint32_t delta;
    if (!aletheia_span_ok(m, outer) || !aletheia_span_ok(m, inner)) {
        return false;
    }
    if (inner.addr < outer.addr) {
        return false;
    }
    delta = inner.addr - outer.addr;
    if (delta > outer.size) {
        return false;
    }
    return inner.size <= outer.size - delta;
}

static bool aletheia_span_overlap(const struct AletheiaMem *m,
                                  struct AletheiaSpan a,
                                  struct AletheiaSpan b) {
    AletheiaAddr a_end = 0u;
    AletheiaAddr b_end = 0u;
    if (!aletheia_span_end(m, a, &a_end) ||
        !aletheia_span_end(m, b, &b_end)) {
        return false;
    }
    return a.addr < b_end && b.addr < a_end;
}

static bool aletheia_span_fill(const struct AletheiaMem *m,
                               struct AletheiaSpan s, AletheiaByte value) {
    uint32_t i;
    if (!aletheia_span_ok(m, s)) {
        return false;
    }
    for (i = 0u; i < s.size; ++i) {
        if (!aletheia_poke_u8(m, s.addr + i, value)) {
            return false;
        }
    }
    return true;
}

static bool aletheia_span_copy(const struct AletheiaMem *m,
                               struct AletheiaSpan dst,
                               struct AletheiaSpan src) {
    uint32_t i;
    if (!aletheia_span_ok(m, dst) || !aletheia_span_ok(m, src)) {
        return false;
    }
    if (dst.size != src.size || aletheia_span_overlap(m, dst, src)) {
        return false;
    }
    for (i = 0u; i < src.size; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_peek_u8(m, src.addr + i, &b) ||
            !aletheia_poke_u8(m, dst.addr + i, b)) {
            return false;
        }
    }
    return true;
}

static bool aletheia_ptr_make(const struct AletheiaMem *m, AletheiaAddr addr,
                              uint32_t elem_size,
                              struct AletheiaPtr *out) {
    if (out == NULL || elem_size == 0u || !aletheia_mem_ok(m)) {
        return false;
    }
    if (!aletheia_mem_has(m, addr, elem_size)) {
        return false;
    }
    out->addr = addr;
    out->elem_size = elem_size;
    return true;
}

static bool aletheia_ptr_ok(const struct AletheiaMem *m,
                            struct AletheiaPtr p) {
    return p.elem_size != 0u && aletheia_mem_has(m, p.addr, p.elem_size);
}

static bool aletheia_ptr_walk(const struct AletheiaMem *m,
                              struct AletheiaPtr p, int32_t k,
                              struct AletheiaPtr *out) {
    int64_t delta;
    int64_t next;
    int64_t limit;
    if (out == NULL || !aletheia_ptr_ok(m, p)) {
        return false;
    }
    delta = (int64_t)k * (int64_t)p.elem_size;
    next = (int64_t)p.addr + delta;
    if (next < (int64_t)m->base) {
        return false;
    }
    limit = (int64_t)m->base + (int64_t)m->size;
    if (next + (int64_t)p.elem_size > limit) {
        return false;
    }
    out->addr = (AletheiaAddr)next;
    out->elem_size = p.elem_size;
    return true;
}

static bool aletheia_ptr_diff(const struct AletheiaMem *m,
                              struct AletheiaPtr a, struct AletheiaPtr b,
                              int32_t *out) {
    int64_t diff;
    int64_t quotient;
    if (out == NULL || a.elem_size != b.elem_size) {
        return false;
    }
    if (!aletheia_ptr_ok(m, a) || !aletheia_ptr_ok(m, b)) {
        return false;
    }
    diff = (int64_t)a.addr - (int64_t)b.addr;
    if (diff % (int64_t)a.elem_size != 0) {
        return false;
    }
    quotient = diff / (int64_t)a.elem_size;
    if (quotient < (int64_t)INT32_MIN ||
        quotient > (int64_t)INT32_MAX) {
        return false;
    }
    *out = (int32_t)quotient;
    return true;
}

static bool aletheia_ptr_read_u8(const struct AletheiaMem *m,
                                 struct AletheiaPtr p, AletheiaByte *out) {
    if (out == NULL || !aletheia_ptr_ok(m, p)) {
        return false;
    }
    return aletheia_peek_u8(m, p.addr, out);
}

static bool aletheia_ptr_write_u8(const struct AletheiaMem *m,
                                  struct AletheiaPtr p,
                                  AletheiaByte value) {
    if (!aletheia_ptr_ok(m, p)) {
        return false;
    }
    return aletheia_poke_u8(m, p.addr, value);
}

static bool aletheia_arr_ok(const struct AletheiaMem *m,
                            struct AletheiaArr a) {
    uint64_t total;
    if (!aletheia_mem_ok(m) || a.elem_size == 0u || a.count == 0u) {
        return false;
    }
    total = (uint64_t)a.elem_size * (uint64_t)a.count;
    if (total > (uint64_t)m->size) {
        return false;
    }
    if (a.addr < m->base) {
        return false;
    }
    return (uint64_t)(a.addr - m->base) <=
           (uint64_t)m->size - total;
}

static bool aletheia_arr_make(const struct AletheiaMem *m, AletheiaAddr addr,
                              uint32_t elem_size, uint32_t count,
                              struct AletheiaArr *out) {
    struct AletheiaArr trial;
    if (out == NULL) {
        return false;
    }
    trial.addr = addr;
    trial.elem_size = elem_size;
    trial.count = count;
    if (!aletheia_arr_ok(m, trial)) {
        return false;
    }
    *out = trial;
    return true;
}

static bool aletheia_arr_at(const struct AletheiaMem *m,
                            struct AletheiaArr a, uint32_t i,
                            struct AletheiaPtr *out) {
    struct AletheiaPtr base;
    if (out == NULL || !aletheia_arr_ok(m, a) || i >= a.count) {
        return false;
    }
    if (!aletheia_ptr_make(m, a.addr, a.elem_size, &base)) {
        return false;
    }
    return aletheia_ptr_walk(m, base, (int32_t)i, out);
}

static bool aletheia_arr_addr(const struct AletheiaMem *m,
                              struct AletheiaArr a, uint32_t i,
                              AletheiaAddr *out) {
    struct AletheiaPtr p;
    if (out == NULL || !aletheia_arr_at(m, a, i, &p)) {
        return false;
    }
    *out = p.addr;
    return true;
}

static bool aletheia_arr_sum(const struct AletheiaMem *m,
                             struct AletheiaArr a, uint32_t *out) {
    uint32_t sum = 0u;
    uint32_t i;
    if (out == NULL || !aletheia_arr_ok(m, a) || a.elem_size != 1u) {
        return false;
    }
    for (i = 0u; i < a.count; ++i) {
        struct AletheiaPtr p;
        AletheiaByte v = 0u;
        if (!aletheia_arr_at(m, a, i, &p) ||
            !aletheia_ptr_read_u8(m, p, &v)) {
            return false;
        }
        sum += (uint32_t)v;
    }
    *out = sum;
    return true;
}

static bool aletheia_grid_index(uint32_t cols, uint32_t i, uint32_t j,
                                uint32_t *out) {
    uint64_t index;
    if (out == NULL || cols == 0u) {
        return false;
    }
    index = (uint64_t)i * (uint64_t)cols + (uint64_t)j;
    if (index > (uint64_t)UINT32_MAX) {
        return false;
    }
    *out = (uint32_t)index;
    return true;
}

static bool aletheia_grid_addr(const struct AletheiaMem *m,
                               AletheiaAddr base, uint32_t elem_size,
                               uint32_t rows, uint32_t cols,
                               uint32_t i, uint32_t j,
                               AletheiaAddr *out) {
    struct AletheiaArr a;
    struct AletheiaPtr p;
    uint64_t total;
    uint32_t index;
    if (out == NULL || rows == 0u || cols == 0u ||
        i >= rows || j >= cols) {
        return false;
    }
    total = (uint64_t)rows * (uint64_t)cols;
    if (total > (uint64_t)UINT32_MAX) {
        return false;
    }
    if (!aletheia_arr_make(m, base, elem_size, (uint32_t)total, &a)) {
        return false;
    }
    if (!aletheia_grid_index(cols, i, j, &index)) {
        return false;
    }
    if (!aletheia_arr_at(m, a, index, &p)) {
        return false;
    }
    *out = p.addr;
    return true;
}

static bool aletheia_align_pow2(uint32_t a) {
    return a != 0u && (a & (a - 1u)) == 0u;
}

static bool aletheia_align_up(uint32_t n, uint32_t a, uint32_t *out) {
    uint64_t v;
    if (out == NULL || !aletheia_align_pow2(a)) {
        return false;
    }
    v = ((uint64_t)n + (uint64_t)a - 1u) & ~((uint64_t)a - 1u);
    if (v > (uint64_t)UINT32_MAX) {
        return false;
    }
    *out = (uint32_t)v;
    return true;
}

static bool aletheia_offset_table(const struct AletheiaMem *m,
                                  AletheiaAddr base,
                                  const struct AletheiaFieldSpec *spec,
                                  uint32_t n,
                                  struct AletheiaStruct *out) {
    struct AletheiaStruct s;
    uint64_t cursor = 0u;
    uint32_t max_align = 1u;
    uint32_t i;
    if (out == NULL || spec == NULL || n == 0u ||
        n > ALETHEIA_MAX_FIELDS) {
        return false;
    }
    s.addr = base;
    s.size = 0u;
    s.field_count = n;
    for (i = 0u; i < n; ++i) {
        uint32_t offset;
        uint64_t end;
        if (spec[i].size == 0u || !aletheia_align_pow2(spec[i].align)) {
            return false;
        }
        if (cursor > (uint64_t)UINT32_MAX) {
            return false;
        }
        if (!aletheia_align_up((uint32_t)cursor, spec[i].align,
                               &offset)) {
            return false;
        }
        end = (uint64_t)offset + (uint64_t)spec[i].size;
        if (end > (uint64_t)UINT32_MAX) {
            return false;
        }
        s.fields[i].offset = offset;
        s.fields[i].size = spec[i].size;
        s.fields[i].align = spec[i].align;
        cursor = end;
        if (spec[i].align > max_align) {
            max_align = spec[i].align;
        }
    }
    {
        uint64_t total;
        total = (cursor + (uint64_t)max_align - 1u) &
                ~((uint64_t)max_align - 1u);
        if (total > (uint64_t)UINT32_MAX ||
            !aletheia_mem_has(m, base, (uint32_t)total)) {
            return false;
        }
        s.size = (uint32_t)total;
    }
    *out = s;
    return true;
}

static bool aletheia_struct_ok(const struct AletheiaMem *m,
                               const struct AletheiaStruct *s) {
    uint32_t max_align = 1u;
    uint32_t i;
    if (s == NULL || s->field_count == 0u ||
        s->field_count > ALETHEIA_MAX_FIELDS || s->size == 0u) {
        return false;
    }
    if (!aletheia_mem_has(m, s->addr, s->size)) {
        return false;
    }
    for (i = 0u; i < s->field_count; ++i) {
        struct AletheiaField f = s->fields[i];
        if (f.size == 0u || !aletheia_align_pow2(f.align)) {
            return false;
        }
        if ((f.offset & (f.align - 1u)) != 0u) {
            return false;
        }
        if (i == 0u && f.offset != 0u) {
            return false;
        }
        if ((uint64_t)f.offset + (uint64_t)f.size >
            (uint64_t)s->size) {
            return false;
        }
        if (i > 0u) {
            struct AletheiaField prev = s->fields[i - 1u];
            if ((uint64_t)f.offset <
                (uint64_t)prev.offset + (uint64_t)prev.size) {
                return false;
            }
        }
        if (f.align > max_align) {
            max_align = f.align;
        }
    }
    return (s->size & (max_align - 1u)) == 0u;
}

static bool aletheia_field_ptr(const struct AletheiaMem *m,
                               const struct AletheiaStruct *s, uint32_t i,
                               struct AletheiaPtr *out) {
    struct AletheiaField f;
    if (s == NULL || out == NULL || !aletheia_struct_ok(m, s) ||
        i >= s->field_count) {
        return false;
    }
    f = s->fields[i];
    return aletheia_ptr_make(m, s->addr + f.offset, f.size, out);
}

static bool aletheia_struct_at(const struct AletheiaMem *m,
                               const struct AletheiaStruct *s, uint32_t i,
                               AletheiaAddr *out) {
    uint64_t addr;
    if (s == NULL || out == NULL || !aletheia_struct_ok(m, s)) {
        return false;
    }
    addr = (uint64_t)s->addr + (uint64_t)i * (uint64_t)s->size;
    if (addr + (uint64_t)s->size >
        (uint64_t)m->base + (uint64_t)m->size) {
        return false;
    }
    *out = (AletheiaAddr)addr;
    return true;
}

static bool aletheia_str_ok(const struct AletheiaMem *m,
                            const struct AletheiaStr *s) {
    struct AletheiaPtr p;
    if (s == NULL || s->capacity == 0u) {
        return false;
    }
    return aletheia_ptr_make(m, s->addr, s->capacity, &p);
}

static bool aletheia_str_make(const struct AletheiaMem *m,
                              AletheiaAddr addr, uint32_t capacity,
                              struct AletheiaStr *out) {
    struct AletheiaStr trial;
    if (out == NULL) {
        return false;
    }
    trial.addr = addr;
    trial.capacity = capacity;
    if (!aletheia_str_ok(m, &trial)) {
        return false;
    }
    *out = trial;
    return true;
}

static bool aletheia_str_byte(const struct AletheiaMem *m,
                              const struct AletheiaStr *s, uint32_t i,
                              AletheiaByte *out) {
    struct AletheiaPtr p;
    if (s == NULL || out == NULL || !aletheia_str_ok(m, s) ||
        i >= s->capacity) {
        return false;
    }
    if (!aletheia_ptr_make(m, s->addr + i, 1u, &p)) {
        return false;
    }
    return aletheia_ptr_read_u8(m, p, out);
}

static bool aletheia_str_poke(const struct AletheiaMem *m,
                              const struct AletheiaStr *s, uint32_t i,
                              AletheiaByte value) {
    struct AletheiaPtr p;
    if (s == NULL || !aletheia_str_ok(m, s) || i >= s->capacity) {
        return false;
    }
    if (!aletheia_ptr_make(m, s->addr + i, 1u, &p)) {
        return false;
    }
    return aletheia_ptr_write_u8(m, p, value);
}

static bool aletheia_strlen(const struct AletheiaMem *m,
                            const struct AletheiaStr *s, uint32_t *out) {
    struct AletheiaPtr base;
    uint32_t i;
    if (out == NULL || !aletheia_str_ok(m, s)) {
        return false;
    }
    if (!aletheia_ptr_make(m, s->addr, 1u, &base)) {
        return false;
    }
    for (i = 0u; i < s->capacity; ++i) {
        struct AletheiaPtr p;
        AletheiaByte b = 0u;
        if (!aletheia_ptr_walk(m, base, (int32_t)i, &p) ||
            !aletheia_ptr_read_u8(m, p, &b)) {
            return false;
        }
        if (b == 0u) {
            *out = i;
            return true;
        }
    }
    return false;
}

static bool aletheia_str_put(const struct AletheiaMem *m,
                             const struct AletheiaStr *s,
                             const char *text) {
    uint32_t n = 0u;
    uint32_t i;
    if (s == NULL || text == NULL || !aletheia_str_ok(m, s)) {
        return false;
    }
    while (text[n] != '\0') {
        ++n;
    }
    if (n >= s->capacity) {
        return false;
    }
    for (i = 0u; i < n; ++i) {
        if (!aletheia_str_poke(m, s, i, (AletheiaByte)text[i])) {
            return false;
        }
    }
    return aletheia_str_poke(m, s, n, 0u);
}

static bool aletheia_str_eq_text(const struct AletheiaMem *m,
                                 const struct AletheiaStr *s,
                                 const char *text) {
    uint32_t n;
    uint32_t i;
    if (text == NULL || !aletheia_strlen(m, s, &n)) {
        return false;
    }
    for (i = 0u; i < n; ++i) {
        AletheiaByte b = 0u;
        if (text[i] == '\0' || !aletheia_str_byte(m, s, i, &b) ||
            b != (AletheiaByte)text[i]) {
            return false;
        }
    }
    return text[n] == '\0';
}

static bool aletheia_str_print(const struct AletheiaMem *m,
                               const struct AletheiaStr *s) {
    uint32_t n = 0u;
    uint32_t limit;
    uint32_t i;
    bool terminated;
    if (!aletheia_str_ok(m, s)) {
        printf("(bad string)");
        return false;
    }
    terminated = aletheia_strlen(m, s, &n);
    limit = terminated ? n : s->capacity;
    for (i = 0u; i < limit; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_str_byte(m, s, i, &b)) {
            return false;
        }
        putchar((int)b);
    }
    if (!terminated) {
        printf("(unterminated)");
    }
    return terminated;
}

static bool aletheia_store_ok(const struct AletheiaMem *m,
                              const struct AletheiaStore *s) {
    if (s == NULL || s->size == 0u || !aletheia_mem_ok(m)) {
        return false;
    }
    return aletheia_mem_has(m, s->base, s->size);
}

static bool aletheia_store_make(const struct AletheiaMem *m,
                                AletheiaAddr base, uint32_t size,
                                struct AletheiaStore *out) {
    struct AletheiaStore trial;
    if (out == NULL) {
        return false;
    }
    trial.base = base;
    trial.size = size;
    if (!aletheia_store_ok(m, &trial)) {
        return false;
    }
    *out = trial;
    return true;
}

static bool aletheia_store_has(const struct AletheiaMem *m,
                               const struct AletheiaStore *s,
                               AletheiaAddr addr, uint32_t width) {
    uint32_t off;
    if (!aletheia_store_ok(m, s)) {
        return false;
    }
    if (width != 1u && width != 2u && width != 4u) {
        return false;
    }
    if (width > s->size || addr < s->base) {
        return false;
    }
    off = addr - s->base;
    if (off > s->size - width) {
        return false;
    }
    return aletheia_mem_has(m, addr, width);
}

static bool aletheia_store_span(const struct AletheiaMem *m,
                                const struct AletheiaStore *s,
                                AletheiaAddr addr, uint32_t n) {
    uint32_t off;
    if (!aletheia_store_ok(m, s) || n == 0u) {
        return false;
    }
    if (n > s->size || addr < s->base) {
        return false;
    }
    off = addr - s->base;
    if (off > s->size - n) {
        return false;
    }
    return aletheia_mem_has(m, addr, n);
}

static bool aletheia_store_read_le(const struct AletheiaMem *m,
                                   const struct AletheiaStore *s,
                                   AletheiaAddr addr, uint32_t width,
                                   uint32_t *out) {
    if (out == NULL || !aletheia_store_has(m, s, addr, width)) {
        return false;
    }
    return aletheia_mem_read_le(m, addr, width, out);
}

static bool aletheia_store_write_le(const struct AletheiaMem *m,
                                    const struct AletheiaStore *s,
                                    AletheiaAddr addr, uint32_t width,
                                    uint32_t value) {
    if (!aletheia_store_has(m, s, addr, width)) {
        return false;
    }
    return aletheia_mem_write_le(m, addr, width, value);
}

static bool aletheia_store_read_u32(const struct AletheiaMem *m,
                                    const struct AletheiaStore *s,
                                    AletheiaAddr addr, uint32_t *out) {
    return aletheia_store_read_le(m, s, addr, 4u, out);
}

static bool aletheia_store_write_u32(const struct AletheiaMem *m,
                                     const struct AletheiaStore *s,
                                     AletheiaAddr addr, uint32_t value) {
    return aletheia_store_write_le(m, s, addr, 4u, value);
}

static bool aletheia_label_ok(const char *label) {
    uint32_t i;
    if (label == NULL || label[0] == '\0') {
        return false;
    }
    for (i = 0u; i < ALETHEIA_LABEL; ++i) {
        if (label[i] == '\0') {
            return true;
        }
    }
    return false;
}

static bool aletheia_label_copy(char *dst, const char *src) {
    uint32_t i;
    if (dst == NULL || !aletheia_label_ok(src)) {
        return false;
    }
    for (i = 0u; i < ALETHEIA_LABEL; ++i) {
        dst[i] = src[i];
        if (src[i] == '\0') {
            return true;
        }
    }
    return false;
}

static bool aletheia_tape_ok(const struct AletheiaMem *m,
                             const struct AletheiaTape *t) {
    struct AletheiaStore region;
    AletheiaAddr cursor;
    uint32_t i;
    if (t == NULL || t->mark_count > ALETHEIA_MAX_MARKS) {
        return false;
    }
    if (!aletheia_store_make(m, t->base, t->size, &region)) {
        return false;
    }
    cursor = t->base;
    for (i = 0u; i < t->mark_count; ++i) {
        const struct AletheiaMark *mk = &t->marks[i];
        uint32_t off;
        if (mk->size == 0u || mk->size > t->size ||
            !aletheia_label_ok(mk->label)) {
            return false;
        }
        if (mk->addr < cursor) {
            return false;
        }
        off = mk->addr - t->base;
        if (off > t->size - mk->size) {
            return false;
        }
        cursor = mk->addr + mk->size;
    }
    return true;
}

static bool aletheia_tape_make(const struct AletheiaMem *m,
                               AletheiaAddr base, uint32_t size,
                               struct AletheiaTape *out) {
    struct AletheiaTape trial;
    uint32_t i;
    uint32_t j;
    if (out == NULL) {
        return false;
    }
    trial.base = base;
    trial.size = size;
    trial.mark_count = 0u;
    for (i = 0u; i < ALETHEIA_MAX_MARKS; ++i) {
        trial.marks[i].addr = 0u;
        trial.marks[i].size = 0u;
        for (j = 0u; j < ALETHEIA_LABEL; ++j) {
            trial.marks[i].label[j] = '\0';
        }
    }
    if (!aletheia_tape_ok(m, &trial)) {
        return false;
    }
    *out = trial;
    return true;
}

static bool aletheia_tape_mark(const struct AletheiaMem *m,
                               struct AletheiaTape *t, AletheiaAddr addr,
                               uint32_t size, const char *label) {
    struct AletheiaMark mk;
    uint32_t off;
    if (t == NULL || label == NULL || !aletheia_tape_ok(m, t)) {
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
        const struct AletheiaMark *last =
            &t->marks[t->mark_count - 1u];
        if (last->addr + last->size > addr) {
            return false;
        }
    }
    mk.addr = addr;
    mk.size = size;
    if (!aletheia_label_copy(mk.label, label)) {
        return false;
    }
    t->marks[t->mark_count] = mk;
    t->mark_count += 1u;
    return true;
}

static bool aletheia_tape_find(const struct AletheiaMem *m,
                               const struct AletheiaTape *t,
                               AletheiaAddr addr, uint32_t *index,
                               uint32_t *offset) {
    uint32_t i;
    if (index == NULL || offset == NULL || !aletheia_tape_ok(m, t)) {
        return false;
    }
    for (i = 0u; i < t->mark_count; ++i) {
        const struct AletheiaMark *mk = &t->marks[i];
        if (addr >= mk->addr && addr < mk->addr + mk->size) {
            *index = i;
            *offset = addr - mk->addr;
            return true;
        }
    }
    return false;
}

static bool aletheia_tape_cover(const struct AletheiaMem *m,
                                const struct AletheiaTape *t,
                                uint32_t *covered, uint32_t *gaps) {
    uint32_t total = 0u;
    uint32_t i;
    if (covered == NULL || gaps == NULL || !aletheia_tape_ok(m, t)) {
        return false;
    }
    for (i = 0u; i < t->mark_count; ++i) {
        total += t->marks[i].size;
    }
    *covered = total;
    *gaps = t->size - total;
    return true;
}

static bool aletheia_tape_store(const struct AletheiaMem *m,
                                const struct AletheiaTape *t,
                                struct AletheiaStore *out) {
    if (t == NULL) {
        return false;
    }
    return aletheia_store_make(m, t->base, t->size, out);
}

static bool aletheia_hexdump(const struct AletheiaMem *m,
                             const struct AletheiaStore *s,
                             AletheiaAddr addr, uint32_t n) {
    uint32_t done = 0u;
    if (!aletheia_store_span(m, s, addr, n)) {
        return false;
    }
    while (done < n) {
        uint32_t row = n - done;
        uint32_t i;
        if (row > 16u) {
            row = 16u;
        }
        printf("0x%05x ", (unsigned)(addr + done));
        for (i = 0u; i < 16u; ++i) {
            if (i < row) {
                AletheiaByte b = 0u;
                if (!aletheia_peek_u8(m, addr + done + i, &b)) {
                    return false;
                }
                printf("%02x ", (unsigned)b);
            } else {
                printf("   ");
            }
        }
        printf("|");
        for (i = 0u; i < row; ++i) {
            AletheiaByte b = 0u;
            if (!aletheia_peek_u8(m, addr + done + i, &b)) {
                return false;
            }
            putchar((b >= 0x20u && b <= 0x7eu) ? (int)b : '.');
        }
        printf("|\n");
        done += row;
    }
    return true;
}

static long long aletheia_signed32(uint32_t v) {
    if (v <= 0x7fffffffu) {
        return (long long)v;
    }
    return (long long)v - 4294967296LL;
}

static bool aletheia_fill_boot(const struct AletheiaMem *m) {
    static const char signature[8] = {
        'A', 'L', 'E', 'T', 'H', 'E', 'I', 'A'
    };
    uint32_t i;
    if (!aletheia_span_fill(m, aletheia_regions[REGION_BOOT].span, 0u)) {
        return false;
    }
    for (i = 0u; i < 8u; ++i) {
        if (!aletheia_poke_u8(
                m, aletheia_regions[REGION_BOOT].span.addr + i,
                (AletheiaByte)signature[i])) {
            return false;
        }
    }
    return true;
}

static bool aletheia_fill_data(const struct AletheiaMem *m) {
    static const uint32_t values[8] = {
        0x00000000u, 0x00000001u, 0xffffffffu, 0x12345678u,
        0xdeadbeefu, 0x0000002au, 0x7fffffffu, 0x80000000u
    };
    AletheiaAddr base = aletheia_regions[REGION_DATA].span.addr;
    uint32_t i;
    if (!aletheia_span_fill(m, aletheia_regions[REGION_DATA].span, 0u)) {
        return false;
    }
    for (i = 0u; i < 8u; ++i) {
        if (!aletheia_write_u32(m, base + i * 4u, values[i])) {
            return false;
        }
    }
    for (i = 0u; i < 12u; ++i) {
        if (!aletheia_poke_u8(m, base + 0x60u + i,
                              (AletheiaByte)(i + 1u))) {
            return false;
        }
    }
    return true;
}

static bool aletheia_fill_stack(const struct AletheiaMem *m) {
    struct AletheiaSpan stack = aletheia_regions[REGION_STACK].span;
    AletheiaAddr end = 0u;
    if (!aletheia_span_fill(m, stack, 0u) ||
        !aletheia_span_end(m, stack, &end)) {
        return false;
    }
    if (!aletheia_write_u32(m, end - 8u, 42u)) {
        return false;
    }
    return aletheia_write_u32(m, end - 4u,
                              aletheia_regions[REGION_CODE].span.addr);
}

static bool aletheia_build_record(const struct AletheiaMem *m,
                                  struct AletheiaStruct *out) {
    static const struct AletheiaFieldSpec specs[5] = {
        { 4u, 4u }, { 2u, 2u }, { 1u, 1u }, { 1u, 1u }, { 4u, 4u }
    };
    AletheiaAddr base = aletheia_regions[REGION_DATA].span.addr + 0x20u;
    return aletheia_offset_table(m, base, specs, 5u, out);
}

static bool aletheia_fill_record(const struct AletheiaMem *m,
                                 const struct AletheiaStruct *rec) {
    struct AletheiaStore store;
    struct AletheiaPtr p;
    if (!aletheia_store_make(m, rec->addr, rec->size, &store)) {
        return false;
    }
    if (!aletheia_field_ptr(m, rec, 0u, &p) ||
        !aletheia_store_write_u32(m, &store, p.addr, 7u)) {
        return false;
    }
    if (!aletheia_field_ptr(m, rec, 1u, &p) ||
        !aletheia_store_write_le(m, &store, p.addr, 2u, 3u)) {
        return false;
    }
    if (!aletheia_field_ptr(m, rec, 2u, &p) ||
        !aletheia_store_write_le(m, &store, p.addr, 1u, 1u)) {
        return false;
    }
    if (!aletheia_field_ptr(m, rec, 3u, &p) ||
        !aletheia_store_write_le(m, &store, p.addr, 1u, 2u)) {
        return false;
    }
    if (!aletheia_field_ptr(m, rec, 4u, &p) ||
        !aletheia_store_write_u32(
            m, &store, p.addr,
            aletheia_regions[REGION_DATA].span.addr)) {
        return false;
    }
    return true;
}

static bool aletheia_build_string(const struct AletheiaMem *m,
                                  struct AletheiaStr *out) {
    AletheiaAddr base = aletheia_regions[REGION_DATA].span.addr + 0x40u;
    if (!aletheia_str_make(m, base, 32u, out)) {
        return false;
    }
    return aletheia_str_put(m, out, "Aletheia");
}

static bool aletheia_build_tape(const struct AletheiaMem *m,
                                struct AletheiaTape *out) {
    uint32_t i;
    if (!aletheia_tape_make(m, 0u, ALETHEIA_SIZE, out)) {
        return false;
    }
    for (i = 0u; i < (uint32_t)REGION_COUNT; ++i) {
        const struct AletheiaRegion *r = &aletheia_regions[i];
        if (!aletheia_tape_mark(m, out, r->span.addr, r->span.size,
                                r->label)) {
            return false;
        }
    }
    return true;
}

static bool aletheia_check_marks(const struct AletheiaMem *m,
                                 const struct AletheiaTape *t) {
    uint32_t i;
    if (!aletheia_tape_ok(m, t)) {
        return false;
    }
    printf("MARKS\n");
    printf("LABEL START END   SIZE\n");
    for (i = 0u; i < t->mark_count; ++i) {
        const struct AletheiaMark *mk = &t->marks[i];
        printf("%-5s 0x%05x 0x%05x %5u\n", mk->label,
               (unsigned)mk->addr, (unsigned)(mk->addr + mk->size),
               (unsigned)mk->size);
    }
    return true;
}

static bool aletheia_text_eq(const char *a, const char *b) {
    uint32_t i;
    if (a == NULL || b == NULL) {
        return false;
    }
    for (i = 0u; i < ALETHEIA_LABEL; ++i) {
        if (a[i] != b[i]) {
            return false;
        }
        if (a[i] == '\0') {
            return true;
        }
    }
    return false;
}

static bool aletheia_check_find(const struct AletheiaMem *m,
                                const struct AletheiaTape *t) {
    static const AletheiaAddr addrs[10] = {
        0x00000u, 0x0003fu, 0x00100u, 0x01000u, 0x010ffu,
        0x3f1ffu, 0x3f200u, 0x3ffffu, 0x00040u, 0x3e000u
    };
    static const char *const labels[10] = {
        "boot", "boot", "code", "data", "data",
        "stack", "free", "free", "(gap)", "(gap)"
    };
    static const uint32_t offsets[10] = {
        0u, 63u, 0u, 0u, 255u, 511u, 0u, 3583u, 0u, 0u
    };
    uint32_t i;
    printf("\nFIND\n");
    printf("ADDR    LABEL OFFSET\n");
    for (i = 0u; i < 10u; ++i) {
        uint32_t index = 0u;
        uint32_t offset = 0u;
        bool found = aletheia_tape_find(m, t, addrs[i],
                                        &index, &offset);
        if (found) {
            printf("0x%05x %-5s %u\n", (unsigned)addrs[i],
                   t->marks[index].label, (unsigned)offset);
            if (offset != offsets[i] ||
                !aletheia_text_eq(t->marks[index].label, labels[i])) {
                return false;
            }
        } else {
            printf("0x%05x %-5s %u\n", (unsigned)addrs[i],
                   "(gap)", 0u);
            if (labels[i][0] != '(') {
                return false;
            }
        }
    }
    return true;
}

static bool aletheia_check_paper(const struct AletheiaMem *m,
                                 const struct AletheiaTape *t) {
    static const uint32_t expected[8] = {
        0x00000000u, 0x00000001u, 0xffffffffu, 0x12345678u,
        0xdeadbeefu, 0x0000002au, 0x7fffffffu, 0x80000000u
    };
    struct AletheiaStore full;
    AletheiaAddr base = aletheia_regions[REGION_DATA].span.addr;
    uint32_t i;
    if (!aletheia_tape_store(m, t, &full)) {
        return false;
    }
    printf("\nPAPER TAPE\n");
    printf("ADDR    BYTES       HEX      UNSIGNED   SIGNED\n");
    for (i = 0u; i < 8u; ++i) {
        AletheiaAddr addr = base + i * 4u;
        uint32_t value = 0u;
        uint32_t j;
        if (!aletheia_store_read_u32(m, &full, addr, &value) ||
            value != expected[i]) {
            return false;
        }
        printf("0x%05x ", (unsigned)addr);
        for (j = 0u; j < 4u; ++j) {
            AletheiaByte b = 0u;
            if (!aletheia_peek_u8(m, addr + j, &b)) {
                return false;
            }
            printf("%02x ", (unsigned)b);
        }
        printf(" %08x %10u %10lld\n", (unsigned)value,
               (unsigned)value, aletheia_signed32(value));
    }
    return true;
}

static bool aletheia_check_ptr(const struct AletheiaMem *m) {
    struct AletheiaPtr base;
    AletheiaAddr data = aletheia_regions[REGION_DATA].span.addr;
    uint32_t i;
    if (!aletheia_ptr_make(m, data, 4u, &base)) {
        return false;
    }
    printf("\nPTR\n");
    printf("INDEX ADDR    EXPECT  DELTA OK\n");
    for (i = 0u; i < 8u; ++i) {
        struct AletheiaPtr p;
        AletheiaAddr expect = data + i * 4u;
        AletheiaAddr computed = 0u;
        int32_t delta = 0;
        bool ok;
        if (!aletheia_ptr_walk(m, base, (int32_t)i, &p) ||
            !aletheia_ptr_diff(m, p, base, &delta) ||
            !aletheia_addr_of(m, data, i, 4u, &computed)) {
            return false;
        }
        ok = p.addr == expect && computed == expect &&
             delta == (int32_t)i;
        printf("%5u 0x%05x 0x%05x %5d %s\n", (unsigned)i,
               (unsigned)p.addr, (unsigned)expect, (int)delta,
               ok ? "true" : "false");
        if (!ok) {
            return false;
        }
    }
    return true;
}

static bool aletheia_check_array(const struct AletheiaMem *m) {
    AletheiaAddr base = aletheia_regions[REGION_DATA].span.addr + 0x60u;
    struct AletheiaArr bytes;
    struct AletheiaPtr p;
    AletheiaAddr at7 = 0u;
    AletheiaAddr grid = 0u;
    uint32_t sum = 0u;
    bool ok;
    if (!aletheia_arr_make(m, base, 1u, 12u, &bytes) ||
        !aletheia_arr_sum(m, bytes, &sum) ||
        !aletheia_arr_at(m, bytes, 7u, &p) ||
        !aletheia_arr_addr(m, bytes, 7u, &at7) ||
        !aletheia_grid_addr(m, base, 1u, 3u, 4u, 1u, 2u, &grid)) {
        return false;
    }
    printf("\nARRAY\n");
    printf("BASE  0x%05x\n", (unsigned)base);
    printf("COUNT %u\n", (unsigned)bytes.count);
    printf("SUM   %u\n", (unsigned)sum);
    printf("AT7   0x%05x\n", (unsigned)p.addr);
    printf("GRID  1,2 0x%05x\n", (unsigned)grid);
    ok = sum == 78u && p.addr == base + 7u && at7 == base + 7u &&
         grid == base + 6u;
    return ok;
}

static bool aletheia_check_layout(const struct AletheiaMem *m,
                                  const struct AletheiaStruct *rec) {
    static const char *const names[5] = {
        "id", "flags", "kind", "tag", "next"
    };
    static const uint32_t expected[5] = { 0u, 4u, 6u, 7u, 8u };
    uint32_t i;
    if (!aletheia_struct_ok(m, rec)) {
        return false;
    }
    printf("\nLAYOUT\n");
    printf("FIELD OFFSET SIZE\n");
    for (i = 0u; i < 5u; ++i) {
        printf("%-5s %6u %4u\n", names[i],
               (unsigned)rec->fields[i].offset,
               (unsigned)rec->fields[i].size);
        if (rec->fields[i].offset != expected[i]) {
            return false;
        }
    }
    printf("TOTAL %6u\n", (unsigned)rec->size);
    return rec->size == 12u;
}

static bool aletheia_check_record(const struct AletheiaMem *m,
                                  const struct AletheiaStruct *rec) {
    struct AletheiaStore store;
    struct AletheiaPtr p;
    AletheiaAddr inst0 = 0u;
    AletheiaAddr inst1 = 0u;
    uint32_t id = 0u;
    uint32_t flags = 0u;
    uint32_t kind = 0u;
    uint32_t tag = 0u;
    uint32_t next = 0u;
    if (!aletheia_store_make(m, rec->addr, rec->size, &store)) {
        return false;
    }
    if (!aletheia_field_ptr(m, rec, 0u, &p) ||
        !aletheia_store_read_u32(m, &store, p.addr, &id)) {
        return false;
    }
    if (!aletheia_field_ptr(m, rec, 1u, &p) ||
        !aletheia_store_read_le(m, &store, p.addr, 2u, &flags)) {
        return false;
    }
    if (!aletheia_field_ptr(m, rec, 2u, &p) ||
        !aletheia_store_read_le(m, &store, p.addr, 1u, &kind)) {
        return false;
    }
    if (!aletheia_field_ptr(m, rec, 3u, &p) ||
        !aletheia_store_read_le(m, &store, p.addr, 1u, &tag)) {
        return false;
    }
    if (!aletheia_field_ptr(m, rec, 4u, &p) ||
        !aletheia_store_read_u32(m, &store, p.addr, &next)) {
        return false;
    }
    if (!aletheia_struct_at(m, rec, 0u, &inst0) ||
        !aletheia_struct_at(m, rec, 1u, &inst1)) {
        return false;
    }
    printf("\nRECORD\n");
    printf("ADDR    FIELD VALUE\n");
    printf("0x%05x id    %u\n", (unsigned)rec->addr, (unsigned)id);
    printf("0x%05x flags %u\n", (unsigned)(rec->addr + 4u),
           (unsigned)flags);
    printf("0x%05x kind  %u\n", (unsigned)(rec->addr + 6u),
           (unsigned)kind);
    printf("0x%05x tag   %u\n", (unsigned)(rec->addr + 7u),
           (unsigned)tag);
    printf("0x%05x next  0x%05x\n", (unsigned)(rec->addr + 8u),
           (unsigned)next);
    printf("INSTANCE 0 0x%05x\n", (unsigned)inst0);
    printf("INSTANCE 1 0x%05x\n", (unsigned)inst1);
    return id == 7u && flags == 3u && kind == 1u && tag == 2u &&
           next == aletheia_regions[REGION_DATA].span.addr &&
           inst0 == rec->addr && inst1 == rec->addr + rec->size;
}

static bool aletheia_check_string(const struct AletheiaMem *m,
                                  const struct AletheiaStr *s) {
    uint32_t len = 0u;
    printf("\nSTRING\nTEXT ");
    if (!aletheia_str_print(m, s)) {
        return false;
    }
    if (!aletheia_strlen(m, s, &len)) {
        return false;
    }
    printf("\nLEN  %u\n", (unsigned)len);
    return len == 8u && aletheia_str_eq_text(m, s, "Aletheia");
}

static bool aletheia_check_boot(const struct AletheiaMem *m) {
    static const char expect[8] = {
        'A', 'L', 'E', 'T', 'H', 'E', 'I', 'A'
    };
    struct AletheiaSpan boot = aletheia_regions[REGION_BOOT].span;
    uint32_t i;
    if (!aletheia_span_ok(m, boot)) {
        return false;
    }
    printf("\nBOOT\nSIGNATURE ");
    for (i = 0u; i < 8u; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_peek_u8(m, boot.addr + i, &b) ||
            (char)b != expect[i]) {
            return false;
        }
        putchar((int)b);
    }
    printf("\n");
    return true;
}

static bool aletheia_check_stack(const struct AletheiaMem *m,
                                 const struct AletheiaTape *t) {
    struct AletheiaStore full;
    struct AletheiaSpan stack = aletheia_regions[REGION_STACK].span;
    AletheiaAddr end = 0u;
    AletheiaAddr frame_addr;
    AletheiaAddr ret_addr;
    uint32_t frame = 0u;
    uint32_t ret = 0u;
    if (!aletheia_tape_store(m, t, &full) ||
        !aletheia_span_end(m, stack, &end)) {
        return false;
    }
    frame_addr = end - 8u;
    ret_addr = end - 4u;
    if (!aletheia_store_read_u32(m, &full, frame_addr, &frame) ||
        !aletheia_store_read_u32(m, &full, ret_addr, &ret)) {
        return false;
    }
    printf("\nSTACK\n");
    printf("SP     0x%05x\n", (unsigned)frame_addr);
    printf("FRAME  %u\n", (unsigned)frame);
    printf("RET    0x%05x\n", (unsigned)ret);
    return frame == 42u && ret == 0x00100u;
}

static bool aletheia_check_span(const struct AletheiaMem *m) {
    static const char signature[8] = {
        'A', 'L', 'E', 'T', 'H', 'E', 'I', 'A'
    };
    struct AletheiaSpan machine = aletheia_span_new(0u, ALETHEIA_SIZE);
    struct AletheiaSpan scratch;
    bool okay = true;
    bool ordered = true;
    bool disjoint = true;
    bool inside = true;
    bool copied;
    uint32_t i;
    uint32_t j;
    printf("\nSPAN\n");
    printf("LABEL START END   SIZE OK\n");
    for (i = 0u; i < (uint32_t)REGION_COUNT; ++i) {
        struct AletheiaSpan s = aletheia_regions[i].span;
        AletheiaAddr end = 0u;
        bool ok = aletheia_span_ok(m, s) &&
                  aletheia_span_end(m, s, &end);
        printf("%-5s 0x%05x 0x%05x %5u %s\n",
               aletheia_regions[i].label, (unsigned)s.addr,
               (unsigned)end, (unsigned)s.size,
               ok ? "true" : "false");
        if (!ok) {
            okay = false;
        }
        if (!aletheia_span_contains(m, machine, s)) {
            inside = false;
        }
        if (i > 0u) {
            AletheiaAddr prev_end = 0u;
            if (!aletheia_span_end(m, aletheia_regions[i - 1u].span,
                                   &prev_end) ||
                prev_end > s.addr) {
                ordered = false;
            }
        }
        for (j = i + 1u; j < (uint32_t)REGION_COUNT; ++j) {
            if (aletheia_span_overlap(m, s,
                                      aletheia_regions[j].span)) {
                disjoint = false;
            }
        }
    }
    scratch = aletheia_span_new(
        aletheia_regions[REGION_DATA].span.addr + 0x70u, 8u);
    copied = aletheia_span_fill(m, scratch, 0u) &&
             aletheia_span_copy(
                 m, scratch,
                 aletheia_span_new(
                     aletheia_regions[REGION_BOOT].span.addr, 8u));
    for (i = 0u; copied && i < 8u; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_peek_u8(m, scratch.addr + i, &b) ||
            b != (AletheiaByte)signature[i]) {
            copied = false;
        }
    }
    printf("ORDER    %s\n", ordered ? "true" : "false");
    printf("DISJOINT %s\n", disjoint ? "true" : "false");
    printf("INSIDE   %s\n", inside ? "true" : "false");
    printf("COPY     %s\n", copied ? "true" : "false");
    return okay && ordered && disjoint && inside && copied;
}

static bool aletheia_check_cover(const struct AletheiaMem *m,
                                 const struct AletheiaTape *t) {
    uint32_t covered = 0u;
    uint32_t gaps = 0u;
    if (!aletheia_tape_cover(m, t, &covered, &gaps)) {
        return false;
    }
    printf("\nCOVER\n");
    printf("MARKED %u\n", (unsigned)covered);
    printf("GAPS   %u\n", (unsigned)gaps);
    printf("TOTAL  %u\n", (unsigned)(covered + gaps));
    printf("ties   %s\n",
           covered + gaps == ALETHEIA_SIZE ? "true" : "false");
    return covered + gaps == ALETHEIA_SIZE;
}

static bool aletheia_check_fail(const struct AletheiaMem *m,
                                const struct AletheiaTape *t) {
    static const struct AletheiaFieldSpec bad_specs[2] = {
        { 4u, 3u }, { 4u, 4u }
    };
    struct AletheiaMem bad_mem;
    struct AletheiaStore full;
    struct AletheiaStore bad_store;
    struct AletheiaPtr p4;
    struct AletheiaPtr pa;
    struct AletheiaPtr pb;
    struct AletheiaPtr out;
    struct AletheiaArr bytes;
    struct AletheiaStruct bad_struct;
    struct AletheiaStr bad_str;
    struct AletheiaTape overlap;
    struct AletheiaArr bad_arr;
    uint32_t value = 0u;
    AletheiaAddr addr = 0u;
    int32_t delta = 0;
    bool mem_range;
    bool store_range;
    bool read_tail;
    bool write_tail;
    bool bad_width;
    bool addr_bad;
    bool ptr_bad;
    bool diff_bad;
    bool array_bad;
    bool index_bad;
    bool layout_bad;
    bool struct_bad;
    bool string_bad;
    bool overlap_bad;
    if (!aletheia_tape_store(m, t, &full)) {
        return false;
    }
    mem_range = !aletheia_mem_make(&bad_mem, 0x3f000u, 0x2000u);
    store_range = !aletheia_store_make(m, 0x3f000u, 0x2000u,
                                       &bad_store);
    read_tail = !aletheia_store_read_u32(m, &full, 0x3ffffu, &value);
    write_tail = !aletheia_store_write_u32(m, &full, 0x3ffffu, 1u);
    bad_width = !aletheia_store_read_le(m, &full, 0x01000u, 3u,
                                        &value);
    addr_bad = !aletheia_addr_of(m, 0x01000u, 0x40000000u, 4u, &addr);
    ptr_bad = aletheia_ptr_make(m, 0x01000u, 4u, &p4) &&
              !aletheia_ptr_walk(m, p4, 0x40000000, &out);
    diff_bad = aletheia_ptr_make(m, 0x01001u, 4u, &pa) &&
               aletheia_ptr_make(m, 0x01004u, 4u, &pb) &&
               !aletheia_ptr_diff(m, pa, pb, &delta);
    array_bad = !aletheia_arr_make(m, 0x01000u, 4u, 0x40000000u,
                                   &bad_arr);
    index_bad = aletheia_arr_make(m, 0x01060u, 1u, 12u, &bytes) &&
                !aletheia_arr_at(m, bytes, 12u, &out);
    layout_bad = !aletheia_offset_table(m, 0x01000u, bad_specs, 2u,
                                        &bad_struct);
    bad_struct.addr = 0x01000u;
    bad_struct.size = 12u;
    bad_struct.field_count = 1u;
    bad_struct.fields[0].offset = 0u;
    bad_struct.fields[0].size = 4u;
    bad_struct.fields[0].align = 3u;
    struct_bad = !aletheia_struct_ok(m, &bad_struct);
    string_bad = !aletheia_str_make(m, 0x3ffffu, 4u, &bad_str);
    overlap_bad = aletheia_tape_make(m, 0u, 0x1000u, &overlap) &&
                  aletheia_tape_mark(m, &overlap, 0x100u, 0x100u,
                                     "first") &&
                  !aletheia_tape_mark(m, &overlap, 0x180u, 0x10u,
                                      "second");
    printf("\nFAIL\n");
    printf("mem range     %s\n",
           mem_range ? "rejected" : "accepted");
    printf("store range   %s\n",
           store_range ? "rejected" : "accepted");
    printf("read tail     %s\n",
           read_tail ? "rejected" : "accepted");
    printf("write tail    %s\n",
           write_tail ? "rejected" : "accepted");
    printf("bad width     %s\n",
           bad_width ? "rejected" : "accepted");
    printf("addr overflow %s\n",
           addr_bad ? "rejected" : "accepted");
    printf("ptr walk      %s\n", ptr_bad ? "rejected" : "accepted");
    printf("ptr diff      %s\n", diff_bad ? "rejected" : "accepted");
    printf("array fit     %s\n",
           array_bad ? "rejected" : "accepted");
    printf("array index   %s\n",
           index_bad ? "rejected" : "accepted");
    printf("bad layout    %s\n",
           layout_bad ? "rejected" : "accepted");
    printf("bad struct    %s\n",
           struct_bad ? "rejected" : "accepted");
    printf("bad string    %s\n",
           string_bad ? "rejected" : "accepted");
    printf("overlap mark  %s\n",
           overlap_bad ? "rejected" : "accepted");
    return mem_range && store_range && read_tail && write_tail &&
           bad_width && addr_bad && ptr_bad && diff_bad &&
           array_bad && index_bad && layout_bad && struct_bad &&
           string_bad && overlap_bad;
}

int main(void) {
    struct AletheiaMem machine;
    struct AletheiaTape tape;
    struct AletheiaStruct record;
    struct AletheiaStr text;
    bool ok_mem;
    bool ok_marks;
    bool ok_find;
    bool ok_paper;
    bool ok_ptr;
    bool ok_array;
    bool ok_layout;
    bool ok_record;
    bool ok_string;
    bool ok_boot;
    bool ok_stack;
    bool ok_span;
    bool ok_hex;
    bool ok_cover;
    bool ok_fail;
    bool ok;
    uint32_t i;
    ok_mem = aletheia_mem_make(&machine, 0u, ALETHEIA_SIZE);
    if (!ok_mem) {
        printf("ALETHEIA MEM BROKEN\n");
        return 1;
    }
    if (!aletheia_fill_boot(&machine) ||
        !aletheia_fill_data(&machine) ||
        !aletheia_fill_stack(&machine) ||
        !aletheia_build_record(&machine, &record) ||
        !aletheia_fill_record(&machine, &record) ||
        !aletheia_build_string(&machine, &text) ||
        !aletheia_build_tape(&machine, &tape)) {
        printf("ALETHEIA MEM BROKEN\n");
        return 1;
    }
    printf("ALETHEIA MEM\n");
    printf("SIZE  : %u\n", (unsigned)ALETHEIA_SIZE);
    printf("MACH  : 0x%05x..0x%05x\n", (unsigned)machine.base,
           (unsigned)(machine.base + machine.size - 1u));
    for (i = 0u; i < (uint32_t)REGION_COUNT; ++i) {
        const struct AletheiaSpan *s = &aletheia_regions[i].span;
        printf("%-5s : 0x%05x..0x%05x\n", aletheia_regions[i].label,
               (unsigned)s->addr,
               (unsigned)(s->addr + s->size - 1u));
    }
    printf("\n");
    ok_marks = aletheia_check_marks(&machine, &tape);
    ok_find = aletheia_check_find(&machine, &tape);
    ok_paper = aletheia_check_paper(&machine, &tape);
    ok_ptr = aletheia_check_ptr(&machine);
    ok_array = aletheia_check_array(&machine);
    ok_layout = aletheia_check_layout(&machine, &record);
    ok_record = aletheia_check_record(&machine, &record);
    ok_string = aletheia_check_string(&machine, &text);
    ok_boot = aletheia_check_boot(&machine);
    ok_stack = aletheia_check_stack(&machine, &tape);
    ok_span = aletheia_check_span(&machine);
    printf("\nHEXDUMP\n");
    printf("ADDR    00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f  "
           "ASCII\n");
    {
        struct AletheiaStore data;
        if (!aletheia_store_make(
                &machine, aletheia_regions[REGION_DATA].span.addr,
                aletheia_regions[REGION_DATA].span.size, &data)) {
            ok_hex = false;
        } else {
            ok_hex = aletheia_hexdump(
                &machine, &data,
                aletheia_regions[REGION_DATA].span.addr, 80u);
        }
    }
    ok_cover = aletheia_check_cover(&machine, &tape);
    ok_fail = aletheia_check_fail(&machine, &tape);
    ok = ok_mem && ok_marks && ok_find && ok_paper && ok_ptr &&
         ok_array && ok_layout && ok_record && ok_string && ok_boot &&
         ok_stack && ok_span && ok_hex && ok_cover && ok_fail;
    printf("\nSUMMARY\n");
    printf("mem     : %s\n", ok_mem ? "true" : "false");
    printf("marks   : %s\n", ok_marks ? "true" : "false");
    printf("find    : %s\n", ok_find ? "true" : "false");
    printf("paper   : %s\n", ok_paper ? "true" : "false");
    printf("ptr     : %s\n", ok_ptr ? "true" : "false");
    printf("array   : %s\n", ok_array ? "true" : "false");
    printf("layout  : %s\n", ok_layout ? "true" : "false");
    printf("record  : %s\n", ok_record ? "true" : "false");
    printf("string  : %s\n", ok_string ? "true" : "false");
    printf("boot    : %s\n", ok_boot ? "true" : "false");
    printf("stack   : %s\n", ok_stack ? "true" : "false");
    printf("span    : %s\n", ok_span ? "true" : "false");
    printf("hexdump : %s\n", ok_hex ? "true" : "false");
    printf("cover   : %s\n", ok_cover ? "true" : "false");
    printf("fail    : %s\n", ok_fail ? "true" : "false");
    if (!ok) {
        printf("ALETHEIA MEM BROKEN\n");
        return 1;
    }
    printf("ALETHEIA MEM OK\n");
    return 0;
}
```

## 八、真实输出与验收

在本地编译运行，得到以下输出：

```text
ALETHEIA MEM
SIZE  : 262144
MACH  : 0x00000..0x3ffff
boot  : 0x00000..0x0003f
code  : 0x00100..0x002ff
data  : 0x01000..0x010ff
stack : 0x3f000..0x3f1ff
free  : 0x3f200..0x3ffff

MARKS
LABEL START END   SIZE
boot  0x00000 0x00040    64
code  0x00100 0x00300   512
data  0x01000 0x01100   256
stack 0x3f000 0x3f200   512
free  0x3f200 0x40000  3584

FIND
ADDR    LABEL OFFSET
0x00000 boot  0
0x0003f boot  63
0x00100 code  0
0x01000 data  0
0x010ff data  255
0x3f1ff stack 511
0x3f200 free  0
0x3ffff free  3583
0x00040 (gap) 0
0x3e000 (gap) 0

PAPER TAPE
ADDR    BYTES       HEX      UNSIGNED   SIGNED
0x01000 00 00 00 00  00000000          0          0
0x01004 01 00 00 00  00000001          1          1
0x01008 ff ff ff ff  ffffffff 4294967295         -1
0x0100c 78 56 34 12  12345678  305419896  305419896
0x01010 ef be ad de  deadbeef 3735928559 -559038737
0x01014 2a 00 00 00  0000002a         42         42
0x01018 ff ff ff 7f  7fffffff 2147483647 2147483647
0x0101c 00 00 00 80  80000000 2147483648 -2147483648

PTR
INDEX ADDR    EXPECT  DELTA OK
    0 0x01000 0x01000     0 true
    1 0x01004 0x01004     1 true
    2 0x01008 0x01008     2 true
    3 0x0100c 0x0100c     3 true
    4 0x01010 0x01010     4 true
    5 0x01014 0x01014     5 true
    6 0x01018 0x01018     6 true
    7 0x0101c 0x0101c     7 true

ARRAY
BASE  0x01060
COUNT 12
SUM   78
AT7   0x01067
GRID  1,2 0x01066

LAYOUT
FIELD OFFSET SIZE
id         0    4
flags      4    2
kind       6    1
tag        7    1
next       8    4
TOTAL     12

RECORD
ADDR    FIELD VALUE
0x01020 id    7
0x01024 flags 3
0x01026 kind  1
0x01027 tag   2
0x01028 next  0x01000
INSTANCE 0 0x01020
INSTANCE 1 0x0102c

STRING
TEXT Aletheia
LEN  8

BOOT
SIGNATURE ALETHEIA

STACK
SP     0x3f1f8
FRAME  42
RET    0x00100

SPAN
LABEL START END   SIZE OK
boot  0x00000 0x00040    64 true
code  0x00100 0x00300   512 true
data  0x01000 0x01100   256 true
stack 0x3f000 0x3f200   512 true
free  0x3f200 0x40000  3584 true
ORDER    true
DISJOINT true
INSIDE   true
COPY     true

HEXDUMP
ADDR    00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f  ASCII
0x01000 00 00 00 00 01 00 00 00 ff ff ff ff 78 56 34 12 |............xV4.|
0x01010 ef be ad de 2a 00 00 00 ff ff ff 7f 00 00 00 80 |....*...........|
0x01020 07 00 00 00 03 00 01 02 00 10 00 00 00 00 00 00 |................|
0x01030 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 |................|
0x01040 41 6c 65 74 68 65 69 61 00 00 00 00 00 00 00 00 |Aletheia........|

COVER
MARKED 4928
GAPS   257216
TOTAL  262144
ties   true

FAIL
mem range     rejected
store range   rejected
read tail     rejected
write tail    rejected
bad width     rejected
addr overflow rejected
ptr walk      rejected
ptr diff      rejected
array fit     rejected
array index   rejected
bad layout    rejected
bad struct    rejected
bad string    rejected
overlap mark  rejected

SUMMARY
mem     : true
marks   : true
find    : true
paper   : true
ptr     : true
array   : true
layout  : true
record  : true
string  : true
boot    : true
stack   : true
span    : true
hexdump : true
cover   : true
fail    : true
ALETHEIA MEM OK
```

逐段看。头部打印机器大小、地址范围、启动图。`SIZE` 是 262144，`MACH` 是 `0x00000..0x3ffff`，五个区域各占一行。`MARKS` 段打印五个标注，标签、起点、终点、大小四列对齐。`FIND` 段打印十个地址的归属：启动区首尾、代码区起点、数据区首尾、栈区末尾、空闲区首尾，以及两个空隙。区内地址给出标签和偏移，空隙打印 `(gap)`。

`PAPER TAPE` 段打印八个 32 位值。每一行左边是地址，中间是四个字节，接着是十六进制值，最后是无符号和有符号两列。`0xffffffff` 的字节是 `ff ff ff ff`，无符号是 4294967295，有符号是 -1。`0xdeadbeef` 的字节是 `ef be ad de`，无符号是 3735928559，有符号是 -559038737。`0x80000000` 的无符号是 2147483648，有符号是 -2147483648。同一个位模式，两种解释，两列并排。

`PTR` 段打印八个元素地址。起点 0x01000，步长 4，第八个元素在 0x0101C。每一行的 `ADDR`、`EXPECT` 相等，`DELTA` 等于下标，`OK` 为真。这张表验证了 $a_i=a_0+4i$，也验证了 `ptr_walk`、`ptr_diff`、`addr_of` 三条路径算出同一个结果。

`ARRAY` 段打印 12 字节数组的基地址 0x01060、个数 12、和 78、第 7 个元素 0x01067、网格 `(1,2)` 的地址 0x01066。和是 $1+2+\cdots+12=78$；下标 7 的字节是 8；网格按行优先展开，`(1,2)` 是第 1 行第 2 列，展平下标是 $1\cdot4+2=6$，地址是 `0x01060+6=0x01066`。

`LAYOUT` 段打印五个字段的偏移和大小。`id` 在 0，`flags` 在 4，`kind` 在 6，`tag` 在 7，`next` 在 8，总大小 12。五个偏移和手算表一致。`RECORD` 段打印按这些偏移写入的字段值：`id=7`、`flags=3`、`kind=1`、`tag=2`、`next=0x01000`。写入和读取都经过 `field_ptr` 加存储窗口，没有直接下标数组。`INSTANCE 0` 是 0x01020，`INSTANCE 1` 是 0x0102C，后者是前一个实例加 12 字节。

`STRING` 段打印 `Aletheia` 和长度 8。`BOOT` 段打印启动签名 `ALETHEIA`。`STACK` 段打印栈顶地址 0x3F1F8、帧值 42、返回地址 0x00100。栈区从 0x3F000 到 0x3F1FF，栈顶在 0x3F200，两个字分别放在 0x3F1F8 和 0x3F1FC，正好在栈区的高端。

`SPAN` 段打印五段区间的起点、终点、大小和有效性，然后打印四个布尔值：`ORDER` 为真表示五段按地址递增，`DISJOINT` 为真表示两两不重叠，`INSIDE` 为真表示五段都在整机内，`COPY` 为真表示启动签名的前八个字节复制到数据区暂存区后逐字节一致。`COPY` 这一项把 `span_fill` 和 `span_copy` 都跑了一遍：先清零，再复制，再读回。

`HEXDUMP` 段打印数据区前 80 字节，五行。第一行是八个 32 位值的前四个，第二行是后四个，第三行是记录，第四行是零填充，第五行是字符串。十六进制列和 ASCII 列对齐，`Aletheia` 在最后一行开头。`COVER` 段打印覆盖 4928、空隙 257216、总计 262144，`ties` 为真。

`FAIL` 段打印十四种失败：机器窗口越界、存储窗口越界、尾部读越界、尾部写越界、宽度 3、地址乘法溢出、指针走步溢出、指针对不齐、数组总量溢出、数组下标越界、对齐不是 2 的幂、手工结构体对齐错误、字符串容量越界、标注重叠。十四种全部拒绝。失败时函数返回假，不修改内存，不崩溃。`SUMMARY` 段打印十五个布尔值，全部为真，最后一行 `ALETHEIA MEM OK`，返回码 0。

验收标准有十条：

1. 机器大小 262144 字节，地址范围 0x00000 到 0x3FFFF，所有访问都经过 `AletheiaMem`。
2. 五个区域按地址排序、互不重叠、完全在机器内，覆盖 4928 字节，空隙 257216 字节，总和 262144。
3. 八个 32 位值的字节、十六进制、无符号、有符号四列正确，全 1 显示 4294967295 和 -1。
4. 八个元素地址满足 $a_i=a_0+4i$，`ptr_walk`、`ptr_diff`、`addr_of` 三方一致。
5. 12 字节数组的和为 78，下标 7 的地址为 0x01067，网格 `(1,2)` 的地址为 0x01066。
6. 五个字段偏移 0、4、6、7、8 和总大小 12 与手算一致，记录字段按偏移正确读回，第二个实例地址为 0x0102C。
7. 字符串长度 8，启动签名 `ALETHEIA`，栈顶帧值 42、返回地址 0x00100。
8. 五段区间排序、不重叠、都在机器内，8 字节复制逐字节一致。
9. 十六进制转储五行，每行 16 字节，地址递增 16，ASCII 列正确。
10. 十四种非法操作全部拒绝，编译零警告，ASan/UBSan 无报错，输出确定且不超过 80 列。

十条全部通过，程序打印 `ALETHEIA MEM OK` 并返回 0。输出最宽一行 74 列，共 149 行，重复运行完全一致。程序不打印宿主地址、不打印时间、不依赖未初始化内存。启动签名、数据值、记录、字符串、栈值都在每次运行开始时重新写入，标注表在每次构造时清零，所有显示都能复现。

这个程序也在 ASan 和 UBSan 下跑过。所有读写都先检查描述符和区间，所有标注都先检查排序和边界，所有地址乘法都用 64 位中间值，所有布局计算都检查对齐和溢出。两个消毒器都没有报错，输出和普通编译一致。程序没有动态分配，没有泄露，没有越界，没有未定义行为。

如果某一项检查失败，输出会是什么样？对应段的布尔值变成假，`SUMMARY` 里那一行打印 `false`，最后一行打印 `ALETHEIA MEM BROKEN`，返回码变成 1。程序不会在第一次失败时停下，所以后面的段仍然会运行，读者能看到是一个地方坏了还是整片都坏了。比如 `ARRAY` 失败，后面的 `LAYOUT`、`RECORD` 仍然会打印，`SUMMARY` 里只有 `array` 是假；再比如 `mem` 构造失败，程序在头部就打印 `ALETHEIA MEM BROKEN` 并返回 1，因为描述符不可用时后面的检查没有意义。两种失败路径都写死在 `main` 里，不靠异常，不靠 `setjmp`，不靠全局错误码。

总装程序能证明什么，不能证明什么，要分开。它能证明：在同一块数组上，九种看法的边界检查互相一致；所有读写都经过同一个入口；覆盖等式成立；指针公式、数组公式、布局公式、小端公式都能落到可执行的检查；七种视图都能在同一台机器上构造、写入、读回。它不能证明：这台机器能跑一段真正的程序，因为第三卷才有指令；它能分配内存，因为第二卷才有分配器；它能处理任意输入，因为演示数据是固定的。总装是地基验收，不是整机验收。整机验收要等第四卷。

## 九、交给第二卷

这一章定义了 `AletheiaMem`，一个由起点和大小组成的机器描述符。在它之上，第一卷的七种视图全部接通：区间、指针、数组、结构体、字符串、存储、纸带。它们共享一块 256 KiB 数组，共享一套地址，共享一条从 `store_has` 到 `mem_has` 再到 `peek_u8` 和 `poke_u8` 的访问路径。

交给第二卷的接口是：

```c
struct AletheiaMem {
    AletheiaAddr base;
    uint32_t size;
};

bool aletheia_mem_make(struct AletheiaMem *m, AletheiaAddr base,
                       uint32_t size);
bool aletheia_mem_ok(const struct AletheiaMem *m);
bool aletheia_mem_has(const struct AletheiaMem *m, AletheiaAddr addr,
                      uint32_t width);
bool aletheia_peek_u8(const struct AletheiaMem *m, AletheiaAddr addr,
                      AletheiaByte *out);
bool aletheia_poke_u8(const struct AletheiaMem *m, AletheiaAddr addr,
                      AletheiaByte value);
bool aletheia_mem_read_le(const struct AletheiaMem *m, AletheiaAddr addr,
                          uint32_t width, uint32_t *out);
bool aletheia_mem_write_le(const struct AletheiaMem *m, AletheiaAddr addr,
                           uint32_t width, uint32_t value);
bool aletheia_write_u32(const struct AletheiaMem *m, AletheiaAddr addr,
                        uint32_t value);
bool aletheia_addr_of(const struct AletheiaMem *m, AletheiaAddr base,
                      uint32_t index, uint32_t elem_size,
                      AletheiaAddr *out);

bool aletheia_span_ok(const struct AletheiaMem *m,
                      struct AletheiaSpan s);
bool aletheia_ptr_make(const struct AletheiaMem *m, AletheiaAddr addr,
                       uint32_t elem_size, struct AletheiaPtr *out);
bool aletheia_arr_make(const struct AletheiaMem *m, AletheiaAddr addr,
                       uint32_t elem_size, uint32_t count,
                       struct AletheiaArr *out);
bool aletheia_offset_table(const struct AletheiaMem *m,
                           AletheiaAddr base,
                           const struct AletheiaFieldSpec *spec,
                           uint32_t n, struct AletheiaStruct *out);
bool aletheia_str_make(const struct AletheiaMem *m, AletheiaAddr addr,
                       uint32_t capacity, struct AletheiaStr *out);
bool aletheia_store_make(const struct AletheiaMem *m, AletheiaAddr base,
                         uint32_t size, struct AletheiaStore *out);
bool aletheia_tape_make(const struct AletheiaMem *m, AletheiaAddr base,
                        uint32_t size, struct AletheiaTape *out);
```

第二卷会在这个描述符上盖分配器。分配器把一块大区域切成小块，每块有一个块头，块头记录大小和状态；空闲块串成链表；分配时找到足够大的块，必要时拆分；释放时把块标成空闲，必要时和相邻块合并。所有块头、链表指针、用户数据都住在同一块 256 KiB 数组里，所有读写仍然经过 `AletheiaMem`。第一卷给的 `base`、`size`、`mem_read_le`、`mem_write_le`、`addr_of`，以及区间、指针、数组、结构体、字符串、存储、纸带七种视图，就是第二卷的全部地基。

第一卷到此结束。九章，九个零件，一块内存。第一章看到一个字节，第二章看到一段区间，第三章看到负数，第四章看到指针，第五章看到数组，第六章看到结构体，第七章看到字符串，第八章看到整数，第九章看到纸带，第十章看到整台机器。下一卷从这台机器上切第一块内存，给它装上块头，串成链表，让“有什么”变成“怎么放”。
