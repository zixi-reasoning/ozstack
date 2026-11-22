# 字节读写

> 第八章。零件：`AletheiaStore`。整数不是一块，是几个有编号的格子。

## 一、回访：字符串之后的停止符

第七章的字符串层一次读一个字节。遇到 0 就停，容量给出上界，长度靠扫描得到。字节层的函数 `aletheia_peek_u8` 和 `aletheia_poke_u8` 只管一个格子，字符串层在它们上面加了终止符和 UTF-8 的约定。这一章要处理另一种数据：多字节的整数。一个 32 位整数不是一个格子，是四个连续的格子。读它要把四个格子拼起来，写它要把一个数拆成四个格子。

第三章讲过补码，讲过负数在内存里长什么样。那时候我们只关心字节的取值，没有认真处理“四个字节按什么顺序拼成一个数”。第四章的指针算术、第五章的数组下标、第六章的结构体偏移，都在算地址，也都没有回答字节顺序的问题。字符串按字节读，顺序就是文本顺序，不需要拼装。整数不同，同样四个字节，按不同顺序拼，得到不同的数。

这一章补上这块。一个 32 位值 $v$ 存在地址 $a$ 起，占四个字节。第 0 个字节放在 $a$，第 1 个放在 $a+1$，第 2 个放在 $a+2$，第 3 个放在 $a+3$。问题是：这四个字节里，哪个是 $v$ 的最低有效字节？Aletheia 的答案是“第 0 个”，也就是最低地址放最低有效字节。这个约定叫小端。选了小端，读写函数就必须按小端拼装和拆分，不能依赖宿主机器碰巧也是小端。

这个选择会带来一串公式。字节权重、移位掩码、地址范围、边界检查、读写往返，都能写成等式。公式落到 C 里，就是几个循环和几个移位，没有指针类型双关，没有 `memcpy`，没有对宿主字节序的假设。`AletheiaStore` 是这一章的组件，它管理一块存储区，提供按宽度读写小端值的能力。下一章的纸带台会用它把内存摊开，第十章的总装会把它交给 `AletheiaMem`。

表示和值要分开。0x12345678 是一个值，`78 56 34 12` 是它在内存里的表示；`12 34 56 78` 是同一个值在大端机器上的表示。值不变，表示可以变。C 的整数变量在寄存器里没有“字节顺序”，只有存进内存、从内存读出来的时候才需要约定。源程序里写 `uint32_t v = 0x12345678u;`，编译器决定怎么放；这一章不让编译器决定，而是自己逐字节写，自己逐字节读。这样做的代价是代码长一点，好处是每一步都能在纸上推、在输出里看、在不同机器上复现。

还有一个常见误区：以为 `uint32_t` 的四个字节就是“一个整体”，不能单独碰。其实内存里没有整体，只有字节。`aletheia_peek_u8(addr)` 可以读其中任何一个字节，`aletheia_poke_u8(addr, b)` 可以改其中任何一个字节。多字节读只是把这些字节按权重拼起来，拼的动作发生在函数里，不在内存里。理解了这一点，后面的字节序、未对齐、单字节改动就都顺了。

## 二、开场实验：四个格子里的数

把 0x12345678 写到 0x00800。四个字节是：

```text
addr    byte
0x00800 0x78
0x00801 0x56
0x00802 0x34
0x00803 0x12
```

最低地址 0x00800 放的是 0x78，它是这个数的最低有效字节。最高地址 0x00803 放的是 0x12，它是最高有效字节。按十六进制写，值从高到低是 `12 34 56 78`；按地址从低到高看，字节是 `78 56 34 12`，正好反过来。读的时候要反一次，写的时候也要反一次。这个“反”不是随便定的，是小端约定。

拼装的过程是加权求和：

$$
v=0x78\cdot 256^0+0x56\cdot 256^1+0x34\cdot 256^2+0x12\cdot 256^3
$$

$256^0=1$，$256^1=256$，$256^2=65536$，$256^3=16777216$。算出来是 $120+22016+3407872+301989888=305419896$，十六进制就是 0x12345678。每个字节的权重是 $256$ 的“它到起始地址的距离”次方。距离 0 的权重 1，距离 1 的权重 256，距离 2 的权重 65536，距离 3 的权重 16777216。

同样四个字节，如果按大端读，权重就反过来：0x00800 的 0x78 当成最高有效字节，0x00803 的 0x12 当成最低有效字节，拼出来是 0x78563412。字节没变，地址没变，只是权重分配变了。一个数是 0x12345678 还是 0x78563412，取决于读的人用哪种约定。这就是字节序。

再看同一个地址按不同宽度读。0x00800 起四个字节是 `78 56 34 12`：

```text
width  bytes         value
1      78            0x00000078
2      78 56         0x00005678
4      78 56 34 12   0x12345678
```

宽度 1 只读一个字节，得到 0x78；宽度 2 读两个字节，得到 0x5678；宽度 4 读四个字节，得到 0x12345678。窄读是宽读的低位部分，宽读是窄读的扩展。这个关系在边界检查里也出现：一个四字节读占四个格子，一个单字节读占一个格子，读的起点相同，占的范围不同。

如果从 0x00801 读四个字节，得到的是 `56 34 12` 加上 0x00804 的一个字节。0x00804 当时是 0，所以值是 0x00123456。这个地址不是 4 的倍数，按很多硬件的要求是“未对齐”。我们的读函数照样工作，因为它不执行一条四字节加载指令，而是读四个单字节再拼起来。未对齐在字节层面不是问题，在硬件层面可能是问题；这一章选择字节层面，把问题消掉。

最后做一个改动：把 0x00802 的那个字节改成 0xff。原来的四个字节 `44 33 22 11`（另一个例子）变成 `44 33 ff 11`，值从 0x11223344 变成 0x11ff3344。只改了一个格子，数的中间一段变了。多字节值不是不可分割的整体，它在内存里就是几个格子，任何一个格子都能被单字节函数改掉。读函数看到的“整体”，是拼装出来的结果。

再写三个极端值，看看字节是什么样。写 1，四个字节是 `01 00 00 00`，只有最低地址是 1，其余三个是 0。写 0，四个字节全是 0。写 0xFFFFFFFF，四个字节全是 `FF`。1 的表示说明“高位没有”就是 0，不是省略；零的表示说明“全 0”对应数值 0；全 1 的表示按无符号是 4294967295，按有符号是 -1。三个值的字节都只有 0 和 1 或 0xFF，可它们背后的权重完全不同。1 在权重 1 的位置，全 1 在每个权重位置都有 255。

从 1 加到 2，只有最低地址的字节从 01 变成 02，其余三个字节不动。从 255 加到 256，最低字节从 FF 变成 00，产生进位，第二个字节从 00 变成 01。这就是小端的进位方向：低地址先变，进位向高地址走。如果按大端存，最低有效字节在高地址，进位要从高地址向低地址走，读起来别扭。这个实验不用真的执行加法，只要看字节的变化，就能理解为什么小端和竖式的进位方向一致。

写 0x00010000，字节是 `00 00 01 00`，第三个字节是 1。这个值在权重 $2^{16}=65536$ 的位置上。只改 0x00802 这一个字节，就能把 0x11223344 的中间 8 位改掉，其他 24 位不变。多字节值像四个叠起来的格子，每个格子管 8 位，改一格只影响那 8 位。读函数把四格拼成整体，写函数把整体拆回四格，单字节函数直接改一格。三种操作作用于同一块内存，粒度不同，结果可以互相验证。

## 三、小端约定

### 3.1 字节分解

设一个 32 位值 $v$，占四个字节，起始地址 $a$。每个字节 $b_i$ 是 $v$ 在第 $i$ 个位置上的 8 位片段：

$$
b_i=(v\gg 8i)\ \&\ 0xFF,\qquad i=0,1,2,3
$$

$\gg$ 是逻辑右移。$v$ 是无符号 32 位，右移补 0，不会带进符号位。`& 0xFF` 保留最低 8 位，丢掉其余。$i=0$ 时不移位，取最低字节；$i=1$ 时右移 8 位，取次低字节；$i=2$ 时右移 16 位；$i=3$ 时右移 24 位，取最高字节。

反过来，已知四个字节，拼成值：

$$
v=\sum_{i=0}^{3} b_i\cdot 2^{8i}
$$

这是小端的定义：第 $i$ 个字节的权重是 $2^{8i}$，地址越低，权重越小，越靠近最低有效位。$b_0$ 是最低有效字节，$b_3$ 是最高有效字节。字节在内存里的顺序是 $b_0,b_1,b_2,b_3$，从低地址到高地址。

两个公式互为逆运算。把 $v$ 拆成 $b_i$，再按权重拼回去，得到 $v$：

$$
\sum_{i=0}^{3}\left((v\gg 8i)\ \&\ 0xFF\right)\cdot 2^{8i}=v
$$

这个等式对每个 32 位 $v$ 都成立。它说明拆分不丢信息，拼装能完全恢复。读写函数的正确性，最终就靠这个等式。

### 3.2 移位与掩码

C 的移位运算对无符号类型是定义良好的。`v >> 8` 把每个位向右移 8 格，最低的 8 位移出去，高的位补 0。`v & 0xFF` 只保留最低 8 位。两个操作合起来，取出任意一个字节，不需要指针，不需要联合体，不需要把 `uint32_t *` 强转成 `uint8_t *`。

掩码写 `0xFFu` 比写 `0xFF` 更明确。`0xFF` 在这个范围里能表示成 `int`，和 `uint32_t` 运算时会被转换成无符号值，结果通常没问题；`0xFFu` 直接标明是无符号常量，读者不用去想转换规则。移位量也不能超过 31，否则是未定义行为。这里的移位量是 0、8、16、24，都在范围内。

取字节的循环可以写成：

```c
for (i = 0; i < width; ++i) {
    b[i] = (AletheiaByte)((value >> (8u * i)) & 0xffu);
}
```

`width` 是 1、2 或 4，`8u * i` 最大 24。每次取一个字节，强转成 `AletheiaByte`，低 8 位保留，高位丢掉。这个循环对小端写是完整的：第 $i$ 个字节写到 $addr+i$。

拼装的循环是：

```c
for (i = 0; i < width; ++i) {
    value |= (uint32_t)b << (8u * i);
}
```

从 0 开始，每读一个字节，左移到它的权重位置，按位或进去。因为每个字节占不同的 8 位，或运算不会互相覆盖。循环结束时，`value` 就是拼好的数。这个写法对小端读是完整的。

这里有两个 C 的细节。第一，`b` 是 `AletheiaByte`，也就是 `uint8_t`，在表达式里会先做整数提升，变成 `int`。`int` 至少 16 位，装得下 0 到 255，提升不会改变值。左移到 24 位后再转成 `uint32_t`，结果是确定的。第二，`(uint32_t)b << 24` 的移位量是 24，对 32 位无符号类型合法；如果 `b` 是带符号的 `char` 且值为负，提升后会带符号，左移可能出问题。用 `uint8_t` 就没有这个风险，字节永远是非负的 0 到 255。

取字节时也要注意：`(value >> (8u * i)) & 0xffu` 的括号不能省。`&` 的优先级低于 `>>`，写成 `value >> 8u * i & 0xffu` 也能按预期解析，但可读性差；写成 `(value >> 8u * i) & 0xffu` 更清楚。`8u * i` 也不能写成 `8 * i`，虽然结果一样，`u` 后缀提醒读者这是无符号运算，移位量不会变成负数。C 的运算符优先级和整数提升是这类代码最常见的坑，公式写对了，括号和类型写错，结果仍然会错。

还有一种写法是把 `uint32_t *` 强转成 `uint8_t *`，直接按字节读。这种写法叫类型双关，在很多平台上能工作，可它依赖对象的表示、对齐和别名规则，C 标准不保证。书里不用。我们已经有 `aletheia_peek_u8`，它接受任意地址、返回一个字节，正好是拆字节需要的操作。用现成的字节函数，比重新解释指针类型安全，也更符合“所有访问都经过字节层”的约定。

### 3.3 大端对照

大端把最高有效字节放在最低地址。同样的字节序列 $b_0,b_1,b_2,b_3$，大端的值是：

$$
v_{\mathrm{BE}}=\sum_{i=0}^{3} b_i\cdot 2^{8(3-i)}
$$

$b_0$ 的权重是 $2^{24}$，$b_3$ 的权重是 $2^0$。小端的权重顺序是 $1,256,65536,16777216$，大端正好反过来。同一串字节 `78 56 34 12`，小端读成 0x12345678，大端读成 0x78563412。两个值互为字节反转。

有些处理器天然是大端，有些是小端，有些可以切换。网络协议传统上用大端，叫做网络字节序；x86 和 ARM 常见配置用小端。C 程序如果直接把一块内存按 `uint32_t` 读，读出来的值取决于宿主字节序，换一台机器结果就变了。这一章不这样读。所有多字节值都经过逐字节拼装，字节顺序由代码写死，和宿主无关。

这也意味着 Aletheia 的记录可以跨机器复现。同一段 C 代码，在一台小端机器和一台大端机器上编译运行，只要平台提供 `uint8_t` 和 `uint32_t`，输出就一样。`<stdint.h>` 里的 `uint8_t` 和 `uint32_t` 如果存在，就是正好 8 位和正好 32 位的无符号类型。书里的程序不假设宿主的大小端，也不假设 `int` 的宽度，一律用定宽类型，不用 `unsigned int`。

如果直接用类型双关读整数，比如 `*(uint32_t *)(mem + addr)`，代码短，可它同时依赖三件事：`mem` 的地址对齐、编译器的别名规则、宿主的字节序。换一个平台，任何一条不成立，结果就可能变。更隐蔽的是，编译器可能假定 `uint32_t *` 和别的指针不指向同一块内存，做优化时把读写调换顺序。这类 bug 很难复现，也很难在小型例子里看到。逐字节拼装没有这些问题：每个字节都是 `uint8_t`，每次访问都合法，权重由代码决定，宿主只负责存取单个字节。

字节序不只影响整数。浮点数、宽字符、文件格式都有字节序问题。这一章只处理 32 位无符号整数，因为第一卷的材料只需要这一种。后面如果需要 16 位或 64 位，公式是一样的，宽度换一下，字节数换一下，权重从 $2^{8i}$ 变成对应的幂。组件的 `read_le` 已经支持 1、2、4 三种宽度，扩展到 8 需要 64 位中间变量，那是下一步的事，不在这一章的范围里。

### 3.4 为什么选小端

小端不是唯一正确的选择，是一个约定。选它的理由有几条。第一，低地址放低有效字节，地址增加和权重增加方向一致，公式里的 $2^{8i}$ 很自然。第二，多字节加法从低位向高位进位，低地址先处理，和手工竖式一致。第三，Aletheia 的字节层从 0 开始编号，地址 0 是最低地址，把最低有效字节放在那里，读写的循环可以从 0 开始，不用倒着写。第四，很多读者手边的机器是小端，实验现象和公式对得上，少一层解释。

代价是和网络字节序相反。如果将来要把 Aletheia 的数发到网络上，需要做字节序转换。这一章不涉及网络，只处理机器内部的内存。书里明确写“小端”，所有输出、所有记录都按小端解释。换一种约定，公式和程序都要改，不能只改一个常量。

大端也不是错的。大端的优点是字节顺序和十六进制书写顺序一致，人读十六进制 `12 34 56 78`，内存里也是 `12 34 56 78`，调试时直观。小端的内存字节是反的，读十六进制转储要习惯一下。两种约定各有取舍，重要的是选一个、写清楚、所有组件一致。

### 3.5 有符号解释

同样的四个字节，按无符号读是 0 到 4294967295，按有符号读是 -2147483648 到 2147483647。第三章的补码公式是：

$$
s(v)=
\begin{cases}
v, & v<2^{31},\\
v-2^{32}, & v\ge 2^{31}.
\end{cases}
$$

0xffffffff 按无符号是 4294967295，按有符号是 -1。0x80000000 按无符号是 2147483648，按有符号是 -2147483648。字节完全一样，只是解释不同。这一章的读写函数返回 `uint32_t`，不返回 `int32_t`，因为位模式是底层的，符号是上层的。需要负数时，调用者按上面的公式解释，或者另外写一个有符号读取函数。

程序里没有把 `uint32_t` 直接转成 `int32_t` 再打印。C 标准里，超出范围的无符号转有符号是实现定义的，不同编译器可能有不同结果。书里的程序避免这种转换，只打印无符号十六进制。补码的公式在第三章已经推过，这一章只提一句，说明“字节读写”和“符号解释”是两层，不要混在一起。

## 四、读写组件 AletheiaStore

### 4.1 存储区描述符

`AletheiaStore` 描述一块存储区：

```c
struct AletheiaStore {
    AletheiaAddr base;
    uint32_t size;
};
```

`base` 是起始地址，`size` 是字节数。它和字符串描述符 `AletheiaStr` 形状相同，都是地址加容量，可语义不同：字符串有终止符，存储区没有；字符串按字节扫描，存储区按宽度读写；字符串的长度是算出来的，存储区的大小是构造时给的。两个描述符都只是视图，不拥有内存，不负责分配。

存储区用绝对地址，不用相对偏移。读写函数的 `addr` 参数是机器地址，必须落在 $[base,base+size)$ 内。为什么不用偏移？因为前面的章节都用绝对地址：字节层、指针层、数组层、结构体层，地址都是 0 到 262143 的整数。存储层如果改用偏移，调用者要来回换算，容易错。绝对地址让所有层的地址空间一致，存储层只是在绝对地址上加了一个范围限制。

范围是左闭右开：

$$
[\,base,\ base+size\,)
$$

包含 `base`，不包含 `base+size`。一个字节的访问在 `addr`，要求 `addr < base+size`；一个四字节的访问占 `addr` 到 `addr+3`，要求 `addr+3 < base+size`，等价于 `addr <= base+size-4`。右端开区间让“结束地址”不指向任何一个有效字节，`base+size` 是第一个不属于这块区域的地址。

### 4.2 有效性与跨度

存储区本身有效，要求大小非零、起始地址加大小不超过 262144：

$$
size>0,\qquad base+size\le 262144
$$

`base` 和 `size` 都是 `uint32_t`，直接相加可能溢出。程序里先检查 `size <= ALETHEIA_SIZE`，再用 `base <= ALETHEIA_SIZE - size`，把加法变成减法，避免溢出。这个写法在第六章的对齐检查里也出现过：先确认减数不大于被减数，再相减。

一次读写有效，还要求访问的跨度完全落在存储区内：

$$
base\le addr,\qquad addr-base\le size-width
$$

其中 $width$ 是字节数。第一个条件保证起点不在区外；第二个条件保证从起点到终点不超过区的右端。$addr-base$ 是偏移，$size-width$ 是最后一个合法起点相对 `base` 的最大偏移。两个条件合起来，等价于 $addr\in[base,base+size-width]$。

程序里先检查 `width > size`，避免 `size-width` 下溢。如果宽度比整个区还大，直接拒绝，不用算偏移。然后检查 `addr < base`，再算 `off=addr-base`，最后比较 `off <= size-width`。每一步都在无符号范围内，不会出现负数，也不会溢出。

宽度只支持 1、2、4。为什么不支持 3？因为组件服务的是 8 位、16 位、32 位整数，这三种宽度覆盖了第一卷的需求。3 字节的读写公式也能写，可它不是常见的寄存器宽度，增加了测试面，没有带来新的概念。程序里的 BOUNDS 段专门测了宽度 3 被拒绝，说明宽度检查是显式的，不是碰巧失败。

存储区的边界有两个方向。左边界 `base` 是最低合法地址，右边界 `base+size` 是第一个非法地址。访问的起点可以在左边界上，不能在右边界上；访问的终点可以落在右边界的前一个字节，不能越过右边界。检查时用偏移而不是地址相加，是因为 `addr+width` 可能溢出：如果 `addr` 接近 4294967295，加 4 会回绕到一个小数，检查就失效了。先确认 `addr>=base`，再算 `addr-base`，这个差不会溢出，再和 `size-width` 比较，所有运算都在安全范围里。

为什么存储区要求 `size>0`？因为一个没有字节的区域不能读也不能写，保留它只会让每个访问都失败。空区在概念上有用，比如“这里暂时没有数据”，可组件不需要表达这个概念；调用者可以用 `false` 或一个空指针表达，不必构造一个无效的存储区。`size=1` 是合法的最小区域，能读一个字节，不能读两个。这个边界在 EMPTY 段里测了，说明最小区域和空区是两回事。

### 4.3 读与写

读函数 `aletheia_read_le` 的参数是存储区、地址、宽度、输出指针。它先检查跨度和宽度，再从 `addr` 开始逐字节读，按小端权重拼装：

$$
\operatorname{read}(addr,width)=\sum_{i=0}^{width-1} b_{addr+i}\cdot 2^{8i}
$$

每个 $b_{addr+i}$ 通过 `aletheia_peek_u8` 读取，读取前检查地址在 262144 内。拼装用 `uint32_t`，宽度最大 4，移位最大 24，不会溢出。读成功时写 `*out`，失败时不写。调用者必须先看返回值，再看输出。

写函数 `aletheia_write_le` 的参数是存储区、地址、宽度、值。它先做同样的跨度检查，再把值拆成字节：

$$
b_{addr+i}=(value\gg 8i)\ \&\ 0xFF,\qquad i=0,\dots,width-1
$$

每个字节通过 `aletheia_poke_u8` 写入。拆分和写入都在检查之后，检查通过后不会因为地址越界而中途失败。如果 `aletheia_poke_u8` 返回失败，说明前面的检查有 bug，函数返回失败，可能已经写了一部分。这种“先验证、后修改”的顺序和第七章的反转一致：输入错误挡在修改之前，实现错误用测试去抓。

读写互为逆运算。对任意合法地址和宽度，写进去的值再读出来，等于原值：

$$
\operatorname{read}(addr,width,\operatorname{write}(addr,width,v))=v
$$

这个等式叫往返不变量。它成立是因为拆分和拼装互为逆运算，且读写访问的是同一组字节。程序里的 ROUNDTRIP 段用七个值测这个不变量，包括 0、1、最大值、最小值、全 1 和两个任意模式。七个都通过，说明公式和实现对得上。

可以按字节归纳证明。写操作把 $v$ 拆成 $b_0,\dots,b_{w-1}$，分别写到地址 $a,\dots,a+w-1$。读操作从同一组地址读回 $b'_0,\dots,b'_{w-1}$。因为写的是这几个字节，读的也是这几个字节，中间没有别的操作，每个 $b'_i=b_i$。拼装公式对字节序列是确定的，所以读回的值等于写进去的值。归纳的每一步只依赖一个事实：同一个地址先写后读，得到刚写的字节。这个事实由字节层的 `poke` 和 `peek` 保证，存储层只是把它们串起来。

写操作的范围检查在读之前完成。如果检查失败，一个字节都不写；如果检查成功，循环里的每个地址都在区内，`poke` 不会越界。读操作同理，检查失败一个字节都不读，检查成功循环里的每个地址都在区内。这种“全有或全无”的边界行为，让调用者可以根据返回值判断内存有没有被改。写失败时内存保持原样，读失败时输出保持原样。程序里的失败路径没有单独打印，可代码结构保证了这一点：检查和修改分离，检查在前。

如果 `width=1`，读写退化成一个字节，往返不变量变成 `peek(poke(addr,b))=b`，就是第一、二章已经建立的性质。如果 `width=2`，是两个字节的往返。如果 `width=4`，是四个字节的往返。三种宽度共用同一个循环，只是次数不同。组件没有为每种宽度写一套代码，而是把宽度作为参数，减少了重复，也减少了不一致的可能。

### 4.4 宽度与对齐

宽度决定访问几个字节。宽度 1 读写一个字节，宽度 2 读写两个字节，宽度 4 读写四个字节。宽度的单位是字节，不是位。一个 32 位整数是 4 字节，不是 32 字节。字符串的长度也是字节数，两个“宽度”概念不同：字符串的容量是一段区域的字节数，整数的宽度是一个值的字节数。

对齐在第六章很重要，结构体字段要按对齐规则摆放。在存储层，对齐不是正确性的前提。`aletheia_read_le` 可以从任意地址读四个字节，包括不是 4 的倍数的地址。它不执行一条四字节加载指令，而是读四个单字节，拼成一个 `uint32_t`。硬件层面的未对齐访问限制被绕开了，代价是四次字节读和三次移位，比一条加载指令慢，可在一台教学机器上，正确性比速度重要。

这不意味着对齐可以忽略。结构体布局仍然要对齐，数组元素仍然要按元素大小等距，指针算术仍然按元素大小走。存储层的“任意地址可读”是一个补充能力，不是取消对齐规则。你可以从任意地址读一个数，但如果你把结构体字段放在未对齐的地址，字段之间的偏移就和第六章的偏移表对不上。布局负责摆放，存储负责读写，两层各管一件事。

程序里的 UNALIGNED 段在 0x00841 读四个字节，0x00841 不是 4 的倍数。四个字节是 `56 34 12 00`，读出来是 0x00123456。这个实验说明字节拼装不受对齐限制。它也为下一章的十六进制转储做准备：转储要按任意地址显示字节，不能要求地址对齐。对齐是布局的约束，不是字节访问的前提，两件事可以分开处理。

## 五、手工推演

拿 0x12345678 写到 0x00800，按宽度 4 走一遍写。

$i=0$：右移 0 位，得到 0x12345678，与 0xFF 得 0x78，写到 0x00800。
$i=1$：右移 8 位，得到 0x00123456，与 0xFF 得 0x56，写到 0x00801。
$i=2$：右移 16 位，得到 0x00001234，与 0xFF 得 0x34，写到 0x00802。
$i=3$：右移 24 位，得到 0x00000012，与 0xFF 得 0x12，写到 0x00803。

内存变成 `78 56 34 12`。四个地址各一个字节，顺序和权重的顺序一致。

再按宽度 4 读回来。

$i=0$：读 0x00800 得 0x78，左移 0 位，或进结果，结果 0x00000078。
$i=1$：读 0x00801 得 0x56，左移 8 位，得 0x00005600，或进去，结果 0x00005678。
$i=2$：读 0x00802 得 0x34，左移 16 位，得 0x00340000，或进去，结果 0x00345678。
$i=3$：读 0x00803 得 0x12，左移 24 位，得 0x12000000，或进去，结果 0x12345678。

拼回来的值和写进去的值一样。每一步只影响一个字节的位置，或运算不会覆盖已经拼好的部分。

按宽度 2 读 0x00800：读 0x78 和 0x56，拼成 0x5678。按宽度 2 读 0x00801：读 0x56 和 0x34，拼成 0x3456。按宽度 2 读 0x00802：读 0x34 和 0x12，拼成 0x1234。同一个四字节值，从不同起点按两字节读，得到不同的片段。这些片段是原值的低 16 位在不同地址上的“窗口”，起点变了，窗口的内容也变了。

按大端读 0x00800：读 0x78 左移 24 位，0x56 左移 16 位，0x34 左移 8 位，0x12 不移，拼成 0x78563412。和小端的结果正好字节反转。两个值都“正确”，只是约定不同。程序只实现小端，大端值在 BYTES 段手工算出来做对照。

再推一个两字节窗口。0x00801 起读两个字节，读 0x56 和 0x34，拼成 0x3456。0x00802 起读两个字节，读 0x34 和 0x12，拼成 0x1234。0x00803 起读两个字节，读 0x12 和 0x00，拼成 0x0012。窗口向右移一个字节，低字节丢掉，高字节补进来，值整体右移 8 位。这和 `v >> 8` 的效果一样，但移位发生在地址上，不是数值上。多字节读是“从地址窗口取数”，窗口的位置和宽度决定取到哪一段。

全 1 的推演也值得看一眼。0xFFFFFFFF 写到 0x00860，四个字节都是 `FF`。读回时每一步读 0xFF，左移到对应位置，或进去，四段全 1 拼成 0xFFFFFFFF。没有符号扩展，没有特殊处理，每个字节独立。按有符号看，这个值是 -1；按无符号看，它是 4294967295。存储层只负责位模式，符号解释留给调用者。这就是为什么读写函数用 `uint32_t`，不用 `int32_t`：位模式不需要符号，解释才需要。

0x80000000 写到 0x00864，字节是 `00 00 00 80`。最高地址是 0x80，其余三个是 0。读回时最后一次左移 24 位，0x80 变成 0x80000000。这一步最容易出错：如果中途用了带符号的 `int`，0x80 左移 24 位会落到符号位，结果可能是负数或未定义。用 `uint32_t`，左移是模 2 的 32 次方运算，结果是确定的 0x80000000。类型选对了，公式才成立。

再看改动。原值 0x11223344 写到 0x00850，字节是 `44 33 22 11`。把 0x00852 的 0x22 改成 0xFF，字节变成 `44 33 FF 11`。按小端拼：$0x44+0x33\cdot256+0xFF\cdot65536+0x11\cdot16777216=0x11FF3344$。原来的 0x22 在第二个字节位置，权重 65536；换成 0xFF 后，值在 $65536$ 这一位上增加了 $(0xFF-0x22)\cdot65536$。其他字节不变。

边界推演。存储区 base=0x00800，size=0x00400，右端 0x00C00。宽度 4 的最后一个合法起点是 $base+size-4=0x00800+0x00400-4=0x00BFC$。0x00BFC 到 0x00BFF 四个字节都在区内，合法。0x00BFD 到 0x00C00，最后一个字节 0x00C00 在区外，拒绝。0x007FF 在 base 之前，拒绝。0x00C00 是右端本身，不包含，拒绝。宽度 1 在 0x00C00 也拒绝，因为右端不属于任何有效字节。

空区推演。size=0 时，右端等于 base，区间 $[base,base)$ 是空的，任何宽度都放不下，构造直接拒绝。size=1 时，只能容纳宽度 1 的访问，宽度 4 拒绝。程序里的 EMPTY 段测了这三种情况。空区不是错误的数据，是一个合法的边界情况，组件用拒绝来表达“这里没有可读的字节”。

## 六、把 AletheiaStore 写成 C

### 6.1 结构体与构造

```c
struct AletheiaStore {
    AletheiaAddr base;
    uint32_t size;
};
```

两个字段都是 4 字节，结构体大小 8 字节，没有空洞。`base` 是绝对地址，`size` 是字节数。构造时检查 `size` 非零、不超过 262144，`base` 不超过 `262144 - size`：

```c
static bool aletheia_store_ok(const struct AletheiaStore *s) {
    if (s == NULL || s->size == 0u || s->size > ALETHEIA_SIZE) {
        return false;
    }
    return s->base <= ALETHEIA_SIZE - s->size;
}
```

`ALETHEIA_SIZE - s->size` 在 `size <= ALETHEIA_SIZE` 时不会下溢。`base <=` 这个差，等价于 `base + size <= ALETHEIA_SIZE`，但不用做加法。`aletheia_store_make` 用临时结构体验证，成功才写 `*out`，失败不写输出。这个模式和第六章的偏移表、第七章的字符串构造一致。

### 6.2 跨度检查

```c
static bool aletheia_store_has(const struct AletheiaStore *s,
                               AletheiaAddr addr, uint32_t width) {
    uint32_t off;
    if (!aletheia_store_ok(s)) {
        return false;
    }
    if (width != 1u && width != 2u && width != 4u) {
        return false;
    }
    if (width > s->size || addr < s->base) {
        return false;
    }
    off = addr - s->base;
    return off <= s->size - width;
}
```

函数先验证存储区，再验证宽度，再验证大小和起点，最后算偏移比较。`width > s->size` 挡住“宽度比区还大”的情况，避免后面的减法下溢。`addr < s->base` 挡住起点在区前的情况。`addr >= s->base` 后，`addr - s->base` 在 0 到 4294967295 之间，不会下溢。`size - width` 在 `width <= size` 时安全。

返回真表示从 `addr` 开始的 `width` 个字节全部在区内。这个判断只依赖描述符和参数，不读内存。读函数和写函数都先调用它，再做字节操作。检查一次，读写各自复用。

### 6.3 小端读

```c
static bool aletheia_read_le(const struct AletheiaStore *s, AletheiaAddr addr,
                             uint32_t width, uint32_t *out) {
    uint32_t v = 0u;
    uint32_t i;
    if (out == NULL || !aletheia_store_has(s, addr, width)) {
        return false;
    }
    if (width != 1u && width != 2u && width != 4u) {
        return false;
    }
    for (i = 0; i < width; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_peek_u8(addr + i, &b)) {
            return false;
        }
        v |= (uint32_t)b << (8u * i);
    }
    *out = v;
    return true;
}
```

先检查输出指针和跨度，再重复一次宽度检查。`aletheia_store_has` 已经检查过宽度，这里的重复是防御性的：如果将来有人改了 `has`，读函数仍然不会接受非法宽度。循环里每次读一个字节，左移到权重位置，或进 `v`。`addr+i` 不会溢出，因为 `addr` 和 `i` 都小于 262144，`i` 最多 3。读成功才写 `*out`，失败不写。

读函数不修改内存，参数是 `const struct AletheiaStore *`。它只调用 `aletheia_peek_u8`，不调用 `poke`。这个 const 不是装饰，是接口承诺：读函数不会改存储区，调用者可以放心地在只读场景使用。

### 6.4 小端写

```c
static bool aletheia_write_le(const struct AletheiaStore *s, AletheiaAddr addr,
                              uint32_t width, uint32_t value) {
    uint32_t i;
    if (!aletheia_store_has(s, addr, width)) {
        return false;
    }
    if (width != 1u && width != 2u && width != 4u) {
        return false;
    }
    for (i = 0; i < width; ++i) {
        AletheiaByte b = (AletheiaByte)((value >> (8u * i)) & 0xffu);
        if (!aletheia_poke_u8(addr + i, b)) {
            return false;
        }
    }
    return true;
}
```

写函数也接受 const 描述符。写的是描述符指向的内存，不是描述符本身；描述符的 `base` 和 `size` 不变。这一点和第七章的 `aletheia_str_poke` 一样：视图是只读的描述，内容是可变的内存。如果将来要改描述符，比如扩大区域，那是另一个函数，不在这里做。

循环不变量可以写成两句话。第一句：进入第 $i$ 次迭代时，`value` 的低 $8i$ 位已经由前 $i$ 个字节拼好，高 $32-8i$ 位还是 0。第二句：第 $i$ 次迭代读地址 $addr+i$，把它的 8 位放到 `value` 的第 $8i$ 到 $8i+7$ 位，其余位不变。初始化时 $i=0$，低 0 位拼好，成立。每次迭代把下一个字节放进下一个 8 位段，两个句子都保持。循环结束时 $i=width$，`value` 的低 $8width$ 位全部拼好，高位仍是 0，正好是结果。写循环的不变量类似，只是方向反过来：前 $i$ 个字节已经写入，后面的字节还没动。

这两个不变量解释了为什么循环里不需要清空 `value` 的高位。`value` 从 0 开始，每次只填一个新的 8 位段，没填的段一直是 0。如果 `value` 没初始化，高位可能是垃圾，或运算后结果就错了。初始化不是形式，是算法的一部分。写循环不需要初始化目标字节，因为每个字节都会被覆盖；读循环需要初始化结果，因为结果是从无到有拼出来的。

宽度检查和指针检查放在循环外，循环内不再重复判断宽度。这是性能上的考虑，也是正确性上的分工：外层保证参数合法，内层只做机械的拼接。如果循环内再检查宽度，代码更长，分支更多，不会更安全。分层检查的关键是每一层都知道自己依赖什么：`read_le` 依赖 `store_has` 已经验证了宽度和跨度，`store_has` 依赖 `store_ok` 已经验证了区域。每一层只检查自己负责的条件，不重复别人的工作，也不跳过自己的。

拆分用 `value >> (8u * i)` 加 `& 0xffu`，和小端读的权重对应。写入顺序从低地址到高地址，也就是从最低有效字节到最高有效字节。检查已经保证所有地址在区内，循环里的 `poke` 不会因为越界失败。如果失败，说明实现有错误，函数返回失败，不假装成功。

### 6.5 包装与打印

`aletheia_read_u32` 和 `aletheia_write_u32` 是宽度 4 的包装：

```c
static bool aletheia_read_u32(const struct AletheiaStore *s, AletheiaAddr addr,
                              uint32_t *out) {
    return aletheia_read_le(s, addr, 4u, out);
}

static bool aletheia_write_u32(const struct AletheiaStore *s, AletheiaAddr addr,
                               uint32_t value) {
    return aletheia_write_le(s, addr, 4u, value);
}
```

包装不增加检查，只固定宽度。调用者写 `read_u32` 比写 `read_le(..., 4u, ...)` 清楚，也不容易把宽度写错。以后需要 16 位或 8 位，可以再加 `read_u16`、`read_u8`，底层还是同一个 `read_le`。这一章的检查函数直接调用 `read_le` 测宽度 1、2、4，包装只用于 32 位的主路径。

打印函数 `aletheia_print_bytes` 把一个区间的字节按十六进制打印，字节之间一个空格。它先检查跨度，再逐字节读，用 `%02x` 输出两位十六进制。这个函数是下一章十六进制转储的雏形：下一章会加地址、分组、ASCII 列和标注，这一章只做最小的字节显示。

## 七、完整程序

完整程序把字节层、存储层和检查函数放在一个文件里。检查分七段：BYTES、ROUNDTRIP、WIDTH、UNALIGNED、MUTATE、BOUNDS、EMPTY。每段打印结果，最后打印汇总。

编译命令：

```bash
cc -std=c99 -O2 -Wall -Wextra -pedantic -Werror aletheia_ch08.c -o aletheia_ch08
```

完整代码：

```c
/* aletheia_ch08.c */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define ALETHEIA_SIZE ((uint32_t)256 * 1024)

typedef uint8_t AletheiaByte;
typedef uint32_t AletheiaAddr;

struct AletheiaStore {
    AletheiaAddr base;
    uint32_t size;
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

/* 存储区 = 绝对起始地址 + 字节数；所有访问都必须落在区内。 */
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

static bool aletheia_store_has(const struct AletheiaStore *s,
                               AletheiaAddr addr, uint32_t width) {
    uint32_t off;
    if (!aletheia_store_ok(s)) {
        return false;
    }
    if (width != 1u && width != 2u && width != 4u) {
        return false;
    }
    if (width > s->size || addr < s->base) {
        return false;
    }
    off = addr - s->base;
    return off <= s->size - width;
}

/* 小端读：最低有效字节在最低地址。 */
static bool aletheia_read_le(const struct AletheiaStore *s, AletheiaAddr addr,
                             uint32_t width, uint32_t *out) {
    uint32_t v = 0u;
    uint32_t i;
    if (out == NULL || !aletheia_store_has(s, addr, width)) {
        return false;
    }
    if (width != 1u && width != 2u && width != 4u) {
        return false;
    }
    for (i = 0; i < width; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_peek_u8(addr + i, &b)) {
            return false;
        }
        v |= (uint32_t)b << (8u * i);
    }
    *out = v;
    return true;
}

/* 小端写：value 的第 i 个字节落到 addr+i。 */
static bool aletheia_write_le(const struct AletheiaStore *s, AletheiaAddr addr,
                              uint32_t width, uint32_t value) {
    uint32_t i;
    if (!aletheia_store_has(s, addr, width)) {
        return false;
    }
    if (width != 1u && width != 2u && width != 4u) {
        return false;
    }
    for (i = 0; i < width; ++i) {
        AletheiaByte b = (AletheiaByte)((value >> (8u * i)) & 0xffu);
        if (!aletheia_poke_u8(addr + i, b)) {
            return false;
        }
    }
    return true;
}

static bool aletheia_read_u32(const struct AletheiaStore *s, AletheiaAddr addr,
                              uint32_t *out) {
    return aletheia_read_le(s, addr, 4u, out);
}

static bool aletheia_write_u32(const struct AletheiaStore *s, AletheiaAddr addr,
                               uint32_t value) {
    return aletheia_write_le(s, addr, 4u, value);
}

static bool aletheia_print_bytes(const struct AletheiaStore *s,
                                 AletheiaAddr addr, uint32_t n) {
    uint32_t i;
    if (!aletheia_store_has(s, addr, n)) {
        printf("(bad span)");
        return false;
    }
    for (i = 0; i < n; ++i) {
        AletheiaByte b = 0u;
        if (!aletheia_peek_u8(addr + i, &b)) {
            return false;
        }
        if (i > 0u) {
            printf(" ");
        }
        printf("%02x", (unsigned)b);
    }
    return true;
}

static struct AletheiaStore aletheia_make_region(void) {
    struct AletheiaStore s = { 0u, 0u };
    if (!aletheia_store_make(0x00800u, 0x00400u, &s)) {
        printf("region construction failed\n");
    }
    return s;
}

static bool aletheia_check_bytes(void) {
    struct AletheiaStore s = aletheia_make_region();
    AletheiaByte b[4] = { 0u, 0u, 0u, 0u };
    uint32_t v = 0u;
    uint32_t be = 0u;
    uint32_t i;
    bool ok = aletheia_write_u32(&s, 0x00800u, 0x12345678u);
    for (i = 0; i < 4u; ++i) {
        if (!aletheia_peek_u8(0x00800u + i, &b[i])) {
            ok = false;
        }
    }
    if (!aletheia_read_u32(&s, 0x00800u, &v)) {
        ok = false;
    }
    be = ((uint32_t)b[0] << 24) | ((uint32_t)b[1] << 16) |
         ((uint32_t)b[2] << 8) | (uint32_t)b[3];
    printf("BYTES\n");
    printf("ADDR 0x00800\n");
    if (!aletheia_print_bytes(&s, 0x00800u, 4u)) {
        ok = false;
    }
    printf("\n");
    printf("LE 0x%08x\n", (unsigned)v);
    printf("BE 0x%08x\n", (unsigned)be);
    if (!ok || v != 0x12345678u || be != 0x78563412u ||
        b[0] != 0x78u || b[1] != 0x56u || b[2] != 0x34u || b[3] != 0x12u) {
        return false;
    }
    return true;
}

static bool aletheia_check_roundtrip(void) {
    static const uint32_t values[] = {
        0x00000000u, 0x00000001u, 0x7fffffffu,
        0x80000000u, 0xffffffffu, 0x12345678u, 0xdeadbeefu
    };
    struct AletheiaStore s = aletheia_make_region();
    size_t i;
    bool ok = true;
    printf("ROUNDTRIP\n");
    printf("VALUE      READ       OK\n");
    for (i = 0; i < sizeof(values) / sizeof(values[0]); ++i) {
        AletheiaAddr addr = 0x00810u + (AletheiaAddr)i * 4u;
        uint32_t back = 0u;
        bool wr = aletheia_write_u32(&s, addr, values[i]);
        bool rd = wr && aletheia_read_u32(&s, addr, &back);
        bool eq = rd && back == values[i];
        printf("0x%08x 0x%08x %s\n", (unsigned)values[i], (unsigned)back,
               eq ? "true" : "false");
        if (!wr || !rd || !eq) {
            ok = false;
        }
    }
    return ok;
}

static bool aletheia_check_width(void) {
    struct AletheiaStore s = aletheia_make_region();
    uint32_t v8 = 0u;
    uint32_t v16 = 0u;
    uint32_t v32 = 0u;
    bool ok = aletheia_write_u32(&s, 0x00830u, 0x12345678u);
    ok = ok && aletheia_read_le(&s, 0x00830u, 1u, &v8);
    ok = ok && aletheia_read_le(&s, 0x00830u, 2u, &v16);
    ok = ok && aletheia_read_le(&s, 0x00830u, 4u, &v32);
    printf("WIDTH\n");
    printf("ADDR 0x00830\n");
    if (!aletheia_print_bytes(&s, 0x00830u, 4u)) {
        ok = false;
    }
    printf("\n");
    printf("u8  0x%08x\n", (unsigned)v8);
    printf("u16 0x%08x\n", (unsigned)v16);
    printf("u32 0x%08x\n", (unsigned)v32);
    if (!ok || v8 != 0x78u || v16 != 0x5678u || v32 != 0x12345678u) {
        return false;
    }
    return true;
}

static bool aletheia_check_unaligned(void) {
    struct AletheiaStore s = aletheia_make_region();
    AletheiaByte b[4] = { 0u, 0u, 0u, 0u };
    uint32_t v = 0u;
    uint32_t i;
    bool ok = aletheia_poke_u8(0x00841u, 0x56u) &&
              aletheia_poke_u8(0x00842u, 0x34u) &&
              aletheia_poke_u8(0x00843u, 0x12u);
    for (i = 0; i < 4u; ++i) {
        if (!aletheia_peek_u8(0x00841u + i, &b[i])) {
            ok = false;
        }
    }
    ok = ok && aletheia_read_u32(&s, 0x00841u, &v);
    printf("UNALIGNED\n");
    printf("ADDR 0x00841 BYTES ");
    if (!aletheia_print_bytes(&s, 0x00841u, 4u)) {
        ok = false;
    }
    printf("\n");
    printf("VALUE 0x%08x\n", (unsigned)v);
    if (!ok || v != 0x00123456u) {
        return false;
    }
    return true;
}

static bool aletheia_check_mutate(void) {
    struct AletheiaStore s = aletheia_make_region();
    uint32_t before = 0u;
    uint32_t after = 0u;
    bool ok = aletheia_write_u32(&s, 0x00850u, 0x11223344u);
    ok = ok && aletheia_read_u32(&s, 0x00850u, &before);
    printf("MUTATE\n");
    printf("WRITE 0x11223344 -> ");
    if (!aletheia_print_bytes(&s, 0x00850u, 4u)) {
        ok = false;
    }
    printf("\n");
    printf("POKE  0x00852 = ff\n");
    ok = ok && aletheia_poke_u8(0x00852u, 0xffu);
    printf("BYTES ");
    if (!aletheia_print_bytes(&s, 0x00850u, 4u)) {
        ok = false;
    }
    printf("\n");
    ok = ok && aletheia_read_u32(&s, 0x00850u, &after);
    printf("READ  0x%08x\n", (unsigned)after);
    if (!ok || before != 0x11223344u || after != 0x11ff3344u) {
        return false;
    }
    return true;
}

static void aletheia_print_bound(const struct AletheiaStore *s,
                                 AletheiaAddr addr, uint32_t width) {
    uint32_t v = 0u;
    bool ok = aletheia_read_le(s, addr, width, &v);
    printf("0x%05x w%u    %s\n", (unsigned)addr, (unsigned)width,
           ok ? "ok" : "rejected");
}

static bool aletheia_check_bounds(void) {
    struct AletheiaStore s = aletheia_make_region();
    bool b1;
    bool b2;
    bool b3;
    bool b4;
    bool b5;
    bool b6;
    b1 = aletheia_store_has(&s, 0x00bfcu, 4u);
    b2 = aletheia_store_has(&s, 0x00bfdu, 4u);
    b3 = aletheia_store_has(&s, 0x007ffu, 4u);
    b4 = aletheia_store_has(&s, 0x00c00u, 1u);
    b5 = aletheia_store_has(&s, 0x00800u, 0u);
    b6 = aletheia_store_has(&s, 0x00800u, 3u);
    printf("BOUNDS\n");
    printf("REGION END 0x00c00\n");
    printf("CASE          RESULT\n");
    aletheia_print_bound(&s, 0x00bfcu, 4u);
    aletheia_print_bound(&s, 0x00bfdu, 4u);
    aletheia_print_bound(&s, 0x007ffu, 4u);
    aletheia_print_bound(&s, 0x00c00u, 1u);
    aletheia_print_bound(&s, 0x00800u, 0u);
    aletheia_print_bound(&s, 0x00800u, 3u);
    return b1 && !b2 && !b3 && !b4 && !b5 && !b6;
}

static bool aletheia_check_empty(void) {
    struct AletheiaStore s;
    struct AletheiaStore one;
    uint32_t v = 0u;
    bool zero = aletheia_store_make(0x00800u, 0u, &s);
    bool made = aletheia_store_make(0x00800u, 1u, &one);
    bool w1 = made && aletheia_read_le(&one, 0x00800u, 1u, &v);
    bool w4 = made && aletheia_read_le(&one, 0x00800u, 4u, &v);
    printf("EMPTY\n");
    printf("SIZE 0 rejected\n");
    printf("SIZE 1 w1 %s\n", w1 ? "ok" : "rejected");
    printf("SIZE 1 w4 %s\n", w4 ? "ok" : "rejected");
    return !zero && w1 && !w4;
}

int main(void) {
    bool bytes_ok;
    bool roundtrip_ok;
    bool width_ok;
    bool unaligned_ok;
    bool mutate_ok;
    bool bounds_ok;
    bool empty_ok;

    printf("ALETHEIA STORE\n");
    printf("SIZE       : %u bytes\n", (unsigned)ALETHEIA_SIZE);
    printf("REGION     : 0x00800..0x00bff (1024 bytes)\n");
    printf("STORE BYTES: %lu\n", (unsigned long)sizeof(struct AletheiaStore));
    printf("\n");

    bytes_ok = aletheia_check_bytes();
    printf("\n");
    roundtrip_ok = aletheia_check_roundtrip();
    printf("\n");
    width_ok = aletheia_check_width();
    printf("\n");
    unaligned_ok = aletheia_check_unaligned();
    printf("\n");
    mutate_ok = aletheia_check_mutate();
    printf("\n");
    bounds_ok = aletheia_check_bounds();
    printf("\n");
    empty_ok = aletheia_check_empty();
    printf("\n");

    printf("SUMMARY\n");
    printf("bytes     : %s\n", bytes_ok ? "true" : "false");
    printf("roundtrip : %s\n", roundtrip_ok ? "true" : "false");
    printf("width     : %s\n", width_ok ? "true" : "false");
    printf("unaligned : %s\n", unaligned_ok ? "true" : "false");
    printf("mutate    : %s\n", mutate_ok ? "true" : "false");
    printf("bounds    : %s\n", bounds_ok ? "true" : "false");
    printf("empty     : %s\n", empty_ok ? "true" : "false");
    if (bytes_ok && roundtrip_ok && width_ok && unaligned_ok &&
        mutate_ok && bounds_ok && empty_ok) {
        printf("ALETHEIA STORE OK\n");
        return 0;
    }
    printf("ALETHEIA STORE BROKEN\n");
    return 1;
}
```

程序大约三百五十行。它没有 `malloc`，没有 `<string.h>`，没有指针类型双关，没有对宿主字节序的假设。所有多字节读写都经过四个移位和四个字节操作，所有地址都经过存储区的跨度检查。编译用 `-std=c99 -O2 -Wall -Wextra -pedantic -Werror`，没有警告。

## 八、真实输出与验收

在本地编译运行，得到以下输出：

```text
ALETHEIA STORE
SIZE       : 262144 bytes
REGION     : 0x00800..0x00bff (1024 bytes)
STORE BYTES: 8

BYTES
ADDR 0x00800
78 56 34 12
LE 0x12345678
BE 0x78563412

ROUNDTRIP
VALUE      READ       OK
0x00000000 0x00000000 true
0x00000001 0x00000001 true
0x7fffffff 0x7fffffff true
0x80000000 0x80000000 true
0xffffffff 0xffffffff true
0x12345678 0x12345678 true
0xdeadbeef 0xdeadbeef true

WIDTH
ADDR 0x00830
78 56 34 12
u8  0x00000078
u16 0x00005678
u32 0x12345678

UNALIGNED
ADDR 0x00841 BYTES 56 34 12 00
VALUE 0x00123456

MUTATE
WRITE 0x11223344 -> 44 33 22 11
POKE  0x00852 = ff
BYTES 44 33 ff 11
READ  0x11ff3344

BOUNDS
REGION END 0x00c00
CASE          RESULT
0x00bfc w4    ok
0x00bfd w4    rejected
0x007ff w4    rejected
0x00c00 w1    rejected
0x00800 w0    rejected
0x00800 w3    rejected

EMPTY
SIZE 0 rejected
SIZE 1 w1 ok
SIZE 1 w4 rejected

SUMMARY
bytes     : true
roundtrip : true
width     : true
unaligned : true
mutate    : true
bounds    : true
empty     : true
ALETHEIA STORE OK
```

逐段看。头部打印机器大小、存储区范围、结构体大小。存储区是 0x00800 到 0x00BFF，1024 字节，右端开区间，最后一个字节是 0x00BFF。`AletheiaStore` 是 8 字节，两个 4 字节字段，没有空洞。

BYTES 段写 0x12345678，打印四个字节 `78 56 34 12`。小端读回 0x12345678，大端对照算出 0x78563412。两个值互为字节反转，说明字节顺序的约定确实影响解释结果。这一段还逐字节检查了 `b[0]=0x78`、`b[1]=0x56`、`b[2]=0x34`、`b[3]=0x12`，不是只看拼装结果。

ROUNDTRIP 段用七个值测试读写往返：0、1、0x7FFFFFFF、0x80000000、0xFFFFFFFF、0x12345678、0xDEADBEEF。每个值写到不同的地址，再读回来，七行都是 `true`。这七个值覆盖了零、最小正数、最大正数、最小负数（按补码看）、全 1、普通模式和任意模式。全 1 的字节是 `FF FF FF FF`，最高位为 1，读回来仍然是无符号的 0xFFFFFFFF，没有符号扩展。

WIDTH 段在同一个地址写 0x12345678，按宽度 1、2、4 读。宽度 1 得 0x78，宽度 2 得 0x5678，宽度 4 得 0x12345678。窄读是宽读的低位片段，宽读不是窄读的简单拼接，而是按权重把小端字节组合起来。这三行验证了宽度参数的作用，也验证了同一个地址在不同宽度下的不同解释。

UNALIGNED 段在 0x00841 读四个字节。这个地址不是 4 的倍数，四个字节是 `56 34 12 00`，读出来是 0x00123456。程序没有因为未对齐而拒绝，也没有执行未对齐的四字节加载。它读四个单字节，拼成一个 32 位值。这个结果说明存储层的读写和对齐无关，对齐是布局层的事。

MUTATE 段先把 0x11223344 写到 0x00850，打印 `44 33 22 11`。然后把 0x00852 的字节改成 0xFF，打印 `44 33 FF 11`。读回来是 0x11FF3344。一个字节的改动改变了整个 32 位值的中间一段，其他三个字节不变。这一段说明多字节值不是不可分割的整体，字节层可以直接改其中一格。

BOUNDS 段打印六个边界情况。0x00BFC 宽度 4 合法，因为它是最后一个能放下四个字节的起点。0x00BFD 宽度 4 拒绝，因为最后一个字节落在 0x00C00，区外。0x007FF 宽度 4 拒绝，因为起点在区前。0x00C00 宽度 1 拒绝，因为右端不属于区。0x00800 宽度 0 拒绝，宽度必须非零。0x00800 宽度 3 拒绝，组件只支持 1、2、4。六行的 `ok` 和 `rejected` 与公式一致。

EMPTY 段测空区和单字节区。size 0 构造拒绝；size 1 宽度 1 可以读一个字节；size 1 宽度 4 拒绝。空区不是“读出来是 0”，是“没有可读的字节”，用构造失败表达。单字节区能读一个字节，不能读四个字节，右端检查把它挡住。

验收标准有七条：

1. 0x12345678 的字节顺序是 `78 56 34 12`，小端读回原值，大端对照是 0x78563412。
2. 七个往返值全部读回原值，包括 0xFFFFFFFF。
3. 同一地址按宽度 1、2、4 读出 0x78、0x5678、0x12345678。
4. 未对齐地址 0x00841 能读出 0x00123456。
5. 单字节改动把 0x11223344 变成 0x11FF3344。
6. 六个边界情况和空区检查全部符合预期。
7. 编译零警告，ASan/UBSan 无报错，输出确定，最宽一行不超过 80 列。

还要做一个失败演示。把读地址改成 0x00BFE，宽度 4，四个字节是 0x00BFE 到 0x00C01，最后一个字节在区外。`aletheia_store_has` 算偏移 `0x00BFE-0x00800=0x003FE`，`size-width=0x00400-4=0x003FC`，`0x003FE <= 0x003FC` 为假，拒绝。如果去掉范围检查，读函数会读到 0x00C01，那个地址仍在 262144 内，不会崩溃，也不会被 ASan 抓住，可它已经不属于这块存储区。这种“越界但在大数组内”的错误最危险：程序照常运行，数据悄悄串到隔壁区域。存储层的范围检查就是为了抓住它，不能依赖消毒器。

另一个失败演示是字节序。如果把读函数的权重反过来，用 `8u*(3-i)`，同一组字节 `78 56 34 12` 会读成 0x78563412。程序不会崩溃，范围检查也通过，可值和写进去的不一样，ROUNDTRIP 的七行会变成 `false`。这类错误只能靠往返检查发现，不能靠内存安全检查发现。字节序错误是逻辑错误，不是越界错误，两种检查都要有。

七条全部通过，程序打印 `ALETHEIA STORE OK` 并返回 0。输出最宽一行 42 列，重复运行完全一致。程序不打印宿主地址、不打印时间、不依赖未初始化内存。所有被读的字节要么刚写过，要么是静态数组的 0 初始化值。

这个程序也在 ASan 和 UBSan 下跑过。所有读写都先检查存储区跨度，所有字节访问都检查 262144 边界，所有移位量都在 0 到 24 之间，所有数组下标都在范围内。两个消毒器都没有报错，输出和普通编译一致。

## 九、交给下一章

这一章定义了 `AletheiaStore`，一个由起始地址和大小组成的存储区描述符。它提供构造、有效性检查、跨度检查、小端读写和字节打印。`aletheia_read_u32` 和 `aletheia_write_u32` 是宽度 4 的包装，底层是通用的 `aletheia_read_le` 和 `aletheia_write_le`，支持宽度 1、2、4。

交给下一章的接口是：

```c
struct AletheiaStore {
    AletheiaAddr base;
    uint32_t size;
};
```

以及 `aletheia_store_make`、`aletheia_store_ok`、`aletheia_store_has`、`aletheia_read_le`、`aletheia_write_le`、`aletheia_read_u32`、`aletheia_write_u32`。下一章的纸带台会拿一个存储区，把它摊成地址、十六进制、十进制三列，再加区间标注。它不会重新实现读写，而是在 `AletheiaStore` 上做显示和标注。

下一章是纸带台。这一章把字节拼成数，下一章把字节摊开给人看。十六进制转储要处理地址对齐、每行字节数、ASCII 列和标注区间。标注要在存储区里记录“这一段是什么”，还要保证标注之间不重叠、不越界。那是一个新的组件 `AletheiaTape`，它的底层还是这一章的存储区和读写函数。

再往后是第十章的总装。总装会把字节层、区间层、整数层、指针层、数组层、结构体层、字符串层、存储层和纸带台放在一个程序里，用一块 256 KiB 的数组串起来。这一章的 `AletheiaStore` 会成为总装里的读写入口，所有多字节值都从这里过。字符串层的字节访问、纸带台的显示、总装的结构体字段，最终都落在同一块数组的同一组地址上。

这一章从“一个字节”走向“四个字节”，从“地址”走向“字节序”，从“直接读”走向“先检查再拼装”。下一章会把视角从“值”拉回“区域”，把一块内存摊开，让每个字节的地址和内容同时可见。字节读写是纸带台的笔，纸带台是字节读写的纸。

把这一章的公式收在一起：拆字节用 $b_i=(v\gg 8i)\&255$，拼字节用 $v=\sum b_i 2^{8i}$，存储区是 $[base,base+size)$，跨度检查是 $addr-base\le size-width$，往返不变量是 $\operatorname{read}(\operatorname{write}(v))=v$。五个式子覆盖了组件的主要行为，也覆盖了四个检查段：BYTES 查拆和拼，ROUNDTRIP 查往返，BOUNDS 查跨度，WIDTH 查宽度。公式不是装饰，每一行都能落到 C，每一行都能在输出里找到对应的数。

下一章的纸带台会重新用到这些式子。它要按地址逐字节显示，显示的是字节，不是拼好的数；它要用 `AletheiaStore` 的跨度检查决定一行显示到哪里；它要标注区间，区间的起点和大小又回到第四章的区间和第六章的偏移。第一至八章的零件在这里开始合流：字节层给格子，指针层给地址，数组层给连续，结构体层给布局，字符串层给终止，存储层给多字节值。下一章把这些零件摆到同一张纸上。
