# 指针算术

> 第四章。零件：`AletheiaPtr`。一个指针不是地址，是地址加一个元素大小。

## 一、回访：补码留下的负数

第三章把负数放进了字节。八位的 -1 是 `0xff`，32 位的 -4 是 `0xfffffffc`。这些模式在当时只是读法，现在要拿去做一件更具体的事：让地址往回走。

假设有一个地址 0x00100，我们想往回走四个字节。数学上写 $0x00100-4$，结果是 0x000FC。用补码的模式来算，就是：

$$
0x00000100 + 0xfffffffc = 0x000000fc
$$

最高位的进位被丢掉，剩下的 0x000000FC 就是新地址。这里没有“减号运算”，只有一次 32 位加法。补码把减法变成了加法，指针的负偏移正好用上这一点。

可如果只做 `addr + k`，事情会不对。设 $k=-1$，地址 0x00100 加 -1 得到 0x000FF，这是往回走一个字节。可如果指针指向的是一个四字节整数，往回走一个元素应该走四个字节，得到 0x000FC。差别就在“一个元素”到底是几个字节。

第三章留下的工具有 `aletheia_s32`、`aletheia_neg32` 和 `aletheia_add32`。它们能算有符号的加法，但不知道“元素大小”这回事。你可以手动写 `addr + k * 4`，可这个 4 是从哪里来的？如果换成一个八字节的结构体，这个 4 就要改成 8；如果换成一个字节的字符，又要改成 1。手动乘一次不难，难的是让每一次走步都记得乘，而且乘得对。

所以这一章要加一层：把“地址”和“元素大小”绑在一起，变成一个指针。走步的时候，指针自己知道该乘多少。这个绑定不是装饰，它是数组能够用下标访问的前提。

地址空间是一条线。0 在左端，262143 在右端，每个字节是线上的一个点。往前走是加，往后走是减。指针走步就是在这条线上按固定步长跳。这个图像简单，可它解释了为什么地址可以比较大小，为什么负偏移有意义，为什么越界只有两个方向。数组后面会在这条线上占一段连续的区间，结构体会在这条线上占一段有空洞的区间，都是这条线的用法。

先做一个最小实验。同一个基地址，同一个 $k=1$，一个指针指向字节，一个指针指向四字节整数。前者走到 0x00101，后者走到 0x00104。两个结果都正确，因为“一”的含义不同。指针的加法不是地址的加法，是元素的加法。

## 二、开场实验：同一个 1，两个地址

我们把实验写成一张小表，先不解释定义，只看结果：

```text
base = 0x00100
byte pointer : p + 1 -> 0x00101
int pointer  : p + 1 -> 0x00104
```

两行只差一个“指针指向什么”。第一行的对象是一个字节，加一就走一个字节。第二行的对象是一个四字节整数，加一就走四个字节。机器没有变，基地址没有变，$k$ 也没有变，变的只是元素大小。

如果读者以前写过 C，这个结果可能太熟悉了，熟悉到不像一个问题。可正是这个“熟悉”值得拆开。C 的 `int *p; p + 1` 之所以走四个字节，不是因为编译器偷偷知道 4，而是因为 `p` 的类型是 `int *`，类型里带着 `sizeof(int)`。指针的加法规则是：地址加上 $k$ 乘以所指类型的大小。类型系统把这个乘法藏起来了。

我们的机器没有 C 的类型系统。`AletheiaAddr` 就是一个 `uint32_t`，它不知道自己指向什么。你要么在每次走步时手动乘，要么把大小和地址放进同一个结构体。前者容易忘，后者可以检查。这一章选后者。

把两个指针写成对：

```text
p_byte = (0x00100, 1)
p_int  = (0x00100, 4)
```

它们的地址字段相同，大小字段不同。`p_byte + 1` 的地址是 $0x00100+1\times1=0x00101$，`p_int + 1` 的地址是 $0x00100+1\times4=0x00104$。一条公式同时解释了两行。公式里的 $s$ 就是大小字段。

这也说明“指针等于整数”是一个危险的简化。指针里确实有一个整数，地址；但指针还带着一个单位。你把单位丢掉，剩下的整数只能做字节级的地址运算，不能做元素级的指针运算。很多指针错误，根源就是把这两个层次混在一起。

再看一个反例。假设你把地址 0x00100 加 1 得到 0x00101，然后把这个地址当成“下一个整数”的地址。可下一个整数从 0x00104 开始，0x00101 落在第一个整数的中间。你读出来的四个字节，是第一个整数的后三个字节加上第二个整数的第一个字节。这个值既不是第一个整数，也不是第二个整数。机器不会报错，它只会给你一个看似合理的数。指针的大小字段就是为了避免这种“半个对象”的地址。

所以开场实验的结论不是“指针加法要乘 4”，而是“指针加法要乘所指对象的大小”。4 只是这一天的例子。明天指向一个 8 字节的结构体，乘的就是 8；指向一个 1 字节的字符，乘的就是 1。公式不变，$s$ 变。

同一个地址，换一个步长，就换了一种分组。0x100 开始的四个字节是一个整数，0x101 开始的四个字节是另一个“整数”，后者跨过了第一个整数的后三个字节和第二个整数的第一个字节。两个值都不是原来那个整数。指针的步长决定它怎么切分这条字节线。你给它 1，它按字节切；给它 4，它按四字节切；给它 8，它按八字节切。切法不同，读出来的东西不同。

## 三、指针不是整数

### 3.1 地址和步长

先把两个字段的类型定下来。地址用 `AletheiaAddr`，也就是 `uint32_t`。元素大小用 `uint32_t`，不用 `size_t`。为什么不用 `size_t`？因为 `size_t` 的宽度由宿主决定，在 64 位机器上通常是 8 字节，在 32 位机器上通常是 4 字节。我们的机器只有 262144 字节，元素大小最大也就是 262144，四个字节足够。用固定宽度的 `uint32_t`，结构体的布局就是 8 字节，打印和比较都稳定。

结构体只有两个字段：

```c
struct AletheiaPtr {
    AletheiaAddr addr;
    uint32_t elem_size;
};
```

第一个字段是对象在机器内存里的起始地址，第二个字段是这个对象占多少个字节。两个字段都是无符号的，因为地址和大小都不应该为负。偏移 $k$ 才是有符号的，它放在函数的参数里，不放在指针里。指针表示“我在哪里、我指向多大的东西”，不表示“我走了几步”。

为什么不用一个字段同时编码地址和大小？因为地址需要 18 位才能覆盖 262144 个字节，大小也需要最多 18 位。把两者塞进一个 32 位整数，位数不够，而且每次取值都要移位和掩码，容易出错。分开两个字段，读起来直接，检查也直接。结构体多占四个字节，在宿主机上不算什么；在书里，清晰比省四个字节重要。

两个 `uint32_t` 字段放在一起，结构体大小是 8 字节，不会有填充。因为两个字段的自然对齐都是 4 字节，第一个从偏移 0 开始，第二个从偏移 4 开始，正好对齐。如果把 `elem_size` 换成 `size_t`，在 64 位宿主上它占 8 字节，结构体会变成 16 字节，第二个字段前面可能还要补 4 个字节。输出就会随宿主变化。书里要的是确定的 8 字节，所以用固定宽度的 `uint32_t`。

为什么不用 `void *` 或者宿主指针？因为这台机器是封闭的。`aletheia_mem` 是一个静态数组，它的元素在宿主机上的地址由操作系统决定，可能是 0x7ffc1234，也可能是别的。那不是我们定义的 0 到 262143。我们的指针必须用机器自己的地址空间，不能把宿主地址混进来。用 `void *` 还会让指针算术变成非标准扩展，编译器不一定允许。用两个整数，规则全部由我们写。

一个指针有效，需要满足两个条件。第一，元素大小大于零。大小为零的对象没有第一个字节，`p+0` 也没有意义，C 里对 `void *` 做算术也是不允许的。第二，整个对象装得下：起始地址加上元素大小不超过 262144。注意是“整个对象”，不只是起始地址。一个四字节对象从 0x3FFFE 开始，起始地址在范围内，可它的最后一个字节在 0x40001，已经出了内存。这种指针必须拒绝。

一个指针有效，只说明它指向的对象在整块内存里，不说明它指向的对象在某个数组里。数组有自己的起点和长度，指针不知道。一个指针可以从数组中间开始，也可以指向数组最后一个元素之后的内存，只要那个对象完整。数组的边界是另一层信息，要等到第五章和元素个数一起引入。今天先把“对象在内存里”这条底线守住。

用公式写，有效性是：

$$
0 \le \operatorname{addr}(p) \le 262144 - s
$$

其中 $s$ 是元素大小。左边的不等式其实自动成立，因为地址是无符号的；右边的不等式是真正的检查。等号允许，因为地址 0x3FFFC 加 4 正好等于 0x40000，对象的最后一个字节是 0x3FFFF，还在内存里。

### 3.2 为什么 C 的指针加法不是地址加法

C 的指针算术有一套明确的规则：对一个指向类型 $T$ 的指针 $p$，$p+k$ 的地址是 $p$ 的地址加上 $k\cdot\operatorname{sizeof}(T)$。这里的 $k$ 是元素个数，不是字节数。指针相减 $q-p$ 得到的是元素个数，不是字节差。两个规则互为逆运算。

这套规则不是随便定的。它让数组下标成立：

$$
a[i] = *(a+i)
$$

如果 $a+i$ 只加一个字节，那么 $a[1]$ 就会从第二个字节开始，而不是从第二个元素开始。为了拿到第二个元素，你得写 $*(a+i\cdot s)$，每个下标都要乘一次。C 把这次乘法放进指针算术，让下标表达式保持简单。代价是：指针的类型必须知道 $s$。

C 的类型系统把步长编进指针类型。`char *` 的步长是 1，`int *` 的步长通常是 4，`struct Foo *` 的步长是 `sizeof(struct Foo)`。同一个地址，转成不同的指针类型，`+1` 的结果就不同。这不是编译器随心所欲，是类型在告诉你“这个地址指向多大的对象”。我们的结构体把类型换成运行时字段，效果一样，但更显式。你可以打印 `elem_size`，看它到底是多少。

我们的结构体把这个乘法写回显式形式：

$$
\operatorname{addr}(p+k)=\operatorname{addr}(p)+k\cdot s
$$

这条公式是本章的定义。它看起来像 C 的规则，但它是我们自己的规则，因为 $s$ 存在结构体里，不依赖宿主的类型系统。你可以用它走字节、走整数、走结构体，只要把 $s$ 设对。

指针相减也照搬这个单位。两个指针的地址差是 $\operatorname{addr}(q)-\operatorname{addr}(p)$，这个差是字节数。要变成元素个数，得除以 $s$：

$$
k=\frac{\operatorname{addr}(q)-\operatorname{addr}(p)}{s}
$$

这个除法必须除得尽。如果两个地址的差不是 $s$ 的整数倍，说明它们没有落在同一个元素网格上，不能相减。C 里对不指向同一数组的指针相减是未定义行为；我们的机器更直接：除不尽就返回失败。

还有一个 C 的细节值得提前说：C 允许“指向最后一个元素之后一个位置”的指针，叫 one-past-the-end。循环里常用它做终止条件。我们的 `AletheiaPtr` 不采用这个约定，因为它表示一个完整的对象，不是一个数组位置。一个对象必须整个装进内存，所以 `addr + s <= 262144`。数组的末尾和 one-past 的问题，等到第五章有数组和元素个数时再处理。今天先把“指针指向一个对象”这件事做干净。

one-past 指针在 C 里很有用。遍历数组时，循环条件常写成 `p != end`，其中 `end` 指向最后一个元素之后。这个指针不能解引用，只能比较。我们的 `AletheiaPtr` 不表示这种位置，因为它要求整个对象装得下。数组层会用“起始地址 + 元素个数 + 下标”来表示范围，不用 one-past。这样每个下标都能检查，也不会出现一个“指向对象之外”的指针。

### 3.3 一次走步要带哪些信息

一次走步需要四样东西：起点指针 $p$、偏移 $k$、输出指针 $q$、以及一个成功或失败的标志。起点和终点都是 `struct AletheiaPtr`，偏移是 `int32_t`，标志是 `bool`。函数不修改起点，只写终点。这样调用者可以保留原指针，也可以把结果和预期比较。

为什么偏移用 `int32_t`，不用 `int`？因为 `int` 的宽度由宿主决定，可能是 16 位、32 位或 64 位。书里要的是确定的 32 位有符号数，范围从 -2147483648 到 2147483647。这个范围足够表示任何实际的下标，也足够大到能触发溢出检查。用固定宽度，输出才可复现。

为什么乘法要用 `int64_t`？因为 $k\cdot s$ 可能超过 32 位。最坏情况下，$k$ 是 2147483647，$s$ 是 262144，乘积约是 $5.6\times10^{14}$，需要 49 位。32 位乘法会回绕，回绕后的结果可能看起来像一个合法的小偏移，从而把越界检查骗过去。这个陷阱在第六节会详细展开。今天先记住：偏移和大小都先转成 `int64_t`，乘完再检查。

为什么走步要返回新的结构体，而不是直接修改传入的指针？因为函数式的结果更容易检查。调用者拿到一个 `bool`，知道走步有没有成功；拿到一个 `q`，知道成功时走到了哪里。如果直接修改 `p`，失败时 `p` 可能已经被写坏，调用者还要想办法恢复。多一个输出参数，少一类错误。

走步还要保持元素大小不变。$p+k$ 指向的对象和 $p$ 指向的对象是同一类型，大小当然一样。如果大小变了，那就不是同一个指针在走，而是换了一个类型。C 里不同类型的指针不能直接相减，我们的 `aletheia_ptr_diff` 也会拒绝大小不同的两个指针。

最后，走步要检查两边边界。下界是 0，上界是 $262144-s$。下界用 `next < 0` 判断，上界用 `next > 262144-s` 判断。两个判断都在 `int64_t` 里做，避免无符号减法的下溢。检查通过后，才把 `next` 转回 `AletheiaAddr`。这个转换是安全的，因为 `next` 已经落在 $[0,262144-s]$ 里，而 $s\ge1$，所以 `next` 最大是 262143，能放进 32 位无符号数。

## 四、四条公式

### 4.1 走步

设指针 $p$ 的地址是 $a$，元素大小是 $s$。走 $k$ 步后的地址是：

$$
\operatorname{addr}(p+k)=a+k\cdot s
$$

这个定义对正 $k$、负 $k$ 和零都成立。$k=0$ 时得到 $a$，这是原地不动：

$$
\operatorname{addr}(p+0)=\operatorname{addr}(p)
$$

$k=1$ 时得到 $a+s$，这是下一个对象。$k=-1$ 时得到 $a-s$，这是上一个对象。步长 $s$ 不变，因为 $p+k$ 和 $p$ 指向同一种对象。公式里没有“地址加一”，只有“地址加 $k$ 个 $s$”。

这条公式有三种读法。算术读法：新地址等于旧地址加偏移乘大小。几何读法：在字节线上按步长跳 $k$ 次。类型读法：$p+k$ 还是同一种指针，只是位置变了。三种读法说的是同一件事。你做题时用算术，画图时用几何，写代码时用类型。三种语言能互相翻译，说明公式抓到了本质。

把它写成 C，核心只有一行：

```c
delta = (int64_t)k * (int64_t)p.elem_size;
next = (int64_t)p.addr + delta;
```

两个乘数都先转成 `int64_t`，乘法才不会在 32 位里回绕。加法的结果也放在 `int64_t` 里，因为 `next` 可能暂时是负数，不能放在无符号类型里。

### 4.2 指针差

已知两个指针 $p$ 和 $q$，它们指向同一种对象，大小都是 $s$。从 $p$ 走到 $q$ 需要多少步？

$$
k=\frac{\operatorname{addr}(q)-\operatorname{addr}(p)}{s}
$$

分子是字节差，分母是元素大小，商是元素个数。这个商可能为正，也可能为负。$q$ 在 $p$ 后面时为正，$q$ 在 $p$ 前面时为负。两个指针地址相同、大小相同时，商是 0。

这个除法有一个前提：分子必须能被 $s$ 整除。如果除不尽，说明两个地址不在同一个元素网格上，$q$ 不是一个合法的“某个元素起点”。比如 $p=0x100$，$q=0x106$，$s=4$，字节差是 6，6 除以 4 余 2。$q$ 落在某个四字节对象的中间，不能当成某个元素的起点。函数应该返回失败，而不是把商截断成 1。

余数不是废物。字节差除以元素大小，商是走过的元素个数，余数是落在对象内部的第几个字节。余数为零，说明正好落在起点；余数不为零，说明落在中间。指针差只接受余数为零的情况，因为“从 $p$ 走几步到 $q$”要求 $q$ 是一个元素起点。余数不为零时，你可以说“$q$ 在 $p$ 后面一个元素再加两个字节”，但这不是指针差的答案。

C 的整数除法对负数的行为是向零截断。比如 $-6/4$ 得到 $-1$，不是 $-2$。我们先检查整除，再除，所以不依赖截断方向。只要余数为零，商就是精确的；余数不为零，直接拒绝。这样写，正负都一样。

### 4.3 对齐

“地址差能被 $s$ 整除”这个条件，也叫对齐。它不是要求地址本身是 $s$ 的倍数，而是要求两个地址在同一个模 $s$ 的等价类里。比如 $s=4$，地址 0x100 和 0x104 的差是 4，能除尽；0x101 和 0x105 的差也是 4，也能除尽。两个地址都不是 4 的倍数，可它们指向同一类位置，相差一个元素。

对齐在指针相减里是必须的，在指针走步里不是。走步可以从任意地址出发，只要整个对象装得下。你有一个四字节对象从 0x101 开始，它占 0x101 到 0x104，虽然起始地址不是 4 的倍数，但对象本身是完整的。`p+1` 走到 0x105，也是合法的。机器不强制对象按 4 对齐，因为我们的内存是一个字节数组，任何地址都可以放任何字节。真实硬件可能有对齐要求，那是另一层约束，今天不引入。

指针差的对齐检查，本质上是在问：这两个指针是不是同一个数组里的两个元素？如果差能被 $s$ 整除，答案是“可能是”；如果差不能被 $s$ 整除，答案是“一定不是”。我们的函数只做这个必要条件，不检查它们是否真的在同一个数组里。数组的边界和元素个数，要等到第五章。

对齐不是要求地址本身是 4 的倍数。0x101 和 0x105 相差 4，两个地址都不是 4 的倍数，可它们指向同一类位置。指针差只关心两个地址的差，不关心它们各自的绝对值。走步也不要求起始地址对齐，因为对象可以从任意字节开始。真实 CPU 可能要求整数地址按 4 对齐，可我们的机器是一块字节数组，没有这个限制。以后讲结构体对齐时，会把“地址对齐”和“指针差对齐”分开。

### 4.4 边界

走步的结果必须落在内存里，而且要装得下整个对象。条件写成两边：

$$
0 \le \operatorname{addr}(p)+k\cdot s \le 262144-s
$$

左边是下界，右边是上界。右边为什么是 $262144-s$，不是 $262143$？因为指针指向的是对象的起点，对象的最后一个字节是 $\operatorname{addr}+s-1$。最后一个字节必须小于 262144，也就是 $\operatorname{addr}+s-1\le262143$，移项得到 $\operatorname{addr}\le262144-s$。如果只检查起点小于 262144，一个从 0x3FFFE 开始的四字节对象就会被放过，可它的最后一个字节在 0x40001，已经出了内存。

上界的检查可以写成 `next > (int64_t)(ALETHEIA_SIZE - p.elem_size)`。`ALETHEIA_SIZE` 是 262144，`p.elem_size` 已经保证大于零且不超过 262144，所以减法不会下溢。结果是 `uint32_t`，转成 `int64_t` 再比较，避免 `next` 为负数时和无符号数比较出怪结果。

下界的检查是 `next < 0`。`next` 是 `int64_t`，可以为负。只有两个检查都通过，才把 `next` 转成 `AletheiaAddr`。这个转换不是“截断”，是“范围已经确认后的收窄”，所以安全。

走步和差还有一个互逆关系。如果 $q=p+k$ 走步成功，那么从 $q$ 走 $-k$ 步应该回到 $p$：

$$
\operatorname{walk}(p,k)=q \Longrightarrow \operatorname{walk}(q,-k)=p
$$

这个关系是验收里的一条。它同时检查了正负偏移、边界和元素大小。只要有一边走错，往返就对不上。

## 五、手工推演

### 5.1 字节步长

先拿一个字节指针走一遍。基地址 0x00100，元素大小 1，偏移从 -2 到 2：

```text
k=-2  0x00100 + (-2)*1 = 0x000fe
k=-1  0x00100 + (-1)*1 = 0x000ff
k= 0  0x00100 +   0*1  = 0x00100
k= 1  0x00100 +   1*1  = 0x00101
k= 2  0x00100 +   2*1  = 0x00102
```

每一行都只是加一个字节。负偏移用到补码，但在这个例子里，$0x100-1=0xFF$ 太熟，看不出补码的作用。等到四字节步长，负偏移才会跨过更多的位。

### 5.2 四字节步长

基地址还是 0x00100，元素大小 4，偏移从 -1 到 2：

```text
k=-1  0x00100 + (-1)*4 = 0x000fc
k= 0  0x00100 +   0*4  = 0x00100
k= 1  0x00100 +   1*4  = 0x00104
k= 2  0x00100 +   2*4  = 0x00108
```

$k=1$ 走四个字节，到达 0x104。这个地址是下一个整数的起点。$k=2$ 再走四个字节，到达 0x108。$k=-1$ 往回走四个字节，到达 0x0FC。注意 0x0FC 不是 0x0FF：往回走一个元素是四个字节，不是三个。

把两个表并排放，差别一目了然。同一个 $k=1$，字节指针走 1，整数指针走 4。公式里的 $s$ 把两张表统一起来。

0x0FC 和 0x0FF 只差三个字节，可它们代表不同的位置。0x0FC 是上一个四字节对象的起点，0x0FF 是当前对象的最后一个字节。指针往回走一个元素，落在 0x0FC；如果只减一，落在 0x0FF，那是指向对象内部的指针，不是指向上一个对象。指针算术的单位错了，地址就会落在“半个对象”上。

### 5.3 负偏移

负偏移在十六进制里容易算错，因为要借位。算 $0x00100-4$：

```text
0x00100 - 0x004 = 0x000fc
```

从 0x100 借一位，0x100 变成 0x0FC。再算 $0x00100-8$：

```text
0x00100 - 0x008 = 0x000f8
```

如果元素大小是 4，$k=-2$ 先算 $k\cdot s=-8$，再加到 0x100，得到 0x0F8。不要先算地址减一得到 0x0FF，再减三次；那样容易漏掉借位。先算乘积，再做一次加法，步骤少，错误也少。

补码在这里的作用是让负数乘法有一个确定的 32 位模式。$-8$ 的模式是 `0xfffffff8`，加 0x100 得到 `0x000000f8`，进位丢掉。你在纸上可以写减法，在机器里走的是加法。两种写法结果一样，因为补码保证了它们一致。

### 5.4 边界推演

取内存的最后一个四字节对象。地址空间是 0 到 0x3FFFF，最后一个字节是 0x3FFFF。一个四字节对象如果从 0x3FFFC 开始，占 0x3FFFC、0x3FFFD、0x3FFFE、0x3FFFF 四个字节，正好到顶。所以 0x3FFFC 是最后一个合法的四字节起点。

```text
base 0x3fffc, s=4
k= 0 -> 0x3fffc, 对象 [0x3fffc, 0x40000)  合法
k= 1 -> 0x40000, 对象 [0x40000, 0x40004)  越界
k=-1 -> 0x3fff8, 对象 [0x3fff8, 0x3fffc)  合法
```

$k=1$ 的起始地址 0x40000 已经等于 262144，不在地址空间里。即使不看对象，起点也越界了。$k=0$ 的起点合法，对象也刚好装下。$k=-1$ 往回走四个字节，落在 0x3FFF8，对象结束于 0x3FFFC，合法。

再看下界。基地址 0x00000，元素大小 4：

```text
base 0x00000, s=4
k=-1 -> -4       越界
k= 0 -> 0x00000  合法
```

$k=-1$ 的起始地址是 -4，在无符号地址空间里不存在。函数返回失败。这个例子说明为什么 `next` 要放在有符号的 `int64_t` 里算：如果直接在 `uint32_t` 里减，-4 会回绕成 0xFFFFFFFC，然后被误认为是一个很大的合法地址。

0x40000 是最后一个字节之后的地址。它可以作为区间的右端点，写作 `[0x3fffc, 0x40000)`，但不能作为对象的起点。因为一个对象从 0x40000 开始，第一个字节就在内存外面。区间的右端点和对象的起点是两个不同的概念。第二章的区间用右开区间，正好能表达这个区别：右端点可以等于内存大小，起点不能。

### 5.5 指针差推演

拿几个地址算指针差，元素大小 4：

```text
a=0x00108, b=0x00100  (0x108-0x100)/4 = 8/4  = 2
a=0x00100, b=0x00108  (0x100-0x108)/4 = -8/4 = -2
a=0x00106, b=0x00100  (0x106-0x100)/4 = 6/4  = 1 余 2，失败
a=0x0010a, b=0x00100, s=2  (0x10a-0x100)/2 = 10/2 = 5
```

第一行说明 $a$ 在 $b$ 后面两个元素。第二行说明 $a$ 在 $b$ 前面两个元素。第三行的字节差是 6，不是 4 的倍数，$a$ 落在某个元素的中间，失败。第四行换成两个字节的元素，字节差 10 能被 2 整除，商是 5，成功。

如果两个指针的大小不同，比如一个 4、一个 2，差没有统一的单位，函数直接失败。这对应 C 里“不同类型的指针不能相减”的规则。你不能问“一个四字节对象和一个两字节对象相差几个元素”，因为“元素”没有共同的定义。

两个不同大小的指针相减，没有共同的单位。你不能问“一个四字节对象和一个两字节对象相差几个元素”，因为“元素”对它们不是同一个东西。C 里不同类型的指针不能直接相减，我们的函数也拒绝。如果你确实想比较它们的位置，只能比较地址，不能比较元素个数。地址比较是字节级的，元素差是类型级的，两个层次不要混。

## 六、溢出与宽度

现在把最危险的情况摆出来。偏移是 32 位有符号数，元素大小最大是 262144。两者的乘积可能远超 32 位。如果乘法在 32 位里做，结果会回绕，回绕后的值可能看起来很小，从而骗过边界检查。

先看最大正偏移。$k=2147483647$，$s=4$：

```text
精确乘积: 2147483647 * 4 = 8589934588 = 0x1fffffffc
低 32 位 : 0xfffffffc = -4
```

精确乘积是 8589934588，需要 33 位才能表示。32 位只保留低 32 位，得到 0xFFFFFFFC，也就是 -4。如果你用这个 -4 去加基地址 0x100，得到 0x0FC。0x0FC 是一个合法的四字节起点，边界检查会通过。于是，一个偏移了两亿多的走步，被当成了往回走一个元素。这就是回绕骗过检查的过程。

再看最小负偏移。$k=-2147483648$，$s=4$：

```text
精确乘积: -2147483648 * 4 = -8589934592 = -0x200000000
低 32 位 : 0x00000000 = 0
```

精确乘积是 -8589934592，低 32 位全是 0。如果你用这个 0 去加基地址 0x100，得到 0x100，原地不动。边界检查也会通过。一个向后的巨大偏移，被当成了零偏移。

这两个例子说明，乘法必须在更宽的类型里做。`int64_t` 至少有 64 位，能装下 $-8.6\times10^9$ 到 $+8.6\times10^9$ 的范围。实际上，32 位偏移乘 18 位大小，最多需要 50 位左右，64 位足够。乘完以后，`next` 是一个 64 位有符号数，可以直接和 0 以及 $262144-s$ 比较，不会回绕。

为什么选 `int64_t`，不选 `uint64_t`？因为偏移可能是负数，乘积也可能是负数。无符号的 64 位装不下负数，会把 -4 变成 18446744073709551612，边界检查就乱了。`int64_t` 能同时表示正负，范围也足够。为什么不用 `long long`？因为 `long long` 的宽度至少 64 位，但不保证正好 64 位；`int64_t` 是固定宽度，书里要的是确定的行为。

为什么不用无符号的 64 位？因为 $k$ 可能是负数，乘出来也可能是负数。如果用 `uint64_t`，负数会变成一个巨大的正数，比较 `next < 0` 永远不成立，下界检查就失效了。有符号的 `int64_t` 能同时表示正负，适合这个场景。

上界的表达式 $262144-s$ 也要小心。如果 $s$ 大于 262144，减法会下溢。所以 `aletheia_ptr_make` 先检查 $s\le262144$，`aletheia_ptr_walk` 再调用 `aletheia_ptr_ok`，确保进入减法时 $s$ 在范围内。检查的顺序是有意的：先验证前提，再做算术。

检查的顺序也有讲究。先检查大小大于零、不超过内存，再算 `262144-s`，减法才不会下溢。先检查地址不超过 `262144-s`，建立指针时才不会产生一个越界的起点。`make` 管建立，`ok` 管使用，`walk` 管走步，三层各管一段。你把检查合并成一句，可能省几行代码，但出错时不知道是哪一层没守住。

指针差的商也要检查范围。地址空间只有 262144 个字节，两个地址的差最多 262143，除以最小的 $s=1$，商最多 262143，远小于 `INT32_MAX`。看起来不用检查，可接口是通用的，未来地址空间可能变大，或者有人复用这个函数。商先放在 `int64_t` 里，再和 `INT32_MIN`、`INT32_MAX` 比较，最后才转成 `int32_t`。多这一步，不会出错。

## 七、把 AletheiaPtr 写成 C

### 7.1 结构体

结构体只有两个字段，前面已经定过。这里再写一遍，因为它是整章的支点：

```c
struct AletheiaPtr {
    AletheiaAddr addr;
    uint32_t elem_size;
};
```

`addr` 是对象起点，`elem_size` 是对象大小。两个字段都是无符号的。大小为零的指针没有意义，`aletheia_ptr_make` 会拒绝。大小超过整个内存也没有意义，同样拒绝。地址加上大小超过内存，还是拒绝。三个拒绝条件合起来，保证一个刚建立的指针指向一个完整的对象。

### 7.2 建立和检查

建立指针的函数做三件事：检查输出指针不为空，检查大小在 $(0,262144]$ 之间，检查地址不超过 $262144-s$。最后把两个字段写进输出结构体。

```c
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
```

检查函数 `aletheia_ptr_ok` 重复了后两个条件。为什么要重复？因为结构体可以被复制、被赋值、被别的函数传进来。`make` 只保证它自己写出的值合法，不能保证世界上所有的结构体都合法。`ok` 是最后一道门，任何走步、读写、相减之前都要过一遍。重复几条比较，换来的是不会对着一个坏指针做算术。

防御性检查看起来重复，其实是在对付“值可能被改过”这件事。结构体是值类型，可以被赋值、被传参、被存进数组。一个刚建立的指针是合法的，复制几次以后可能被改成大小为零，或者地址越界。`ok` 不假设调用者守规矩，它每次都重新检查。这个习惯在后面的内存层、数组层、结构体层都会保留。

```c
static bool aletheia_ptr_ok(struct AletheiaPtr p) {
    if (p.elem_size == 0u || p.elem_size > ALETHEIA_SIZE) {
        return false;
    }
    return p.addr <= ALETHEIA_ADDR_MAX - p.elem_size;
}
```

这两个函数都不打印，也不修改全局状态。它们只回答“行不行”。把判断和输出分开，测试才好写：你可以直接调 `ok`，不用抓终端输出。

### 7.3 走步

走步函数是本章的核心。它先验证起点，再在 `int64_t` 里算乘积和加法，再检查两边边界，最后写输出。

```c
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
```

注意输出的 `elem_size` 还是原来的 `p.elem_size`。走步不改变类型，只改变位置。如果这里写成别的数，下一次走步的单位就变了，往返也对不上。

往返的单位必须一致。去的时候用 $s$，回来的时候还用 $s$，才能回到原点。如果去的时候用 4，回来的时候用 2，走同样的步数，地址会差一倍。指针结构体里保存 `elem_size`，就是为了让每一次走步都用同一个单位。你可以把 `elem_size` 想成指针的“刻度”，刻度变了，读数就变了。

注意 `next` 的类型是 `int64_t`。它不是“为了保险随便放大”，而是因为 32 位装不下乘积。第六节的两个例子已经说明，32 位乘法会把一个巨大的正偏移变成 -4，把一个巨大的负偏移变成 0。两个结果都能骗过边界检查。`int64_t` 让乘积保持精确，检查才有意义。

### 7.4 指针差

指针差先检查大小相同，再检查两个指针都有效，然后算字节差，检查整除，最后把商收窄到 `int32_t`。

```c
static bool aletheia_ptr_diff(struct AletheiaPtr a, struct AletheiaPtr b,
                              int32_t *out) {
    int64_t diff;
    int64_t quotient;
    if (out == NULL || a.elem_size != b.elem_size) {
        return false;
    }
    if (!aletheia_ptr_ok(a) || !aletheia_ptr_ok(b)) {
        return false;
    }
    diff = (int64_t)a.addr - (int64_t)b.addr;
    if (diff % (int64_t)a.elem_size != 0) {
        return false;
    }
    quotient = diff / (int64_t)a.elem_size;
    if (quotient < (int64_t)INT32_MIN || quotient > (int64_t)INT32_MAX) {
        return false;
    }
    *out = (int32_t)quotient;
    return true;
}
```

整除检查放在除法之前。C 的 `%` 对负数给出的余数符号和被除数相同，但我们只关心它是不是零。是零就整除，不是零就失败。商的范围检查放在最后，因为 `quotient` 已经是 `int64_t`，和 `INT32_MIN`、`INT32_MAX` 比较不会溢出。

### 7.5 读写

指针最终要落到字节上。读一个字节，就是读指针地址处的那个字节；写一个字节，就是写那个地址。两个函数都先验证指针，再调用第一章的字节层。

```c
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
```

这里只读写对象的第一个字节，不读写整个对象。为什么？因为“把一个四字节整数读出来”涉及字节顺序，是第八章的事。今天先把“指针能定位到一个字节”做出来。等有了小端读写，`aletheia_ptr_read_u8` 会成为更上层函数的基石。

## 八、完整程序

把上面的片段拼起来，再加上检查表和输出，就是一个完整的单文件程序。程序分五层：字节层、指针层、检查层、打印层、主函数。字节层还是第一章的 `aletheia_peek_u8` 和 `aletheia_poke_u8`；指针层是本章的 `aletheia_ptr_make`、`aletheia_ptr_walk`、`aletheia_ptr_diff`；检查层把预期结果和实际结果比较；打印层把每个结果写成一行；主函数按表调用。

五层各有各的责任。字节层只认地址和字节，不知道对象；指针层知道对象大小，不知道数组；检查层知道预期结果，不知道内存布局；打印层只负责格式；主函数负责组织顺序。每一层都可以单独测试。你把打印塞进指针函数，测试就要抓输出；你把检查塞进字节层，字节层就变得又大又慢。分层不是洁癖，是为了让错误有地方定位。

程序不读文件，不分配内存，不依赖时间、随机数或宿主地址。所有输出都是确定的。你可以把它保存成 `aletheia_ch04.c`，用 `cc -std=c99 -O2 -Wall -Wextra -pedantic` 编译，然后运行。输出应该和下一节一致。

```c
/* aletheia_ch04.c */
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

/* 一个指针 = 一个地址 + 一个元素大小。建立时必须装得下整个元素。 */
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

/* addr(p + k) = addr(p) + k * elem_size，全部在 int64_t 里算。 */
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

/* 指针相减：先除元素大小，除不尽就是错位的指针。 */
static bool aletheia_ptr_diff(struct AletheiaPtr a, struct AletheiaPtr b,
                              int32_t *out) {
    int64_t diff;
    int64_t quotient;
    if (out == NULL || a.elem_size != b.elem_size) {
        return false;
    }
    if (!aletheia_ptr_ok(a) || !aletheia_ptr_ok(b)) {
        return false;
    }
    diff = (int64_t)a.addr - (int64_t)b.addr;
    if (diff % (int64_t)a.elem_size != 0) {
        return false;
    }
    quotient = diff / (int64_t)a.elem_size;
    if (quotient < (int64_t)INT32_MIN || quotient > (int64_t)INT32_MAX) {
        return false;
    }
    *out = (int32_t)quotient;
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

static void aletheia_print_ptr(struct AletheiaPtr p) {
    if (!aletheia_ptr_ok(p)) {
        printf("invalid");
        return;
    }
    printf("[0x%05x, 0x%05x) size=%u",
           (unsigned)p.addr,
           (unsigned)(p.addr + p.elem_size),
           (unsigned)p.elem_size);
}

static bool aletheia_check_walk(AletheiaAddr base, int32_t k,
                                uint32_t elem_size, AletheiaAddr expected,
                                bool want_ok) {
    struct AletheiaPtr p;
    struct AletheiaPtr q;
    bool made;
    bool walked;
    bool match;
    printf("0x%05x  %4ld  %2u  ",
           (unsigned)base, (long)k, (unsigned)elem_size);
    made = aletheia_ptr_make(base, elem_size, &p);
    if (!made) {
        printf("bad base\n");
        return false;
    }
    walked = aletheia_ptr_walk(p, k, &q);
    if (walked) {
        aletheia_print_ptr(q);
    } else {
        printf("invalid");
    }
    printf("\n");
    if (want_ok) {
        match = walked && q.addr == expected && q.elem_size == elem_size;
    } else {
        match = !walked;
    }
    return match;
}

static bool aletheia_check_diff_sizes(AletheiaAddr a_addr, uint32_t a_size,
                                      AletheiaAddr b_addr, uint32_t b_size,
                                      int32_t expected, bool want_ok) {
    struct AletheiaPtr a;
    struct AletheiaPtr b;
    int32_t d = 0;
    bool made_a;
    bool made_b;
    bool diffed;
    bool match;
    printf("0x%05x  %2u  0x%05x  %2u  ",
           (unsigned)a_addr, (unsigned)a_size,
           (unsigned)b_addr, (unsigned)b_size);
    made_a = aletheia_ptr_make(a_addr, a_size, &a);
    made_b = aletheia_ptr_make(b_addr, b_size, &b);
    if (!made_a || !made_b) {
        printf("bad ptr\n");
        return false;
    }
    diffed = aletheia_ptr_diff(a, b, &d);
    if (diffed) {
        printf("%ld", (long)d);
    } else {
        printf("invalid");
    }
    printf("\n");
    if (want_ok) {
        match = diffed && d == expected;
    } else {
        match = !diffed;
    }
    return match;
}

static bool aletheia_check_roundtrip(AletheiaAddr base, int32_t k,
                                     uint32_t elem_size) {
    struct AletheiaPtr p;
    struct AletheiaPtr q;
    struct AletheiaPtr r;
    bool made;
    bool forward;
    bool backward;
    bool same;
    if (k == INT32_MIN) {
        return false;
    }
    made = aletheia_ptr_make(base, elem_size, &p);
    forward = made && aletheia_ptr_walk(p, k, &q);
    backward = forward && aletheia_ptr_walk(q, (int32_t)(-(int64_t)k), &r);
    same = backward && r.addr == p.addr && r.elem_size == p.elem_size;
    printf("0x%05x  %4ld  %2u  ", (unsigned)base, (long)k,
           (unsigned)elem_size);
    if (backward) {
        printf("0x%05x  0x%05x  %s\n", (unsigned)q.addr,
               (unsigned)r.addr, same ? "true" : "false");
    } else {
        printf("%-9s  %-9s  false\n", "invalid", "invalid");
    }
    return same;
}

static bool aletheia_check_memory(void) {
    struct AletheiaPtr p;
    unsigned i;
    bool ok = aletheia_ptr_make(0x00100u, 4u, &p);
    printf("fill [0x00100, 0x0010c)\n");
    for (i = 0; i < 12u; ++i) {
        struct AletheiaPtr b;
        bool made = aletheia_ptr_make(0x00100u + i, 1u, &b);
        bool wrote = made && aletheia_ptr_write_u8(b, (AletheiaByte)(0x11u * (i + 1u)));
        if (!wrote) {
            ok = false;
        }
    }
    printf("BYTES ");
    for (i = 0; i < 12u; ++i) {
        AletheiaByte v = 0;
        if (aletheia_peek_u8((AletheiaAddr)(0x00100u + i), &v)) {
            printf("%02x ", (unsigned)v);
        }
    }
    printf("\n");
    for (i = 0; i < 3u; ++i) {
        struct AletheiaPtr q;
        AletheiaByte v = 0;
        bool walked = aletheia_ptr_walk(p, (int32_t)i, &q);
        bool read = walked && aletheia_ptr_read_u8(q, &v);
        printf("p+%u ", i);
        if (read) {
            aletheia_print_ptr(q);
            printf(" first=0x%02x\n", (unsigned)v);
        } else {
            printf("invalid\n");
            ok = false;
        }
    }
    return ok;
}

int main(void) {
    bool walk_byte_ok = true;
    bool walk_int_ok = true;
    bool boundary_ok = true;
    bool large_ok = true;
    bool diff_ok = true;
    bool roundtrip_ok = true;
    bool memory_ok;

    printf("ALETHEIA PTR\n");
    printf("SIZE       : %u bytes\n", (unsigned)ALETHEIA_SIZE);
    printf("ADDR RANGE : 0x00000..0x3ffff\n");
    printf("ADDR BYTES : %lu\n", (unsigned long)sizeof(AletheiaAddr));
    printf("SIZE BYTES : %lu\n", (unsigned long)sizeof(uint32_t));
    printf("PTR BYTES  : %lu\n", (unsigned long)sizeof(struct AletheiaPtr));
    printf("\n");

    printf("WALK BYTE\n");
    printf("BASE       K  S  RESULT\n");
    walk_byte_ok = aletheia_check_walk(0x00100u, -2, 1u, 0x000feu, true) && walk_byte_ok;
    walk_byte_ok = aletheia_check_walk(0x00100u, -1, 1u, 0x000ffu, true) && walk_byte_ok;
    walk_byte_ok = aletheia_check_walk(0x00100u, 0, 1u, 0x00100u, true) && walk_byte_ok;
    walk_byte_ok = aletheia_check_walk(0x00100u, 1, 1u, 0x00101u, true) && walk_byte_ok;
    walk_byte_ok = aletheia_check_walk(0x00100u, 2, 1u, 0x00102u, true) && walk_byte_ok;
    printf("\n");

    printf("WALK I32\n");
    printf("BASE       K  S  RESULT\n");
    walk_int_ok = aletheia_check_walk(0x00100u, -1, 4u, 0x000fcu, true) && walk_int_ok;
    walk_int_ok = aletheia_check_walk(0x00100u, 0, 4u, 0x00100u, true) && walk_int_ok;
    walk_int_ok = aletheia_check_walk(0x00100u, 1, 4u, 0x00104u, true) && walk_int_ok;
    walk_int_ok = aletheia_check_walk(0x00100u, 2, 4u, 0x00108u, true) && walk_int_ok;
    printf("\n");

    printf("BOUNDARY\n");
    printf("BASE       K  S  RESULT\n");
    boundary_ok = aletheia_check_walk(0x00000u, -1, 4u, 0u, false) && boundary_ok;
    boundary_ok = aletheia_check_walk(0x00000u, 0, 4u, 0x00000u, true) && boundary_ok;
    boundary_ok = aletheia_check_walk(0x3fffcu, -1, 4u, 0x3fff8u, true) && boundary_ok;
    boundary_ok = aletheia_check_walk(0x3fffcu, 0, 4u, 0x3fffcu, true) && boundary_ok;
    boundary_ok = aletheia_check_walk(0x3fffcu, 1, 4u, 0u, false) && boundary_ok;
    printf("\n");

    printf("LARGE K\n");
    printf("BASE       K             S  RESULT\n");
    large_ok = aletheia_check_walk(0x00100u, INT32_MAX, 4u, 0u, false) && large_ok;
    large_ok = aletheia_check_walk(0x00100u, INT32_MIN, 4u, 0u, false) && large_ok;
    printf("\n");

    printf("DIFF\n");
    printf("A         S   B         S   RESULT\n");
    diff_ok = aletheia_check_diff_sizes(0x00108u, 4u, 0x00100u, 4u, 2, true) && diff_ok;
    diff_ok = aletheia_check_diff_sizes(0x00100u, 4u, 0x00108u, 4u, -2, true) && diff_ok;
    diff_ok = aletheia_check_diff_sizes(0x00106u, 4u, 0x00100u, 4u, 0, false) && diff_ok;
    diff_ok = aletheia_check_diff_sizes(0x0010au, 2u, 0x00100u, 2u, 5, true) && diff_ok;
    diff_ok = aletheia_check_diff_sizes(0x00108u, 4u, 0x00100u, 2u, 0, false) && diff_ok;
    diff_ok = aletheia_check_diff_sizes(0x00100u, 4u, 0x00100u, 4u, 0, true) && diff_ok;
    printf("\n");

    printf("ROUNDTRIP\n");
    printf("BASE       K  S  END       BACK      OK\n");
    roundtrip_ok = aletheia_check_roundtrip(0x00100u, 3, 4u) && roundtrip_ok;
    roundtrip_ok = aletheia_check_roundtrip(0x00100u, -3, 4u) && roundtrip_ok;
    roundtrip_ok = aletheia_check_roundtrip(0x3fffcu, -1, 4u) && roundtrip_ok;
    roundtrip_ok = aletheia_check_roundtrip(0x00000u, 0, 1u) && roundtrip_ok;
    printf("\n");

    printf("MEMORY\n");
    memory_ok = aletheia_check_memory();
    printf("\n");

    printf("SUMMARY\n");
    printf("walk byte : %s\n", walk_byte_ok ? "true" : "false");
    printf("walk int  : %s\n", walk_int_ok ? "true" : "false");
    printf("boundary  : %s\n", boundary_ok ? "true" : "false");
    printf("large k   : %s\n", large_ok ? "true" : "false");
    printf("diff      : %s\n", diff_ok ? "true" : "false");
    printf("roundtrip : %s\n", roundtrip_ok ? "true" : "false");
    printf("memory    : %s\n", memory_ok ? "true" : "false");
    if (walk_byte_ok && walk_int_ok && boundary_ok && large_ok &&
        diff_ok && roundtrip_ok && memory_ok) {
        printf("ALETHEIA PTR OK\n");
        return 0;
    }
    printf("ALETHEIA PTR BROKEN\n");
    return 1;
}
```

程序里的检查函数都返回 `bool`。每一行打印完，函数还会比较实际结果和预期结果。所有行都通过，最后打印 `ALETHEIA PTR OK`；有一行不通过，打印 `ALETHEIA PTR BROKEN` 并返回 1。这样你不需要用眼睛逐行对答案，程序自己会对。

## 九、真实输出与验收

下面是程序在本机上的真实输出。它不是手画的，是把程序跑出来的结果原样贴回来。

```text
ALETHEIA PTR
SIZE       : 262144 bytes
ADDR RANGE : 0x00000..0x3ffff
ADDR BYTES : 4
SIZE BYTES : 4
PTR BYTES  : 8

WALK BYTE
BASE       K  S  RESULT
0x00100    -2   1  [0x000fe, 0x000ff) size=1
0x00100    -1   1  [0x000ff, 0x00100) size=1
0x00100     0   1  [0x00100, 0x00101) size=1
0x00100     1   1  [0x00101, 0x00102) size=1
0x00100     2   1  [0x00102, 0x00103) size=1

WALK I32
BASE       K  S  RESULT
0x00100    -1   4  [0x000fc, 0x00100) size=4
0x00100     0   4  [0x00100, 0x00104) size=4
0x00100     1   4  [0x00104, 0x00108) size=4
0x00100     2   4  [0x00108, 0x0010c) size=4

BOUNDARY
BASE       K  S  RESULT
0x00000    -1   4  invalid
0x00000     0   4  [0x00000, 0x00004) size=4
0x3fffc    -1   4  [0x3fff8, 0x3fffc) size=4
0x3fffc     0   4  [0x3fffc, 0x40000) size=4
0x3fffc     1   4  invalid

LARGE K
BASE       K             S  RESULT
0x00100  2147483647   4  invalid
0x00100  -2147483648   4  invalid

DIFF
A         S   B         S   RESULT
0x00108   4  0x00100   4  2
0x00100   4  0x00108   4  -2
0x00106   4  0x00100   4  invalid
0x0010a   2  0x00100   2  5
0x00108   4  0x00100   2  invalid
0x00100   4  0x00100   4  0

ROUNDTRIP
BASE       K  S  END       BACK      OK
0x00100     3   4  0x0010c  0x00100  true
0x00100    -3   4  0x000f4  0x00100  true
0x3fffc    -1   4  0x3fff8  0x3fffc  true
0x00000     0   1  0x00000  0x00000  true

MEMORY
fill [0x00100, 0x0010c)
BYTES 11 22 33 44 55 66 77 88 99 aa bb cc 
p+0 [0x00100, 0x00104) size=4 first=0x11
p+1 [0x00104, 0x00108) size=4 first=0x55
p+2 [0x00108, 0x0010c) size=4 first=0x99

SUMMARY
walk byte : true
walk int  : true
boundary  : true
large k   : true
diff      : true
roundtrip : true
memory    : true
ALETHEIA PTR OK
```

第一段是头部。地址空间还是 262144 字节，地址字段 4 字节，大小字段 4 字节，指针结构体 8 字节。没有填充，因为两个字段都是 4 字节，对齐正好。

第二段是字节走步。基地址 0x00100，元素大小 1，偏移从 -2 到 2。地址每次加 1，负偏移往回减 1。0x000FE 和 0x000FF 都在内存里，合法。这一段说明指针走步对字节对象就是普通的地址加减。

字节走步表看起来最无聊，可它是最基本的对照。如果字节指针的 $p+1$ 不走一个字节，后面的四字节表就不可信。先让最简单的表通过，再让复杂的表通过，这是验收的顺序。很多错误不是出在复杂公式上，而是出在最简单的单位上。

第三段是四字节走步。基地址不变，元素大小 4，偏移从 -1 到 2。地址每次加 4，$k=-1$ 走到 0x000FC。0x000FC 是上一个整数的起点，不是 0x000FF。这一段是整章的核心演示：同一个 $k=1$，步长从 1 变成 4，地址就从 0x101 变成 0x104。

第四段是边界。基地址 0x00000，$k=-1$ 被拒绝；$k=0$ 合法。基地址 0x3FFFC，$k=-1$ 走到 0x3FFF8，合法；$k=0$ 停在 0x3FFFC，对象正好到 0x40000；$k=1$ 被拒绝。上界和下界都有一行失败，说明检查不是只朝一个方向。

第五段是大偏移。`INT32_MAX` 和 `INT32_MIN` 都被拒绝。它们的精确乘积分别是 8589934588 和 -8589934592，远超地址空间。程序用 `int64_t` 算，所以能看出它们越界；如果用 32 位算，前者会变成 -4，后者会变成 0，两行都会被误判为合法。这一段的输出是 `invalid`，不是碰巧的。

大偏移这两行是整张表里最重要的失败演示。它们证明程序不是“碰巧算对”，而是在乘法阶段就用了更宽的类型。你把 `int64_t` 改成 `int32_t`，这两行很可能从 `invalid` 变成合法的地址，其他行仍然通过。这种“只错在边界”的 bug 最难查，因为日常输入不会触发它。验收表把它放在显眼的位置，就是为了让边界错误无处可藏。

第六段是指针差。0x00108 和 0x00100 相差 2 个四字节元素；反过来是 -2。0x00106 和 0x00100 的字节差是 6，不能被 4 整除，失败。0x0010A 和 0x00100 的元素大小是 2，字节差 10 能被 2 整除，商是 5。大小不同的两个指针，失败。同一个指针相减，得到 0。六行覆盖了正、负、错位、不同大小和零。

第七段是往返。从 0x00100 走 3 步到 0x0010C，再走 -3 步回到 0x00100。从 0x00100 走 -3 步到 0x000F4，再走 3 步回来。从 0x3FFFC 走 -1 步到 0x3FFF8，再走 1 步回来。从 0 走 0 步，原地不动。四行的 `OK` 都是 `true`。

第八段是内存。程序在 0x00100 到 0x0010B 写入 12 个字节，值是 0x11 到 0xCC，每个字节加 0x11。然后用一个四字节指针从 0x00100 开始走，读每个对象的第一个字节：`p+0` 读到 0x11，`p+1` 读到 0x55，`p+2` 读到 0x99。三个地址分别相差 4，读到的字节分别相差 0x44。这个演示把“指针走步”和“字节读写”接在一起。

最后是汇总。七项检查全是 `true`，程序打印 `ALETHEIA PTR OK`。如果有任何一项失败，最后一行会变成 `ALETHEIA PTR BROKEN`，退出码是 1。

验收不是形式。每一条都对应一个可能犯的错误：$p+0$ 对应步长写错，负偏移对应下界漏检，上界对应对象跨过末尾，大偏移对应 32 位乘法回绕，指针差对应整除和大小检查，往返对应单位不一致，内存对应读写越界。你以后改代码，只要有一条验收失败，就知道改坏了哪里。验收表是代码的体检单，不是装饰。

验收项如下：

- $p+0$ 的地址等于 $p$ 的地址，元素大小不变。
- 字节指针的 $p+1$ 走一个字节，四字节指针的 $p+1$ 走四个字节。
- 负偏移在内存内部时合法，走出下界时被拒绝。
- 上界 0x3FFFC 的对象 $p+0$ 合法，$p+1$ 被拒绝。
- `INT32_MAX` 和 `INT32_MIN` 的大偏移被拒绝，不发生 32 位回绕。
- 指针差在整除时给出正确的正负元素个数，不整除时失败。
- 大小不同的指针相减失败。
- 走 $k$ 步再走 $-k$ 步回到原指针。
- 所有读写都经过字节层，没有直接越界访问数组。
- 编译零警告，ASan/UBSan 无报错，重复运行输出一致。
- 输出最宽一行 44 列，没有超过 80 列。

失败演示也值得做一遍。把 `int64_t delta` 改成 `int32_t delta`，重新编译，跑大偏移那两行，你会看到它们可能变成 `[... size=4]`，而不是 `invalid`。把上界检查从 `next > SIZE - s` 改成 `next >= SIZE`，再构造一个起始地址在范围内、对象跨过末尾的指针，你会看到它被放过。把指针差的整除检查删掉，0x00106 和 0x00100 会给出 1，而不是 `invalid`。这三个改动都很小，后果都是“看起来能跑，其实错了”。指针算术的难点不在公式，在这些边界上。

## 十、交给下一章

这一章做了两件事：把地址和元素大小绑成一个指针，把走步写成一条可检查的公式。

下一章要拿走的接口是：

- `struct AletheiaPtr`：地址加元素大小的二元组。
- `aletheia_ptr_make`：建立一个指向完整对象的指针。
- `aletheia_ptr_ok`：检查一个指针是否指向完整对象。
- `aletheia_ptr_walk`：按元素大小走 $k$ 步，带边界检查。
- `aletheia_ptr_diff`：两个同大小指针之间的元素个数。
- `aletheia_ptr_read_u8`：读指针地址处的第一个字节。
- `aletheia_ptr_write_u8`：写指针地址处的第一个字节。

下一章的问题是：数组为什么是连续的？

数组是一串同样大小的对象，一个挨着一个放。第 $i$ 个元素的地址是：

$$
\operatorname{addr}(a,i)=a+i\cdot s
$$

这个公式和指针走步是同一个公式。$a$ 是数组的起始地址，$i$ 是下标，$s$ 是元素大小。`arr[i]` 就是 `*(arr + i)`，也就是从起始指针走 $i$ 步，再读那个对象。指针层已经会把 $i$ 乘上 $s$，数组层只需要再管一件事：下标不能超过元素个数。

连续性的代价是固定步长。数组的元素必须一样大，一个挨着一个放，所以第 $i$ 个元素的地址才能用 $a+i\cdot s$ 算出来。如果元素大小不一样，或者中间有空洞，这个公式就不成立，只能存一张偏移表。结构体就是有空洞的布局，所以它的字段地址要靠偏移递推，不能靠乘法。数组用乘法，结构体用加法，这是两种不同的布局。

指针只知道整个内存的边界，不知道数组在哪里结束。一个指向数组中间的指针，走一步可能还在内存里，但已经出了数组。下一章会给数组加上元素个数，给下标加上范围检查，还会把二维数组的行主序公式写出来：

$$
\operatorname{addr}_{\text{row}}(i,j)=a+(i\cdot C+j)\cdot s
$$

其中 $C$ 是每行的列数。这个公式看起来多了一项，拆开还是“起始地址加偏移乘元素大小”。指针算术是引擎，数组是在引擎上装一个带边界的表盘。

下一章的两个组件是 `aletheia_arr_sum` 和 `aletheia_grid_addr`。前者遍历数组求和，后者算二维数组元素的地址。它们都会调用 `aletheia_ptr_walk`，也都会检查下标。今天先把走步做对，明天数组才有可靠的地基。

从指针到数组，只差一个元素个数。指针知道怎么走，数组知道能走多远。把两者合在一起，就有了带边界检查的下标访问。下一章会先写一维数组的求和，再写二维数组的地址计算。二维数组在内存里还是一维的，行主序只是把两个下标合成一个线性下标。指针走步还是那条公式，只是 $k$ 变成了 $i\cdot C+j$。


