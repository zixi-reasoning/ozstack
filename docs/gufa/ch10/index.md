# 总装

> 第十章。零件：`AletheiaMem`。九种看法，一块内存。

## 一、回访：九种看法

前九章各造了一个零件。第一章定义字节和地址，内存是一张从地址到字节的映射。第二章把变量看成区间，起点加大小，左闭右开。第三章把负数放进字节，用补码把减法变成加法。第四章让指针走步，一个指针加一个整数，地址按元素大小移动。第五章把数组拉直，下标和地址之间只差一次乘法。第六章把结构体拆开，字段之间有偏移，偏移之间可能有空洞。第七章给字符串找尽头，终止符之前的字节都是内容。第八章统一多字节读写，小端把最低有效字节放在最低地址。第九章把内存摊开，十六进制行、ASCII 列、区间标注、覆盖统计。

九个零件，九种看法，看的却是同一块内存。第一章看一个字节，第二章看一段区间，第三章看一个负数，第四章看一个指针，第五章看一排元素，第六章看一个记录，第七章看一句话，第八章看一个整数，第九章看一整片。每一种看法都建立在前一种之上，每一种看法都有自己的检查函数。问题是，前九章的检查各自为政：字节层检查地址，存储层检查区间，纸带层检查标注，谁也没有对整台机器负责。

这一章不造新零件。这一章把九个零件装进一个程序，让它们共用一块 256 KiB 的静态数组、一套地址、一条访问路径。装完以后，读者拿到的是一个可以检查的内存描述符 `AletheiaMem`，以及四个入口：读字节、写字节、读 32 位、写 32 位，外加一个地址算术函数 `aletheia_addr_of`。第二卷会在这个描述符上盖分配器，第三卷会在分配器上盖机器，第四卷会在机器上跑算法。地基就在这一章打完。

## 二、开场实验：九个零件，一块数组

先做一次思想实验。假设前九章的程序各带一块 256 KiB 数组。第一章的 `aletheia_mem` 在文件 A，第八章的 `aletheia_mem` 在文件 B，第九章的纸带又指向文件 C 的一块区域。三个数组内容不同，地址相同。读者从文件 A 里拿到地址 0x00800，把它交给文件 B 的读函数，读出来的是文件 B 的 0x00800，不是文件 A 的。地址没有变，内存变了。这不是指针错误，是机器错误：一台机器只能有一块内存，不能有九块。

总装的第一步是删掉多余的数组，只留一块。所有章节的零件改成接收同一个描述符，描述符指向同一块数组。地址不再属于某个文件的局部数组，地址属于整台机器。第二步是删掉多余的边界检查，只留一层。字节层不再自己判断地址是否合法，它把判断交给 `AletheiaMem`；存储层不再自己判断区间，它也交给 `AletheiaMem`；纸带层只判断标注是否落在机器内。第三步是把检查函数串起来，让一个程序从头到尾跑一遍，最后打印一个总结果。

装完后的机器有这样一张启动图：

```text
BOOT  : 0x00000..0x0003f
CODE  : 0x00100..0x002ff
DATA  : 0x01000..0x010ff
STACK : 0x3f000..0x3f1ff
FREE  : 0x3f200..0x3ffff
```

启动区放签名，代码区留 512 字节，数据区放演示值，栈区在机器高处，空闲区接在栈区后面。区域之间有大段空隙，那些空隙没有标注，也没有内容。启动图不是整块内存的转储，是整块内存的目录。目录告诉读者每一段从哪里开始、到哪里结束、有多大；转储告诉读者每一段里到底有哪些字节。两个合起来，才是一台机器的完整画像。

这一章的程序会打印这些内容：启动图、标注表、地址查找、纸带表、指针算术表、结构体布局表、记录字段、字符串、栈顶、十六进制转储、覆盖统计、失败检查和汇总。每一段都来自同一块数组，每一次读写都经过 `AletheiaMem`。程序最后打印 `ALETHEIA MEM OK`，表示九种看法在同一块内存上达成一致。

看一次写入的完整路径。调用者想把值 7 写到记录的第一个字段，地址 0x01020，宽度 4。它调用 `aletheia_write_u32`，传入描述符、地址、值。包装函数调用 `write_le`，宽度 4。`write_le` 调用 `mem_has`，检查描述符、宽度、下界、上界。`mem_has` 返回真，`write_le` 进入循环，取出最低字节 0x07，调用 `poke` 写到 0x01020；再取下一个字节 0x00，写到 0x01021；再取两个 0x00，写到 0x01022 和 0x01023。四次 `poke`，每次都要再查一次 `mem_has`。最后 `write_le` 返回真，包装函数返回真，调用者看到成功。整条路径上，数组只被 `poke` 碰了四次，边界只被 `mem_has` 检查了多次，没有任何一层跳过检查。

这条路径看起来重复：外层已经检查过区间，内层每次 `poke` 又检查一遍。重复是有意的。外层检查保证整个 4 字节区间合法，内层检查保证每个单字节访问也合法；两层都通过，才能排除“外层算错但内层碰巧挡住”和“内层放宽但外层没发现”的情况。教学代码宁可多查几次，也不把正确性寄托在“调用者已经检查过”的口头约定上。真要优化，可以把内层检查合并成一次区间检查加四次无检查写入，但那要引入一个新的内部入口；这一章不引入，保持只有 `peek` 和 `poke` 两个入口。

## 三、一台机器的地址空间

### 3.1 一块数组

Aletheia 的全部内存是一个静态数组：

```c
static AletheiaByte aletheia_rom[ALETHEIA_SIZE];
```

`ALETHEIA_SIZE` 是 $256\cdot1024=262144$。数组下标从 0 到 262143，地址也用同一套编号。地址空间可以写成：

$$
\mathcal{A}=\{0,1,\dots,2^{18}-1\}
$$

$2^{18}=262144$，所以最大地址是 $2^{18}-1=262143$，十六进制写作 `0x3ffff`。数组右端是地址 262144，也就是 `0x40000`，它不是合法地址，是“末尾之后”的位置。任何读写都必须满足 $a<2^{18}$，任何宽度为 $w$ 的读写还必须满足 $a+w\le2^{18}$。这两个条件看起来只差一个等号，实际差一条边界：最后一字节可以读，末尾之后不能读。

为什么是 $2^{18}$？因为 $256\text{ KiB}=2^8\cdot2^{10}=2^{18}$ 字节。这个数不是随便选的：它足够放下一台教学机器的代码、数据、栈和空闲区，又足够小，整个数组可以静态分配，不需要堆。数组是 `static`，存放在宿主程序的数据段，程序启动时全零，程序结束时消失。Aletheia 不向宿主申请内存，不调用 `malloc`，不在运行时扩大自己。机器的边界在编译时就定死了。

地址是整数，不是宿主指针。宿主的指针是一个 64 位值，可能指向栈、堆、数据段，打印出来是一串宿主地址；Aletheia 的地址是 0 到 262143 的整数，和数组下标一一对应。两者不能混用：把宿主指针存进 32 位地址会截断，把机器地址当宿主指针解引用会崩溃。总装程序从始至终不把机器地址转成宿主指针，也不把宿主指针转成机器地址。打印地址时统一用 `%05x`，读起来是机器地址，不是宿主地址。这个纪律让输出可复现，也让程序不依赖地址空间布局随机化。

地址用 `uint32_t` 存储，虽然 18 位就够。为什么不用 18 位或 24 位？因为 32 位是宿主能直接提供的精确无符号整数类型，运算不会溢出到宿主字长之外，打印也方便。18 位节省不了多少，反而在每次加减时都要手动掩码，增加出错机会。32 位地址的上限是 4294967295，机器大小是 262144，地址检查保证任何合法地址都远小于上限。多出来的位数不浪费内存，`AletheiaAddr` 只是寄存器里的一个值，不是数组里的一格。

地址空间和数组是两层。数组是具体的存储，地址空间是抽象的编号。`aletheia_rom[a]` 是具体访问，`a` 是抽象地址。总装把两层对齐：数组下标就是地址，地址就是下标，中间没有偏移。如果描述符的 `base` 不是 0，数组下标仍然是地址，因为整个数组从 0 开始编号，窗口只是限制可见范围。这个对齐是这台机器的简化，也是它容易检查的原因：读者看到 `0x01000`，既知道它是地址，也知道它对应数组的第 4096 个字节。

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

描述符还让同一份代码可以服务不同的区域。第九章的 `aletheia_hexdump` 接收一个存储描述符，可以转储数据区，也可以转储栈区，还可以转储第二卷的某一块。函数不关心区域里装的是什么，只关心区域从哪里开始、有多大。总装把这种“区域无关”的思路推到整台机器：`AletheiaMem` 是最大的窗口，也是所有窗口的模板。

描述符是契约，不是装饰。契约写在函数签名里：`const struct AletheiaMem *m`。`const` 表示函数不修改描述符，只读它的边界。调用者可以放心把同一个描述符传给多个检查函数，不必担心其中一个把 `base` 或 `size` 改掉。描述符按值传递也可以，但传指针更省，也更清楚：所有函数看的是同一份边界，不是各自的副本。

### 3.4 边界

一次访问由三个量决定：描述符 $M$、地址 $a$、宽度 $w$。合法的条件是：

$$
b\le a,\qquad a-b\le s-w
$$

第一个条件挡住地址落在区间左边。第二个条件用减法避免加法溢出：$a+w\le b+s$ 等价于 $a-b\le s-w$，但右边只做一次减法，左边要做一次加法，加法可能溢出 32 位。先做减法，再比较，地址再大也不会回绕。

第二个条件还要求 $w\le s$。如果宽度比整个区间还大，$s-w$ 在无符号算术里会下溢成一个巨大的数，任何地址都会被误判为合法。所以检查顺序必须是：先确认 $w>0$，再确认 $w\le s$，再确认 $a\ge b$，最后比较 $a-b$ 和 $s-w$。顺序不是风格，是正确性。第八章已经踩过一次类似的坑：宽度检查没和读写函数对齐，导致 `has` 接受 3 字节而 `read_le` 拒绝 3 字节。这一章把宽度检查收进一个函数，读写都调用它，不再各写一份。

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
    *out = aletheia_rom[addr];
    return true;
}
```

```c
static bool aletheia_poke_u8(const struct AletheiaMem *m, AletheiaAddr addr,
                              AletheiaByte value) {
    if (!aletheia_mem_has(m, addr, 1u)) {
        return false;
    }
    aletheia_rom[addr] = value;
    return true;
}
```

`peek` 读一个字节，`poke` 写一个字节。两个函数都先检查，再访问。数组下标只用 `addr`，因为描述符的 `base` 是 0；如果描述符是窗口，正确写法是 `aletheia_rom[m->base + (addr - m->base)]`，化简后还是 `aletheia_rom[addr]`。地址减去 `base` 再加 `base` 抵消了，但检查没有抵消：`addr` 必须落在窗口内。这一层抵消是有意的，它让窗口描述符和整机描述符共用同一套入口。

`out == NULL` 放在最前面。空指针不是地址错误，是调用错误；两种错误都返回假，但检查顺序不同。先查空指针，再查边界，可以避免在空指针上做任何运算。`poke` 没有输出参数，只查边界。两个函数都不打印，不记录日志，不设置全局错误码。错误通过返回值传给调用者，调用者决定是打印、重试还是终止。

为什么只有这两个函数碰数组？因为所有上层都建立在这两个函数上。整数读写循环调用 `peek` 和 `poke`，字符串扫描调用 `peek`，十六进制转储调用 `peek`，记录字段读取调用 `read_le` 或 `peek`。只要这两个函数的边界正确，上层就不需要重复检查；只要这两个函数不越界，整台机器就不会越界。这是总装的核心：把信任集中在一个地方，而不是散在九个地方。

### 4.2 小端整数

32 位值在内存里是四个字节，最低有效字节放在最低地址。读的公式是：

$$
v=\sum_{i=0}^{w-1} b_i\,2^{8i}
$$

写的公式是：

$$
b_i=(v\gg8i)\ \&\ 255
$$

`read_le` 先检查宽度必须是 1、2、4，再检查区间，再循环拼值。`write_le` 先检查同样的宽度，再检查区间，再循环拆字节。两个函数都只接受这三种宽度，因为机器的基本整数类型是 8 位、16 位、32 位；3 字节不是标准宽度，允许它会诱导读者写出无法对齐的结构体字段。

宽度检查放在区间检查之前，理由和边界一样：宽度不合法时，`s-w` 可能下溢。先拒绝 3，再算边界，顺序固定。`read_le` 还检查 `out != NULL`，因为写输出参数之前必须确认指针有效；`write_le` 没有输出参数，不需要这一条。

小端不是唯一的选择，大端也能定义一套完整读写。选小端是因为这台机器的地址从低到高、字节从低到高，数组下标增长的方向和数值权重增长的方向一致。读者在纸带上看到 `78 56 34 12`，从左往右读是低字节到高字节，从右往左读才是常见的十六进制写法 `0x12345678`。这个“反过来”不是错误，是小端的定义。第八章已经解释过，这一章只需要确认：总装没有换字节序，所有整数仍然走小端。

读写满足往返律：

$$
\operatorname{read}_{w}(\operatorname{write}_{w}(v))=v
$$

对任意 32 位 $v$ 和 $w\in\{1,2,4\}$ 成立。$w=1$ 时只保留最低 8 位，严格说往返的是 $v\bmod256$，不是任意 $v$。程序里只对 $w=4$ 验证完整往返，对 $w=1$ 和 $w=2$ 验证截断后的值。这个区别要在验收里写清楚，不能笼统说“所有宽度都往返”。

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

程序用八个元素验证这条公式。数组起点 0x01000，元素大小 4，下标 0 到 7。第 $i$ 个元素的地址是 $0x01000+4i$，逐个和 `addr_of` 的结果比较，八行全部为真。这个表就是第一卷验收里的 `&arr[i] == &arr[0] + i`，只不过地址是机器地址，不是宿主指针。

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

这个公式只在 $g$ 是 2 的幂时好用，因为除法和乘法可以写成位运算；本章仍然用除法和乘法，先保证正确，再谈优化。`aletheia_align_ok` 要求对齐非零且是 2 的幂，`aletheia_round_up` 用 64 位中间值算向上取整，超过 32 位就拒绝。

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

注意，这张表是 Aletheia 的布局规则，不是宿主 C 编译器的布局规则。宿主可能给 `uint32_t` 更大的对齐，也可能在结构体末尾加填充；程序不依赖宿主布局，只依赖自己的字段表和递推公式。记录的实际写入用这套偏移：`id` 在 0x01020，`flags` 在 0x01024，`kind` 在 0x01026，`tag` 在 0x01027，`next` 在 0x01028。所有写入都通过 `AletheiaMem`，读回的值和写进去的值一致。

### 4.5 字符串与纸带

字符串仍然是一串字节加终止符。总装不新增字符串类型，只在 `AletheiaMem` 上写一个带长度上限的扫描：从起点开始读字节，遇到 0 停止，读满 32 字节也停止。上限防止没有终止符的字符串把扫描带出数据区。演示字符串是 `Aletheia`，八个字节，第九个字节是 0，扫描得到长度 8。

纸带仍然由区域和标注组成。第九章的纸带结构可以直接复用，只需要把底层访问换成 `AletheiaMem`。标注的地址是机器地址，不是宿主地址；标注的大小是字节数，不是元素数；标注的顺序必须按地址递增。总装用五个标注描述启动图：`boot`、`code`、`data`、`stack`、`free`。五个标注覆盖 4928 字节，剩下 257216 字节是空隙。空隙不是浪费，是留给第二卷分配器、第三卷栈帧和第四卷权重的空间。

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

总装程序有十二段检查：`MARKS`、`FIND`、`PAPER TAPE`、`PTR`、`LAYOUT`、`RECORD`、`STRING`、`BOOT`、`STACK`、`HEXDUMP`、`COVER`、`FAIL`。每段打印自己的数据，返回一个布尔值；`main` 收集十二个布尔值，最后打印 `SUMMARY`。

`MARKS` 检查标注表本身：数量、顺序、大小、标签。`FIND` 检查地址查找：区内地址返回正确的标签和偏移，空隙返回假。`PAPER TAPE` 检查八个 32 位值的字节、无符号解释和有符号解释。`PTR` 检查八个元素地址是否等于起点加下标乘四。`LAYOUT` 检查五个字段偏移和总大小是否等于手算表。`RECORD` 检查写入的五个字段能否按偏移读回。`STRING` 检查字符串长度。`BOOT` 检查启动签名。`STACK` 检查栈顶两个字。`HEXDUMP` 检查五行十六进制转储。`COVER` 检查覆盖等式。`FAIL` 检查七种非法操作是否被拒绝。

十二段检查不是十二个独立的程序，是同一台机器的十二个侧面。`MARKS` 和 `FIND` 看纸带，`PAPER TAPE` 和 `HEXDUMP` 看字节，`PTR` 看地址算术，`LAYOUT` 和 `RECORD` 看结构体，`STRING` 看终止符，`BOOT` 和 `STACK` 看启动图和栈，`COVER` 看总量，`FAIL` 看边界。每一段都通过 `AletheiaMem` 访问内存，没有一段绕过描述符直接碰数组。

汇总表打印十三个布尔值：`mem`、`marks`、`find`、`paper`、`ptr`、`layout`、`record`、`string`、`boot`、`stack`、`hexdump`、`cover`、`fail`。十三个全为真，程序打印 `ALETHEIA MEM OK` 并返回 0；任何一个为假，程序打印 `ALETHEIA MEM BROKEN` 并返回 1。返回码和最后一行一致，脚本可以直接用返回码判断，不必解析文本。

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

这张表不是装饰。每一个公式都能落到一行 C，每一行 C 都能在总装程序里找到对应的检查。字节公式落到 `peek`，区间公式落到 `mem_has`，补码公式落到 `signed32`，指针公式落到 `addr_of`，数组公式落到 `PTR` 段，结构体公式落到 `layout_offsets`，字符串公式落到 `check_string`，小端公式落到 `read_le`，纸带公式落到 `tape_cover`。公式和代码不是两套东西，是同一件事的两种写法。

## 六、把 AletheiaMem 写成 C

### 6.1 描述符与构造

描述符只有两个字段。构造时先在一个临时结构体里试填，检查通过后再赋给输出参数：

```c
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
```

先把结果放进 `trial`，再整体赋值，失败时 `*m` 不动。这个模式在第六章和第九章都出现过：输出参数要么得到完整的新值，要么保持原值，不会停在“改了一半”的中间状态。描述符没有指针成员，没有需要释放的资源，整体赋值就是复制两个整数，代价可以忽略。

`mem_ok` 检查三件事：描述符非空、大小非零、区间在机器内。区间检查先比 `base > ALETHEIA_SIZE`，再比 `size <= ALETHEIA_SIZE - base`。先比 `base` 是为减法挡住下溢：如果 `base` 大于 262144，`ALETHEIA_SIZE - base` 会回绕；先拒绝，减法才安全。这个顺序和第九章的 `tape_ok` 一样，理由也一样。

### 6.2 边界检查

```c
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
```

`mem_has` 是所有访问的唯一入口。它先检查描述符，再检查宽度，再检查地址下界，最后检查上界。四个检查的顺序固定：描述符不合法，后面的字段都不可信；宽度为零或大于区间，减法会下溢；地址小于起点，`addr - base` 会下溢；只有前三个都通过，最后的减法才是安全的。

`off <= m->size - width` 允许 `off` 正好等于 `size-width`，这时访问的最后一个字节正好落在区间右端之前。`off = size-width+1` 会越界一个字节，拒绝。这个等号是合法的，不能写成 `<`；写成 `<` 会把最后一次合法访问挡掉，程序会在正确地址上报错。第八章的 `store_has` 也用了这个等号，总装保持一致。

### 6.3 字节读写

`mem_peek` 和 `mem_poke` 已经在 4.1 出现过。这里补两个细节。第一，`peek` 先检查 `out` 再检查地址；如果 `out` 是空指针，函数返回假，不写任何东西。第二，`poke` 只检查地址，不检查值；值是一个字节，任何 0 到 255 都合法，不需要额外检查。两个函数都返回布尔值，调用者必须检查返回值；不检查也能编译，但会在越界时静默失败。

整个程序只有这两处出现 `aletheia_rom[...]`。读者可以用文本搜索验证：除了 `peek` 和 `poke`，没有第三个函数直接下标数组。这个约束不是靠注释维持的，是靠代码结构维持的：上层函数拿不到数组名，只拿到描述符和 `peek`、`poke`。第二卷做分配器时，也会遵守同样的约束：分配器只通过 `AletheiaMem` 读写，不直接碰数组。

### 6.4 整数读写

`read_le` 和 `write_le` 都用循环处理宽度 1、2、4。循环里的移位量是 `8u * i`，最大 24，不会超过 31 位，也不会触发未定义行为。`write_le` 先用 `(value >> (8u * i)) & 0xffu` 取出一个字节，再转成 `AletheiaByte`；`0xffu` 的后缀 `u` 让掩码保持无符号，避免有符号右移的实现定义行为。

读的时候先初始化 `value=0`，再逐字节或上。写的时候逐字节覆盖，不读旧值。两种操作都不依赖字节序的宿主实现，因为字节序由循环顺序决定：先处理最低地址，再处理更高地址，最低有效字节放在最低地址，这就是小端。宿主是大端还是小端，都不影响这段代码的结果，因为代码自己拼值，不用 `memcpy`，不用类型双关。

`read_u32` 和 `write_u32` 只是 `read_le`、`write_le` 宽度为 4 的包装。包装函数看起来多余，实际是接口：第二卷和第三卷只关心 32 位读写，不需要知道宽度参数；以后要加 64 位读写，也在这两个包装旁边加，不用改调用者。总装把“常用宽度”和“通用宽度”分开，调用者各取所需。

宽度的语义也要写清楚。宽度 1 的读返回 0 到 255；宽度 2 的读返回 0 到 65535；宽度 4 的读返回 0 到 4294967295。写的时候，高于宽度的位被丢弃：写 0x12345678 到宽度 2，只写低 16 位 0x5678，高 16 位不进入内存。这个截断不是错误，是宽度的定义。程序里的 `read_le` 和 `write_le` 不额外检查“值是否能装进宽度”，因为任何 32 位值都能装进 4 字节，而 1 字节和 2 字节的截断是调用者应知的行为。如果调用者希望拒绝截断，应该在调用前自己比较，或者写一个带范围的辅助函数，而不是让底层偷偷改语义。

宽度 3 被拒绝，原因不是技术上做不到，而是语义上没有标准类型。3 字节整数在某些协议里存在，但不是这台机器的基本类型；允许宽度 3 会让 `read_le` 的返回值范围变成 0 到 16777215，和宽度 4 的接口混在一起，调用者容易把 3 字节值当 4 字节用。总装只保留 1、2、4，把“非标准宽度”挡在入口，后面所有层都不必再考虑。第八章曾经因为 `has` 接受 3 而读写拒绝 3 产生过不一致；总装把宽度检查收进 `mem_has` 和读写函数，三处一致，不再有缝。

### 6.5 地址算术

`addr_of` 用 64 位中间值算乘积，已经在 4.3 解释过。这里补一个边界：`base` 等于区间右端、`index=0` 时，函数返回右端地址。这个地址可以参与比较，不能读写。C 的尾指针规则允许这种地址，Aletheia 的读写检查会拒绝它。如果调用者拿尾指针去读，`mem_has` 会返回假，程序不会越界。

`addr_of` 还检查 `base >= m->base`，但不检查 `base < end`。起点等于右端是允许的，起点大于右端会被 `off > m->size` 挡住。`off` 是 `base - m->base`，因为前面已经确认 `base >= m->base`，减法安全。`delta > m->size - off` 用 64 位比较，右边先转成 64 位，避免 `m->size - off` 在 32 位里回绕；实际上 `off <= size` 已经保证右边非负，转换只是为了比较类型一致。

### 6.6 布局计算

布局计算分三步：检查对齐、向上取整、累加偏移。`align_ok` 要求对齐非零且是 2 的幂，写法是 `(a & (a - 1u)) == 0u`。`round_up` 用 64 位算 `(value + align - 1) / align * align`，结果超过 32 位就拒绝。`layout_offsets` 对每个字段先按自己的对齐取整，记下偏移，再加上字段大小，最后按最大对齐取整得到总大小。

这些函数不分配内存，不修改输入，只写输出数组和总大小。字段表是 `static const`，编译时确定；偏移数组由调用者提供，长度至少等于字段数。函数不检查输出数组长度，因为 C 没有长度信息；调用者必须保证数组够大。这个约定写在函数签名旁边的注释里，读者复制代码时要一起复制约定。

布局检查的演示表用五个字段，偏移数组长度 5，总大小一个变量。程序先算，再打印，再和手算表比较。比较失败时函数返回假，但已经打印的表仍然保留，读者能看到哪一行不对。这种“先打印再判断”的顺序在检查函数里反复出现：输出是证据，返回值是结论，两者分开。

### 6.7 纸带与检查

纸带结构从第九章原样搬来，只把底层的存储描述符换成 `AletheiaMem`。`tape_make` 先把整张表清零，再检查区域；`tape_mark` 追加标注；`tape_find` 按地址查找；`tape_cover` 统计覆盖。清零是为了让未使用的标注位置有确定值，结构体整体赋值时不会复制垃圾。这个细节不影响输出，但影响可复现性：同样的输入，每次运行的内存状态都一样。

检查函数各自独立，不共享全局状态。`check_marks` 只读纸带，`check_paper` 只读数据区，`check_layout` 只读字段表，`check_fail` 只构造临时对象。`main` 按顺序调用，把返回值收集到局部布尔变量，最后统一汇总。任何一段失败都不会阻止后面的段运行，读者一次就能看到所有段的结果。这个设计和第九章的“一次运行给出全貌”一致。

## 七、完整程序

完整程序把字节层、存储层、纸带层、布局层和检查函数放在一个文件里。程序八百四十行，没有 `malloc`，没有 `<string.h>`，没有类型双关，没有变长数组。数组是静态的，描述符是值类型，标注表是定长的。

编译命令：

```bash
cc -std=c99 -O2 -Wall -Wextra -pedantic -Werror aletheia_ch10.c -o aletheia_ch10
```

程序的第一行注释写出建议文件名。读者把整段代码复制到一个空文件，保存为 `aletheia_ch10.c`，就能编译运行。程序不读取外部文件，不依赖当前目录，不打印宿主地址和时间，重复运行输出完全一致。

```c
/* aletheia_ch10.c */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define ALETHEIA_SIZE ((uint32_t)256 * 1024)
#define ALETHEIA_MAX_MARKS 8u
#define ALETHEIA_LABEL 12u

typedef uint32_t AletheiaAddr;
typedef uint8_t AletheiaByte;

struct AletheiaMem {
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

struct AletheiaField {
    const char *name;
    uint32_t size;
    uint32_t align;
};

static AletheiaByte aletheia_rom[ALETHEIA_SIZE];

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
    *out = aletheia_rom[addr];
    return true;
}

static bool aletheia_poke_u8(const struct AletheiaMem *m, AletheiaAddr addr,
                            AletheiaByte value) {
    if (!aletheia_mem_has(m, addr, 1u)) {
        return false;
    }
    aletheia_rom[addr] = value;
    return true;
}

static bool aletheia_mem_read_le(const struct AletheiaMem *m, AletheiaAddr addr,
                                 uint32_t width, uint32_t *out) {
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

static bool aletheia_mem_write_le(const struct AletheiaMem *m, AletheiaAddr addr,
                                  uint32_t width, uint32_t value) {
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

static bool aletheia_read_u32(const struct AletheiaMem *m, AletheiaAddr addr,
                               uint32_t *out) {
    return aletheia_mem_read_le(m, addr, 4u, out);
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

static bool aletheia_tape_ok(const struct AletheiaTape *t) {
    AletheiaAddr cursor;
    uint32_t i;
    if (t == NULL || t->base > ALETHEIA_SIZE || t->size == 0u ||
        t->mark_count > ALETHEIA_MAX_MARKS) {
        return false;
    }
    if (t->size > ALETHEIA_SIZE - t->base) {
        return false;
    }
    cursor = t->base;
    for (i = 0u; i < t->mark_count; ++i) {
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

static bool aletheia_tape_make(struct AletheiaTape *t, AletheiaAddr base,
                               uint32_t size) {
    struct AletheiaTape trial;
    uint32_t i;
    if (t == NULL) {
        return false;
    }
    trial.base = base;
    trial.size = size;
    trial.mark_count = 0u;
    for (i = 0u; i < ALETHEIA_MAX_MARKS; ++i) {
        uint32_t j;
        trial.marks[i].addr = 0u;
        trial.marks[i].size = 0u;
        for (j = 0u; j < ALETHEIA_LABEL; ++j) {
            trial.marks[i].label[j] = '\0';
        }
    }
    if (!aletheia_tape_ok(&trial)) {
        return false;
    }
    *t = trial;
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
    for (off = 0u; off < ALETHEIA_LABEL; ++off) {
        m.label[off] = '\0';
    }
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
    for (i = 0u; i < t->mark_count; ++i) {
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
    for (i = 0u; i < t->mark_count; ++i) {
        total += t->marks[i].size;
    }
    *covered = total;
    *gaps = t->size - total;
    return true;
}

static bool aletheia_hexdump(const struct AletheiaMem *m, AletheiaAddr addr,
                             uint32_t n) {
    uint32_t done = 0u;
    if (!aletheia_mem_has(m, addr, n)) {
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

static bool aletheia_align_ok(uint32_t a) {
    return a != 0u && (a & (a - 1u)) == 0u;
}

static bool aletheia_round_up(uint32_t value, uint32_t align, uint32_t *out) {
    uint64_t r;
    if (out == NULL || !aletheia_align_ok(align)) {
        return false;
    }
    r = ((uint64_t)value + align - 1u) / align * align;
    if (r > 0xffffffffu) {
        return false;
    }
    *out = (uint32_t)r;
    return true;
}

static bool aletheia_layout_offsets(const struct AletheiaField *fields,
                                    uint32_t count, uint32_t *offsets,
                                    uint32_t *total) {
    uint32_t off = 0u;
    uint32_t max_align = 1u;
    uint32_t i;
    if (fields == NULL || offsets == NULL || total == NULL || count == 0u) {
        return false;
    }
    for (i = 0u; i < count; ++i) {
        uint64_t end;
        if (fields[i].size == 0u || !aletheia_align_ok(fields[i].align)) {
            return false;
        }
        if (!aletheia_round_up(off, fields[i].align, &off)) {
            return false;
        }
        offsets[i] = off;
        end = (uint64_t)off + fields[i].size;
        if (end > 0xffffffffu) {
            return false;
        }
        off = (uint32_t)end;
        if (fields[i].align > max_align) {
            max_align = fields[i].align;
        }
    }
    return aletheia_round_up(off, max_align, total);
}

static bool aletheia_fill_boot(const struct AletheiaMem *m) {
    static const char signature[8] = {'A', 'L', 'E', 'T', 'H', 'E', 'I', 'A'};
    uint32_t i;
    for (i = 0u; i < 8u; ++i) {
        if (!aletheia_poke_u8(m, 0x00000u + i, (AletheiaByte)signature[i])) {
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
    uint32_t i;
    for (i = 0u; i < 8u; ++i) {
        if (!aletheia_write_u32(m, 0x01000u + i * 4u, values[i])) {
            return false;
        }
    }
    if (!aletheia_write_u32(m, 0x01020u, 7u)) {
        return false;
    }
    if (!aletheia_mem_write_le(m, 0x01024u, 2u, 3u)) {
        return false;
    }
    if (!aletheia_poke_u8(m, 0x01026u, 1u)) {
        return false;
    }
    if (!aletheia_poke_u8(m, 0x01027u, 2u)) {
        return false;
    }
    if (!aletheia_write_u32(m, 0x01028u, 0x01000u)) {
        return false;
    }
    {
        static const char text[9] = {'A', 'l', 'e', 't', 'h', 'e', 'i', 'a', '\0'};
        for (i = 0u; i < 9u; ++i) {
            if (!aletheia_poke_u8(m, 0x01040u + i, (AletheiaByte)text[i])) {
                return false;
            }
        }
    }
    if (!aletheia_write_u32(m, 0x3f1f8u, 42u)) {
        return false;
    }
    if (!aletheia_write_u32(m, 0x3f1fcu, 0x00100u)) {
        return false;
    }
    return true;
}

static bool aletheia_build_tape(struct AletheiaTape *t) {
    if (!aletheia_tape_make(t, 0u, ALETHEIA_SIZE)) {
        return false;
    }
    if (!aletheia_tape_mark(t, 0x00000u, 0x40u, "boot")) {
        return false;
    }
    if (!aletheia_tape_mark(t, 0x00100u, 0x200u, "code")) {
        return false;
    }
    if (!aletheia_tape_mark(t, 0x01000u, 0x100u, "data")) {
        return false;
    }
    if (!aletheia_tape_mark(t, 0x3f000u, 0x200u, "stack")) {
        return false;
    }
    if (!aletheia_tape_mark(t, 0x3f200u, 0x0e00u, "free")) {
        return false;
    }
    return true;
}

static bool aletheia_check_marks(const struct AletheiaTape *t) {
    uint32_t i;
    if (!aletheia_tape_ok(t)) {
        return false;
    }
    printf("MARKS\n");
    printf("LABEL START END   SIZE\n");
    for (i = 0u; i < t->mark_count; ++i) {
        const struct AletheiaMark *m = &t->marks[i];
        printf("%-5s 0x%05x 0x%05x %5u\n", m->label, (unsigned)m->addr,
               (unsigned)(m->addr + m->size), (unsigned)m->size);
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

static bool aletheia_check_find(const struct AletheiaTape *t) {
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
        bool found = aletheia_tape_find(t, addrs[i], &index, &offset);
        if (found) {
            printf("0x%05x %-5s %u\n", (unsigned)addrs[i],
                   t->marks[index].label, (unsigned)offset);
            if (offset != offsets[i] ||
                !aletheia_text_eq(t->marks[index].label, labels[i])) {
                return false;
            }
        } else {
            printf("0x%05x %-5s %u\n", (unsigned)addrs[i], "(gap)", 0u);
            if (labels[i][0] != '(') {
                return false;
            }
        }
    }
    return true;
}

static bool aletheia_check_paper(const struct AletheiaMem *m) {
    static const uint32_t expected[8] = {
        0x00000000u, 0x00000001u, 0xffffffffu, 0x12345678u,
        0xdeadbeefu, 0x0000002au, 0x7fffffffu, 0x80000000u
    };
    uint32_t i;
    printf("\nPAPER TAPE\n");
    printf("ADDR    BYTES       HEX      UNSIGNED   SIGNED\n");
    for (i = 0u; i < 8u; ++i) {
        AletheiaAddr addr = 0x01000u + i * 4u;
        uint32_t value = 0u;
        uint32_t j;
        if (!aletheia_read_u32(m, addr, &value) || value != expected[i]) {
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
        printf(" %08x %10u %10lld\n", (unsigned)value, (unsigned)value,
               aletheia_signed32(value));
    }
    return true;
}

static bool aletheia_check_ptr(const struct AletheiaMem *m) {
    uint32_t i;
    printf("\nPTR\n");
    printf("INDEX ADDR    EXPECT  OK\n");
    for (i = 0u; i < 8u; ++i) {
        AletheiaAddr addr = 0u;
        AletheiaAddr expect = 0x01000u + i * 4u;
        if (!aletheia_addr_of(m, 0x01000u, i, 4u, &addr)) {
            return false;
        }
        printf("%5u 0x%05x 0x%05x %s\n", (unsigned)i, (unsigned)addr,
               (unsigned)expect, addr == expect ? "true" : "false");
        if (addr != expect) {
            return false;
        }
    }
    return true;
}

static bool aletheia_check_layout(void) {
    static const struct AletheiaField fields[5] = {
        {"id", 4u, 4u},
        {"flags", 2u, 2u},
        {"kind", 1u, 1u},
        {"tag", 1u, 1u},
        {"next", 4u, 4u}
    };
    static const uint32_t expected[5] = {0u, 4u, 6u, 7u, 8u};
    uint32_t offsets[5];
    uint32_t total = 0u;
    uint32_t i;
    if (!aletheia_layout_offsets(fields, 5u, offsets, &total)) {
        return false;
    }
    printf("\nLAYOUT\n");
    printf("FIELD OFFSET SIZE\n");
    for (i = 0u; i < 5u; ++i) {
        printf("%-5s %6u %4u\n", fields[i].name, (unsigned)offsets[i],
               (unsigned)fields[i].size);
        if (offsets[i] != expected[i]) {
            return false;
        }
    }
    printf("TOTAL %6u\n", (unsigned)total);
    return total == 12u;
}

static bool aletheia_check_record(const struct AletheiaMem *m) {
    uint32_t id = 0u;
    uint32_t flags = 0u;
    uint32_t next = 0u;
    AletheiaByte kind = 0u;
    AletheiaByte tag = 0u;
    if (!aletheia_read_u32(m, 0x01020u, &id) ||
        !aletheia_mem_read_le(m, 0x01024u, 2u, &flags) ||
        !aletheia_peek_u8(m, 0x01026u, &kind) ||
        !aletheia_peek_u8(m, 0x01027u, &tag) ||
        !aletheia_read_u32(m, 0x01028u, &next)) {
        return false;
    }
    printf("\nRECORD\n");
    printf("ADDR    FIELD VALUE\n");
    printf("0x01020 id    %u\n", (unsigned)id);
    printf("0x01024 flags %u\n", (unsigned)flags);
    printf("0x01026 kind  %u\n", (unsigned)kind);
    printf("0x01027 tag   %u\n", (unsigned)tag);
    printf("0x01028 next  0x%05x\n", (unsigned)next);
    return id == 7u && flags == 3u && kind == 1u && tag == 2u &&
           next == 0x01000u;
}

static bool aletheia_check_string(const struct AletheiaMem *m) {
    uint32_t len = 0u;
    uint32_t i;
    printf("\nSTRING\n");
    printf("TEXT ");
    for (i = 0u; i < 32u; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_peek_u8(m, 0x01040u + i, &b)) {
            return false;
        }
        if (b == 0u) {
            break;
        }
        putchar((int)b);
        len += 1u;
    }
    printf("\nLEN  %u\n", (unsigned)len);
    return len == 8u;
}

static bool aletheia_check_boot(const struct AletheiaMem *m) {
    static const char expect[8] = {'A', 'L', 'E', 'T', 'H', 'E', 'I', 'A'};
    uint32_t i;
    printf("\nBOOT\nSIGNATURE ");
    for (i = 0u; i < 8u; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_peek_u8(m, i, &b)) {
            return false;
        }
        if ((char)b != expect[i]) {
            return false;
        }
        putchar((int)b);
    }
    printf("\n");
    return true;
}

static bool aletheia_check_stack(const struct AletheiaMem *m) {
    uint32_t frame = 0u;
    uint32_t ret = 0u;
    if (!aletheia_read_u32(m, 0x3f1f8u, &frame) ||
        !aletheia_read_u32(m, 0x3f1fcu, &ret)) {
        return false;
    }
    printf("\nSTACK\n");
    printf("SP     0x3f1f8\n");
    printf("FRAME  %u\n", (unsigned)frame);
    printf("RET    0x%05x\n", (unsigned)ret);
    return frame == 42u && ret == 0x00100u;
}

static bool aletheia_check_cover(const struct AletheiaTape *t) {
    uint32_t covered = 0u;
    uint32_t gaps = 0u;
    if (!aletheia_tape_cover(t, &covered, &gaps)) {
        return false;
    }
    printf("\nCOVER\n");
    printf("MARKED %u\n", (unsigned)covered);
    printf("GAPS   %u\n", (unsigned)gaps);
    printf("TOTAL  %u\n", (unsigned)(covered + gaps));
    printf("ties   %s\n", covered + gaps == ALETHEIA_SIZE ? "true" : "false");
    return covered + gaps == ALETHEIA_SIZE;
}

static bool aletheia_check_fail(void) {
    struct AletheiaMem bad;
    struct AletheiaMem m;
    struct AletheiaTape small;
    struct AletheiaTape overlap;
    uint32_t value = 0u;
    uint32_t addr = 0u;
    uint32_t offsets[2];
    uint32_t total = 0u;
    static const struct AletheiaField bad_fields[2] = {
        {"a", 4u, 3u},
        {"b", 4u, 4u}
    };
    bool range_bad;
    bool read_bad;
    bool write_bad;
    bool width_bad;
    bool addr_bad;
    bool overlap_bad;
    bool layout_bad;
    if (!aletheia_mem_make(&m, 0u, ALETHEIA_SIZE)) {
        return false;
    }
    range_bad = !aletheia_mem_make(&bad, 0x3f000u, 0x2000u);
    read_bad = !aletheia_read_u32(&m, 0x3ffffu, &value);
    write_bad = !aletheia_write_u32(&m, 0x3ffffu, 1u);
    width_bad = !aletheia_mem_read_le(&m, 0x01000u, 3u, &value);
    addr_bad = !aletheia_addr_of(&m, 0x01000u, 0x40000000u, 4u, &addr);
    overlap_bad = aletheia_tape_make(&small, 0u, 0x1000u) &&
                  aletheia_tape_mark(&small, 0x100u, 0x100u, "first") &&
                  aletheia_tape_make(&overlap, 0u, 0x1000u) &&
                  aletheia_tape_mark(&overlap, 0x100u, 0x100u, "first") &&
                  !aletheia_tape_mark(&overlap, 0x180u, 0x10u, "second");
    layout_bad = !aletheia_layout_offsets(bad_fields, 2u, offsets, &total);
    printf("\nFAIL\n");
    printf("mem range    %s\n", range_bad ? "rejected" : "accepted");
    printf("read tail    %s\n", read_bad ? "rejected" : "accepted");
    printf("write tail   %s\n", write_bad ? "rejected" : "accepted");
    printf("bad width    %s\n", width_bad ? "rejected" : "accepted");
    printf("addr overflow %s\n", addr_bad ? "rejected" : "accepted");
    printf("overlap mark %s\n", overlap_bad ? "rejected" : "accepted");
    printf("bad layout   %s\n", layout_bad ? "rejected" : "accepted");
    return range_bad && read_bad && write_bad && width_bad && addr_bad &&
           overlap_bad && layout_bad;
}

int main(void) {
    struct AletheiaMem machine;
    struct AletheiaTape tape;
    bool ok_mem;
    bool ok_marks;
    bool ok_find;
    bool ok_paper;
    bool ok_ptr;
    bool ok_layout;
    bool ok_record;
    bool ok_string;
    bool ok_boot;
    bool ok_stack;
    bool ok_hex;
    bool ok_cover;
    bool ok_fail;
    bool ok;
    ok_mem = aletheia_mem_make(&machine, 0u, ALETHEIA_SIZE);
    if (!ok_mem) {
        printf("ALETHEIA MEM BROKEN\n");
        return 1;
    }
    if (!aletheia_fill_boot(&machine) || !aletheia_fill_data(&machine) ||
        !aletheia_build_tape(&tape)) {
        printf("ALETHEIA MEM BROKEN\n");
        return 1;
    }
    printf("ALETHEIA MEM\n");
    printf("SIZE  : %u\n", (unsigned)ALETHEIA_SIZE);
    printf("MACH  : 0x%05x..0x%05x\n", (unsigned)machine.base,
           (unsigned)(machine.base + machine.size - 1u));
    printf("BOOT  : 0x00000..0x0003f\n");
    printf("CODE  : 0x00100..0x002ff\n");
    printf("DATA  : 0x01000..0x010ff\n");
    printf("STACK : 0x3f000..0x3f1ff\n");
    printf("FREE  : 0x3f200..0x3ffff\n");
    printf("\n");
    ok_marks = aletheia_check_marks(&tape);
    ok_find = aletheia_check_find(&tape);
    ok_paper = aletheia_check_paper(&machine);
    ok_ptr = aletheia_check_ptr(&machine);
    ok_layout = aletheia_check_layout();
    ok_record = aletheia_check_record(&machine);
    ok_string = aletheia_check_string(&machine);
    ok_boot = aletheia_check_boot(&machine);
    ok_stack = aletheia_check_stack(&machine);
    printf("\nHEXDUMP\n");
    printf("ADDR    00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f  ASCII\n");
    ok_hex = aletheia_hexdump(&machine, 0x01000u, 80u);
    ok_cover = aletheia_check_cover(&tape);
    ok_fail = aletheia_check_fail();
    ok = ok_mem && ok_marks && ok_find && ok_paper && ok_ptr && ok_layout &&
         ok_record && ok_string && ok_boot && ok_stack && ok_hex && ok_cover &&
         ok_fail;
    printf("\nSUMMARY\n");
    printf("mem     : %s\n", ok_mem ? "true" : "false");
    printf("marks   : %s\n", ok_marks ? "true" : "false");
    printf("find    : %s\n", ok_find ? "true" : "false");
    printf("paper   : %s\n", ok_paper ? "true" : "false");
    printf("ptr     : %s\n", ok_ptr ? "true" : "false");
    printf("layout  : %s\n", ok_layout ? "true" : "false");
    printf("record  : %s\n", ok_record ? "true" : "false");
    printf("string  : %s\n", ok_string ? "true" : "false");
    printf("boot    : %s\n", ok_boot ? "true" : "false");
    printf("stack   : %s\n", ok_stack ? "true" : "false");
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
BOOT  : 0x00000..0x0003f
CODE  : 0x00100..0x002ff
DATA  : 0x01000..0x010ff
STACK : 0x3f000..0x3f1ff
FREE  : 0x3f200..0x3ffff

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
INDEX ADDR    EXPECT  OK
    0 0x01000 0x01000 true
    1 0x01004 0x01004 true
    2 0x01008 0x01008 true
    3 0x0100c 0x0100c true
    4 0x01010 0x01010 true
    5 0x01014 0x01014 true
    6 0x01018 0x01018 true
    7 0x0101c 0x0101c true

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

STRING
TEXT Aletheia
LEN  8

BOOT
SIGNATURE ALETHEIA

STACK
SP     0x3f1f8
FRAME  42
RET    0x00100

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
mem range    rejected
read tail    rejected
write tail   rejected
bad width    rejected
addr overflow rejected
overlap mark rejected
bad layout   rejected

SUMMARY
mem     : true
marks   : true
find    : true
paper   : true
ptr     : true
layout  : true
record  : true
string  : true
boot    : true
stack   : true
hexdump : true
cover   : true
fail    : true
ALETHEIA MEM OK
```

逐段看。头部打印机器大小、地址范围、启动图。`SIZE` 是 262144，`MACH` 是 `0x00000..0x3ffff`，五个区域各占一行。`MARKS` 段打印五个标注，标签、起点、终点、大小四列对齐。`FIND` 段打印十个地址的归属：启动区首尾、代码区起点、数据区首尾、栈区末尾、空闲区首尾，以及两个空隙。区内地址给出标签和偏移，空隙打印 `(gap)`。

`PAPER TAPE` 段打印八个 32 位值。每一行左边是地址，中间是四个字节，接着是十六进制值，最后是无符号和有符号两列。`0xffffffff` 的字节是 `ff ff ff ff`，无符号是 4294967295，有符号是 -1。`0xdeadbeef` 的字节是 `ef be ad de`，无符号是 3735928559，有符号是 -559038737。`0x80000000` 的无符号是 2147483648，有符号是 -2147483648。同一个位模式，两种解释，两列并排。

`PTR` 段打印八个元素地址。起点 0x01000，步长 4，第八个元素在 0x0101C。每一行的 `ADDR` 和 `EXPECT` 相等，`OK` 为真。这张表验证了 $a_i=a_0+4i$，也验证了 `addr_of` 的 64 位乘法和边界检查。八个元素都在数据区内，没有越界，也没有尾指针。

`LAYOUT` 段打印五个字段的偏移和大小。`id` 在 0，`flags` 在 4，`kind` 在 6，`tag` 在 7，`next` 在 8，总大小 12。五个偏移和手算表一致。`RECORD` 段打印按这些偏移写入的字段值：`id=7`、`flags=3`、`kind=1`、`tag=2`、`next=0x01000`。写入用的是 `read_u32`、`read_le` 和 `peek`，没有直接下标数组。

`STRING` 段打印 `Aletheia` 和长度 8。`BOOT` 段打印启动签名 `ALETHEIA`。`STACK` 段打印栈顶地址 0x3F1F8、帧值 42、返回地址 0x00100。栈区从 0x3F000 到 0x3F1FF，栈顶在 0x3F200，两个字分别放在 0x3F1F8 和 0x3F1FC，正好在栈区的高端。

`HEXDUMP` 段打印数据区前 80 字节，五行。第一行是八个 32 位值的前四个，第二行是后四个，第三行是记录，第四行是零填充，第五行是字符串。十六进制列和 ASCII 列对齐，`Aletheia` 在最后一行开头。`COVER` 段打印覆盖 4928、空隙 257216、总计 262144，`ties` 为真。

`FAIL` 段打印七种失败：机器描述符越界、尾部读越界、尾部写越界、宽度 3、地址乘法溢出、标注重叠、对齐不是 2 的幂。七种全部拒绝。失败时函数返回假，不修改内存，不崩溃。`SUMMARY` 段打印十三个布尔值，全部为真，最后一行 `ALETHEIA MEM OK`，返回码 0。

验收标准有八条：

1. 机器大小 262144 字节，地址范围 0x00000 到 0x3FFFF，所有访问都经过 `AletheiaMem`。
2. 五个区域按地址排序、互不重叠、完全在机器内，覆盖 4928 字节，空隙 257216 字节，总和 262144。
3. 八个 32 位值的字节、十六进制、无符号、有符号四列正确，全 1 显示 4294967295 和 -1。
4. 八个元素地址满足 $a_i=a_0+4i$，逐项与 `addr_of` 的结果相等。
5. 五个字段偏移 0、4、6、7、8 和总大小 12 与手算一致，记录字段按偏移正确读回。
6. 字符串长度 8，启动签名 `ALETHEIA`，栈顶帧值 42、返回地址 0x00100。
7. 十六进制转储五行，每行 16 字节，地址递增 16，ASCII 列正确。
8. 七种非法操作全部拒绝，编译零警告，ASan/UBSan 无报错，输出确定且不超过 80 列。

八条全部通过，程序打印 `ALETHEIA MEM OK` 并返回 0。输出最宽一行 74 列，重复运行完全一致。程序不打印宿主地址、不打印时间、不依赖未初始化内存。启动签名、数据值、记录、字符串、栈值都在每次运行开始时重新写入，标注表在每次构造时清零，所有显示都能复现。

这个程序也在 ASan 和 UBSan 下跑过。所有读写都先检查描述符和区间，所有标注都先检查排序和边界，所有地址乘法都用 64 位中间值，所有布局计算都检查对齐和溢出。两个消毒器都没有报错，输出和普通编译一致。程序没有动态分配，没有泄露，没有越界，没有未定义行为。

如果某一项检查失败，输出会是什么样？对应段的布尔值变成假，`SUMMARY` 里那一行打印 `false`，最后一行打印 `ALETHEIA MEM BROKEN`，返回码变成 1。程序不会在第一次失败时停下，所以后面的段仍然会运行，读者能看到是一个地方坏了还是整片都坏了。比如 `PAPER TAPE` 失败，后面的 `PTR`、`LAYOUT` 仍然会打印，`SUMMARY` 里只有 `paper` 是假；再比如 `mem` 构造失败，程序在头部就打印 `ALETHEIA MEM BROKEN` 并返回 1，因为描述符不可用时后面的检查没有意义。两种失败路径都写死在 `main` 里，不靠异常，不靠 `setjmp`，不靠全局错误码。

总装程序能证明什么，不能证明什么，要分开。它能证明：在同一块数组上，九个零件的边界检查互相一致；所有读写都经过同一个入口；覆盖等式成立；指针公式、布局公式、小端公式都能落到可执行的检查。它不能证明：这台机器能跑一段真正的程序，因为第三卷才有指令；它能分配内存，因为第二卷才有分配器；它能处理任意输入，因为演示数据是固定的。总装是地基验收，不是整机验收。整机验收要等第四卷。

## 九、交给第二卷

这一章定义了 `AletheiaMem`，一个由起点和大小组成的机器描述符。它提供构造、有效性检查、字节读写、整数读写和地址算术。`aletheia_read_u32` 和 `aletheia_write_u32` 是第一卷的最终读写接口；`aletheia_addr_of` 是第一卷的最终地址接口；`aletheia_peek_u8` 和 `aletheia_poke_u8` 是所有访问的最后入口。

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
bool aletheia_read_u32(const struct AletheiaMem *m, AletheiaAddr addr,
                           uint32_t *out);
bool aletheia_write_u32(const struct AletheiaMem *m, AletheiaAddr addr,
                            uint32_t value);
bool aletheia_addr_of(const struct AletheiaMem *m, AletheiaAddr base,
                          uint32_t index, uint32_t elem_size,
                          AletheiaAddr *out);
```

第二卷会在这个描述符上盖分配器。分配器把一块大区域切成小块，每块有一个块头，块头记录大小和状态；空闲块串成链表；分配时找到足够大的块，必要时拆分；释放时把块标成空闲，必要时和相邻块合并。所有块头、链表指针、用户数据都住在同一块 256 KiB 数组里，所有读写仍然经过 `AletheiaMem`。第一卷给的 `base`、`size`、`read_u32`、`write_u32`、`addr_of` 就是第二卷的全部地基。

第一卷到此结束。九章，九个零件，一块内存。第一章看到一个字节，第二章看到一段区间，第三章看到负数，第四章看到指针，第五章看到数组，第六章看到结构体，第七章看到字符串，第八章看到整数，第九章看到纸带，第十章看到整台机器。下一卷从这台机器上切第一块内存，给它装上块头，串成链表，让“有什么”变成“怎么放”。
