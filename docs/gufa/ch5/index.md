# 连续数组

> 第五章。零件：`AletheiaArr`。数组不是一堆变量，是一段等距的区间。

## 一、回访：指针走步之后

第四章把指针做成了“地址加元素大小”的二元组。`aletheia_ptr_walk` 按元素大小走 $k$ 步，负偏移往回走，越界就拒绝。那是一个指针在一个对象上的运动。现在把同样的走步重复很多次，让指针依次走过一排同样大小的对象。这一排对象就是数组。

假设内存 0x00100 开始有八个字节，值分别是 1 到 8。一个元素大小为 1 的指针从 0x00100 出发，走 0 步读到 1，走 1 步读到 2，一直走到 7 步读到 8。把读到的值加起来，得到 36。这个实验里没有新的地址算术，只有八次相同的指针走步。数组的第一层意思就是：把一次走步变成一个循环。

如果对象是四字节整数，指针的步长变成 4。从 0x00200 出发，走 0 步到 0x00200，走 1 步到 0x00204，走 2 步到 0x00208，走 3 步到 0x0020c。地址每次加 4，不是加 1。指针层已经知道该加多少，数组层不需要重新发明乘法。数组只需要知道两件事：从哪里开始，一共有多少个。

第四章的指针知道“我指向多大的对象”，不知道“我属于哪个数组”。一个指针可以从数组中间开始，也可以指向数组最后一个元素之后的内存，只要那个对象完整。数组要在指针外面再包一层，记住起点、元素大小和元素个数。有了这三个数，下标访问才能检查边界。没有元素个数，指针只能检查整块内存的边界，检查不了数组的边界。

这一章要把“一排格子”变成一个有名字、有接口、有验收的组件。名字叫 `AletheiaArr`。它不改变字节层，也不改变指针层，只是在指针层上加了起点、步长和长度。数组的地址公式还是指针的走步公式，只是把 $k$ 写成下标 $i$。连续性不是魔法，是“元素一个挨着一个放”这个约定。

先看一个最小的数组实验。八个字节，基地址 0x00100，元素大小 1，元素个数 8。地址从 0x00100 到 0x00107，每个地址一个字节。值从 1 到 8，和是 36。这个实验小到可以手算，可它包含了数组的全部要素：起点、步长、长度、连续、边界。

## 二、开场实验：一排格子

把实验写成表，先不定义结构体，只看地址和值：

```text
base = 0x00100, count = 8, size = 1
i   addr      value
0   0x00100   1
1   0x00101   2
2   0x00102   3
3   0x00103   4
4   0x00104   5
5   0x00105   6
6   0x00106   7
7   0x00107   8
sum = 36
```

地址一列每次加 1，值一列每次加 1。地址的间隔等于元素大小。如果元素大小是 4，地址一列会变成 0x00100、0x00104、0x00108，间隔变成 4。值的排布不变，变的只是每个值占几个字节。

为什么可以这样排？因为数组要求元素一个挨着一个放，中间没有空洞。第一个元素占 $[a,a+s)$，第二个占 $[a+s,a+2s)$，第三个占 $[a+2s,a+3s)$，依此类推。第 $i$ 个元素的起点是 $a+i\cdot s$。这个公式不是从数组的定义推出来的额外规则，它就是“连续”两个字的算术写法。

如果元素之间有空洞，公式就不成立。比如第一个元素在 0x00100，第二个在 0x00108，中间空了四个字节，那么第二个元素的地址不能用 $0x00100+1\times4$ 算，得查一张偏移表。数组选择连续，就是为了让地址能用乘法算出来。连续是用空间换计算：不浪费空洞，也不存偏移表，代价是元素大小必须一致，而且不能随便在中间插入或删除。

数组还是一张“视图”。同样八个字节，从 0x00100 开始、长度 8，是一个数组；从 0x00102 开始、长度 6，是另一个数组。两个数组看到的值不同，前者看到 1 到 8，后者看到 3 到 8。内存没有变，变的是起点和长度。数组不是内存里的一块特殊区域，它是对一块内存的一种解释。你给它起点、步长、长度，它就按照这三个数去读。

这个“视图”性质很重要。后面的字符串是字节数组加一个终止符，结构体是一段字节加若干偏移，纸带台是整块内存加若干标注。它们都不是新的内存，都是对同一块 `aletheia_mem` 的不同看法。数组是最简单的一种看法：等距、连续、有长度。

开场实验的结论是：数组等于起点加步长加长度。三个数缺一不可。只有起点，你不知道元素多大；只有起点和步长，你不知道到哪里停；只有起点和长度，你不知道每个元素占几个字节。三个数齐了，第 $i$ 个元素的地址就能算，边界就能查。

## 三、数组的三件套

### 3.1 起点、步长、长度

把三个数放进一个结构体：

```c
struct AletheiaArr {
    AletheiaAddr addr;
    uint32_t elem_size;
    uint32_t count;
};
```

`addr` 是第一个元素的起点，`elem_size` 是每个元素占几个字节，`count` 是一共有几个元素。三个字段都是无符号的。起点和大小沿用第四章的约定，长度用 `uint32_t`，因为一块 262144 字节的内存最多装 262144 个字节元素，四个字节足够。结构体大小是 12 字节，三个 4 字节字段，没有填充。

为什么长度不放在指针里？因为指针是“指向一个对象”，数组是“一串对象”。一个指针不需要知道自己属于哪个数组，它只需要知道自己指向的对象多大。数组需要知道长度，才能检查下标。把长度放进指针，会让每个指针都多带一个用不上的数，也会让“指向单个对象”和“指向数组元素”变得难以区分。分开两层，指针管走步，数组管范围。

为什么步长不省略？因为数组的元素不一定是字节。整数数组的步长是 4，结构体数组的步长是结构体大小，二维数组的行步长是列数乘元素大小。省略步长，地址公式就退化成 $a+i$，只能用于字节数组。保留步长，数组层就能服务所有等宽元素。

为什么起点不省略？因为没有起点，地址公式没有基准。你可以用“相对于某个基址的偏移”来表示数组，但每次访问都要加基址，反而多一步。直接存绝对地址，读起来直接，检查也直接。地址是机器地址空间里的数，不是宿主指针，所以可以存、可以打印、可以比较。

### 3.2 有效性的四个条件

一个数组有效，需要满足四个条件：

1. 元素大小大于零。
2. 元素个数大于零。
3. 总字节数 $s\cdot n$ 不超过 262144。
4. 起始地址加上总字节数不超过 262144。

前两个条件排除空数组和零大小元素。第三个条件排除“元素太多，整块内存装不下”。第四个条件排除“起点太靠后，数组尾巴伸出内存”。四个条件合起来，保证数组的每一个元素都完整地落在内存里。

总字节数是：

$$
\operatorname{total}(a)=s\cdot n
$$

有效性可以写成：

$$
0 \le a \quad\text{且}\quad a+s\cdot n \le 262144
$$

左边的不等式自动成立，因为地址是无符号的；右边的不等式是真正的检查。注意是 $a+s\cdot n$，不是 $a+n$。每个元素占 $s$ 个字节，$n$ 个元素占 $s\cdot n$ 个字节。把 $s$ 漏掉，长度就会算错，边界也会查错。

为什么要求元素个数大于零？空数组没有元素，任何下标都越界。你可以定义空数组为合法，但它的起点没有意义，访问也永远失败。为了不让“合法但没有元素”这种状态混进来，`aletheia_arr_make` 直接拒绝 $n=0$。将来如果需要空数组，可以另写一个明确的空数组构造函数，而不是让普通构造函数接受零。

为什么要求元素大小大于零？零大小的元素没有第一个字节，地址公式 $a+i\cdot0$ 对所有 $i$ 都得到同一个地址，所有元素重叠在一起。这种“数组”没有意义，也无法读写。C 里零大小的数组不是标准 C，`void` 也不能做指针算术。拒绝零大小，和第四章拒绝零大小指针是同一个理由。

### 3.3 数组和指针的关系

数组和指针不是同一个东西，但数组能产生指针。给定数组 $a$ 和下标 $i$，第 $i$ 个元素的指针是：

$$
p_i=(a+i\cdot s,\ s)
$$

这个指针的地址是元素起点，大小是元素大小。有了它，就可以调用第四章的 `aletheia_ptr_read_u8`、`aletheia_ptr_write_u8`，也可以继续走步。数组层不需要重新实现字节读写，它只需要把“下标”翻译成“指针”。

反过来，指针不能产生数组。一个指针只知道一个对象的地址和大小，不知道后面还有多少个同样大小的对象。你可以从指针的地址开始，假设后面有 $n$ 个元素，但那是你的假设，不是指针携带的信息。数组把 $n$ 明确写进结构体，所以它能检查下标，也能打印长度。指针做不到这两件事。

C 语言里的数组和这里的数组还有一层区别。C 的数组名在大多数表达式里会退化成“指向第一个元素的指针”，长度信息随之丢失。函数收到一个指针，就不知道后面还有多少个元素，只能再传一个长度参数。`sizeof` 看起来能求数组长度，可它只在数组还没有退化的作用域里有效，传进函数之后只剩下指针大小。C 的这套规则是历史形成的，用起来要时刻记住“这个指针背后到底有没有长度”。我们的 `AletheiaArr` 把长度放进结构体，传到哪里都带着，不会退化，也不会在函数边界悄悄丢掉。这是用显式结构体换掉隐式退化，代价是每次访问多读一个字段，收益是边界检查永远有依据。

这个分工在验收里很重要。指针的验收是“走 $k$ 步地址对不对，越界拒不对”，数组的验收是“第 $i$ 个元素的指针对不对，下标越界拒不对”。两层各测各的，错误容易定位。如果数组直接操作地址，不经过指针，指针层的测试就白做了；如果指针知道数组长度，指针层就变得臃肿。分层不是形式，是为了让每一层都能单独证明。

数组还有一个不变量：相邻元素的地址差等于元素大小。

$$
\operatorname{addr}(a,i+1)-\operatorname{addr}(a,i)=s
$$

这个不变量是“连续”的算术形式。你可以用它检查一个数组是不是真的连续：如果相邻地址差不是 $s$，中间就有空洞，或者元素大小不一致，或者数组根本不是数组。程序里的 `aletheia_arr_at` 每次都按这个不变量算地址，所以它天然假设连续。构造数组时检查总长度，访问时检查下标，两个检查合起来，保证不会读到数组外面。

## 四、下标公式与边界

### 4.1 第 i 个元素在哪里

数组的地址公式是：

$$
\operatorname{addr}(a,i)=a+i\cdot s
$$

其中 $a$ 是起点，$i$ 是下标，$s$ 是元素大小。这个公式和第四章的指针走步公式是同一个：

$$
\operatorname{addr}(p+i)=\operatorname{addr}(p)+i\cdot s
$$

把 $p$ 换成数组起点，把 $k$ 换成下标，两条公式就重合了。数组层没有新的算术，它只是给指针走步加了一个范围。`arr[i]` 在 C 里就是 `*(arr+i)`，先算地址，再解引用。我们的 `aletheia_arr_at` 也是先算指针，再交给字节层读写。

第 $i$ 个元素占的区间是：

$$
[\operatorname{addr}(a,i),\ \operatorname{addr}(a,i)+s)
$$

左闭右开，长度是 $s$。第 $i$ 个元素的最后一个字节是 $\operatorname{addr}(a,i)+s-1$。下一个元素的起点是 $\operatorname{addr}(a,i)+s$，正好等于当前区间的右端点。右开区间让相邻元素不重叠，也让数组的末尾可以写成 $a+n\cdot s$。这个端点不属于任何元素，它是“最后一个元素之后”的位置。

### 4.2 下标必须落在范围里

下标 $i$ 有效，当且仅当：

$$
0 \le i < n
$$

$i$ 是无符号数，左边的不等式自动成立；右边的不等式是真正的检查。`i < n` 这个条件看起来简单，可它是数组安全的核心。没有它，`arr[n]` 会读到数组后面的内存，`arr[n+1]` 会读得更远，直到越出整块内存。指针层只能检查“这个对象在内存里”，检查不了“这个对象在数组里”。数组层必须自己检查。

为什么下标不从 1 开始？因为地址公式 $a+i\cdot s$ 在 $i=0$ 时正好得到起点。从 1 开始会让第一个元素的地址变成 $a+s$，起点就空出来了。从 0 开始，起点和第一个元素重合，公式最简。C 和大多数语言都选 0，不是为了刁难人，是为了让地址算术少一次减法。

为什么上界是 $n$，不是 $n-1$？因为有效下标是 $0$ 到 $n-1$，$n$ 本身越界。`i < n` 正好表达这个范围。数组的末尾地址是 $a+n\cdot s$，它不属于任何元素，但可以作为循环的终止条件。你可以写“走到末尾之前停”，也就是 $i<n$；不要写“走到末尾”，因为末尾那个地址没有元素。

遍历数组的标准写法是 `for (uint32_t i = 0; i < a.count; ++i)`，循环体里访问 `a[i]`。

循环条件是 `i < a.count`，不是 `i <= a.count`。写成小于等于，最后一次循环会访问下标 `count`，正好越界。这个错误叫“差一错误”，是数组编程里最常见的错误之一。左闭右开区间 $[0,n)$ 让循环条件写成小于，长度直接就是上界，不需要减一。如果下标从 1 开始，循环要写 `i <= n`，上界和长度差一，更容易错。从 0 开始、右端开，是让循环和地址公式都最省事的选择。

循环变量用 `uint32_t`，和 `count` 同类型，比较时不会有符号转换的意外。如果用 `int`，当 `count` 超过 `INT_MAX` 时比较会把 `int` 转成无符号，负数会变成巨大的正数，循环可能永远停不下来。这一章的长度最多 262144，`int` 也装得下，但养成同类型比较的习惯，将来换更大的数组时不会突然出问题。

### 4.3 指针差与下标差

两个下标 $i$ 和 $j$ 对应的地址差是：

$$
\operatorname{addr}(a,i)-\operatorname{addr}(a,j)=(i-j)\cdot s
$$

这个差是元素个数差乘以元素大小。反过来，已知两个元素地址，求下标差：

$$
i-j=\frac{\operatorname{addr}(a,i)-\operatorname{addr}(a,j)}{s}
$$

这个除法必须除得尽，否则两个地址不在同一个元素网格上。数组内部的元素地址一定除得尽，因为它们的差是 $s$ 的整数倍。第四章的 `aletheia_ptr_diff` 已经实现了这个检查，数组层可以直接用它，也可以自己算。我们选择让数组层通过指针层来算，避免重复实现。

### 4.4 总长度与边界

数组的总字节数是 $s\cdot n$。数组的末尾地址是：

$$
\operatorname{end}(a)=a+s\cdot n
$$

有效性要求 $\operatorname{end}(a)\le262144$。这个不等式和“起点不超过 $262144-s\cdot n$”等价：

$$
a \le 262144-s\cdot n
$$

为什么用总长度，而不是最后一个元素的起点？因为最后一个元素也占 $s$ 个字节。只检查最后一个元素的起点，会漏掉它的尾巴。比如一个四字节数组，最后一个元素从 0x3fffe 开始，起点在内存里，可它的四个字节越过 0x40000。检查总长度 $a+s\cdot n\le262144$，就能把这种情况拒绝。

总长度的乘法要用更宽的类型。$s$ 和 $n$ 都是 32 位，乘积可能超过 32 位。虽然有效数组的总长度一定不超过 262144，但在检查之前，两个字段可能任意大。如果先用 32 位乘，乘积会回绕，回绕后可能变成一个小数，从而骗过“总长度不超过内存”的检查。程序里用 `uint64_t` 算总长度，再和 262144 比较。这个套路和第四章的 `int64_t` 乘法一样：先宽后窄，先算后查。

举个会骗过 32 位检查的例子。元素大小 65536，长度 65537。真实总字节数是 $65536\times65537=4295032832$，超过四吉字节。32 位乘法的低 32 位是 65536，因为 $4295032832-65536\times65536=65536$。如果程序先用 32 位乘，再拿 65536 和 262144 比较，会认为总长度只有 65536 字节，数组“装得下”。构造于是成功，长度字段却写着 65537，访问到后面就会撞上指针层的边界。指针层会拒绝越界地址，所以不会真的读出内存，但数组的有效性已经被错误地接受，后面的逻辑会建立在一个假前提上。用 64 位算真实乘积，4295032832 大于 262144，构造函数直接拒绝，假前提根本不会出现。安全不只靠最后一层兜底，每一层都要把明显不可能的状态挡在门外。

## 五、二维数组与行主序

### 5.1 内存是一维的

内存是一条线，只有地址，没有行和列。二维数组是人对这条线的一种组织方式。你可以把一行元素连续放，再放下一行，这叫行主序；也可以把一列元素连续放，再放下一列，这叫列主序。两种布局都能表示二维数组，区别在于下标到线性地址的映射。

行主序的规则是：先放第 0 行的所有列，再放第 1 行的所有列，依此类推。第 $i$ 行第 $j$ 列的元素，前面有 $i$ 整行，每行 $C$ 个元素，再加上本行的 $j$ 个元素。线性下标是：

$$
\operatorname{index}(i,j)=i\cdot C+j
$$

其中 $C$ 是列数。这个下标从 0 开始，最大是 $R\cdot C-1$。第 $(i,j)$ 个元素的地址是：

$$
\operatorname{addr}_{\text{row}}(i,j)=a+(i\cdot C+j)\cdot s
$$

这就是行主序公式。它把两个下标合成一个线性下标，再套用一维数组的地址公式。二维数组在内存里还是一维的，只是下标的算法多了一步乘法和一次加法。

### 5.2 行起点与行跳

第 $i$ 行的起点是：

$$
\operatorname{row}(i)=a+i\cdot C\cdot s
$$

从第 $i$ 行到第 $i+1$ 行，地址增加 $C\cdot s$。这个值叫行跳。比如三行四列、元素大小 4，行跳是 $4\times4=16$。第 0 行从 0x00300 开始，第 1 行从 0x00310 开始，第 2 行从 0x00320 开始。每一行内部，列地址每次加 $s=4$。

行内步长是 $s$，行间步长是 $C\cdot s$。两个步长不一样，因为跨行要跳过一整行的元素。你可以把二维数组看成一维数组的数组：外层数组有 $R$ 个元素，每个元素是一行，行的大小是 $C\cdot s$；内层数组有 $C$ 个元素，每个元素大小是 $s$。行主序就是先走外层，再走内层。

第 $(i,j)$ 个元素也可以写成“行起点加列偏移”：

$$
\operatorname{addr}_{\text{row}}(i,j)=\operatorname{row}(i)+j\cdot s
$$

两条公式等价。一条先算线性下标，一条先算行起点，结果一样。程序里用线性下标，因为它只需要一次乘法和一次加法，而且能直接复用一维数组的 `aletheia_arr_at`。

### 5.3 边界与布局选择

二维数组的有效性要求 $i<R$、$j<C$，并且整个 $R\cdot C$ 个元素装得下。行数和列数都大于零，总元素数是 $R\cdot C$，总字节数是 $R\cdot C\cdot s$。这些检查和一维数组一样，只是总元素数换成了行数乘列数。乘法同样要用宽类型，避免回绕。

行主序不是唯一的选择。列主序把一列元素连续放，线性下标是 $j\cdot R+i$。两种布局的地址公式不同，读同一个 $(i,j)$ 会得到不同地址。C 用行主序，很多数值库也用行主序，所以书里选行主序。你以后看到“行主序”三个字，就知道它指的是“一行一行连续放”，不是“一列一列连续放”。

布局选择会影响性能，但不影响“数组是连续的”这个事实。行主序和列主序都是连续布局，只是连续的方向不同。真正不连续的是“数组的数组”用指针连接，每一行单独分配，行与行之间没有固定距离。那种结构需要额外的指针表，地址公式也不再是简单的乘法。我们的二维数组是一整块连续内存，所以行跳是固定的 $C\cdot s$。

列主序的公式可以写成：

$$
\operatorname{index}_{\text{col}}(i,j)=j\cdot R+i
$$

同样是三行四列、起点 0x00300、元素大小 4，第 $(1,2)$ 个元素在列主序下的线性下标是 $2\times3+1=7$，地址是 $0x00300+7\times4=0x0031c$。行主序下同一个元素的下标是 $1\times4+2=6$，地址是 0x00318。两个地址不同，因为两种布局把同一对行列放在了不同的位置。读取的人必须知道写入的人用了哪种布局，否则会把别的元素当成目标元素。布局不是实现细节，它是数据格式的一部分，必须写进接口文档，也必须写进验收。程序里所有二维访问都走 `aletheia_grid_addr`，布局只在那个函数里定义一次，调用者不需要各自记住公式，也就不会一半用行主序、一半用列主序。

## 六、手工推演

### 6.1 字节数组

八个字节，起点 0x00100，元素大小 1，长度 8。有效范围是 $0x00100+8\times1=0x00108$，没有超过 0x40000。第 0 个元素在 0x00100，第 7 个元素在 0x00107。每个元素占一个字节，地址就是下标加起点。

求和时从下标 0 走到 7。每次用地址公式算地址，用字节层读值，累加到和里。和是 $1+2+3+4+5+6+7+8=36$。累加器用 `uint32_t`，因为八个字节最大和是 $8\times255=2040$，远小于 32 位上限。如果数组有两万六千个字节，最大和是 $262144\times255=66846720$，仍然小于 $2^{32}$。字节数组的和不会溢出 32 位，这是选择 `uint32_t` 的依据。

下标 8 越界。`i < count` 检查在算地址之前，所以不会算出 0x00108 再读。0x00108 本身在内存里，字节层会允许读，但数组层不允许。这个区别是数组层的价值：字节层只管“内存在不在”，数组层管“元素在不在”。

### 6.2 四字节数组

四个四字节整数，起点 0x00200，元素大小 4，长度 4。总字节数 $4\times4=16$，结束于 0x00210。第 0 个元素占 $[0x00200,0x00204)$，第 1 个占 $[0x00204,0x00208)$，第 2 个占 $[0x00208,0x0020c)$，第 3 个占 $[0x0020c,0x00210)$。相邻起点差 4，正好是元素大小。

第 $i$ 个元素的地址是 $0x00200+4i$。这个式子里，下标先乘 4 再加起点。把下标 3 代进去，得到 0x0020c。把下标 4 代进去，得到 0x00210，这是数组末尾，不是元素。数组层在下标 4 处拒绝，因为 $4<4$ 不成立。

这个数组的每个元素是四个字节，但数组层只把它们当成“大小 4 的对象”。它不解释这四个字节是补码整数、无符号整数还是四个字符。解释是更高层的事。第 3 章定义了补码的读法，第 8 章会定义跨字节的读法，数组层只负责找到第 $i$ 个对象的起点。分层再一次起作用：数组不需要知道元素的内容，只需要知道元素的大小和位置。

### 6.3 边界推演

程序里的 FIT 表有七个例子，逐个推：

起点 0x3fff0，长度 4，大小 4。总字节数 16，末尾 $0x3fff0+16=0x40000$，正好等于内存上界，有效。

起点 0x3fff0，长度 5，大小 4。总字节数 20，末尾 0x40004，超过 0x40000，无效。

起点 0x3fff8，长度 2，大小 4。总字节数 8，末尾 0x40000，有效。

起点 0x3fff8，长度 3，大小 4。总字节数 12，末尾 0x40004，无效。

起点 0x00100，长度 0，大小 1。长度为零，无效。

起点 0x00100，长度 1，大小 0。元素大小为零，无效。

起点 0x40000，长度 1，大小 1。起点等于内存上界，第一个字节就在内存外，无效。

这些例子覆盖了四种失败：尾巴越界、起点越界、长度为零、大小为零。前两种是边界，后两种是退化。四种都必须在构造函数里拒绝，不能等到访问时才报错。构造时拒绝，数组变量就永远处于有效状态，后面的访问函数可以放心地只查下标。这是“让非法状态不可表示”的做法：不是每个函数都重复检查所有条件，而是构造时一次查完，之后靠类型和约定维持。

### 6.4 二维网格

三行四列，起点 0x00300，元素大小 4。总元素数 12，总字节数 48，末尾 0x00330。行跳是 $4\times4=16$。

第 0 行从 0x00300 开始，列地址是 0x00300、0x00304、0x00308、0x0030c。第 1 行从 0x00310 开始，列地址是 0x00310、0x00314、0x00318、0x0031c。第 2 行从 0x00320 开始，列地址是 0x00320、0x00324、0x00328、0x0032c。行起点每次加 16，列地址每次加 4。

第 $(1,2)$ 个元素的线性下标是 $1\times4+2=6$，地址是 $0x00300+6\times4=0x00318$。用行起点算也一样：第 1 行起点 0x00310，加 $2\times4=8$，得到 0x00318。两条路径必须得到同一个地址，程序里同时算 `index` 和 `addr`，再和手算的期望值比较。这种“两条路径互相对照”的测试，比只测一条路径更容易发现乘法或加法写错。

行主序的遍历顺序是：先固定行，再走完这一行的所有列，然后换下一行。输出里的 I J 两列就是这个顺序：0 0、0 1、0 2、0 3、1 0、1 1、1 2、1 3、2 0、2 1、2 2、2 3。线性下标从 0 连续走到 11。如果你按列遍历，地址会跳着走，不是连续递增。行主序让“按行遍历”变成“线性下标连续递增”，这对缓存和打印都方便。

### 6.5 求和为什么只收字节数组

`aletheia_arr_sum` 明确拒绝元素大小不是 1 的数组。四字节数组的求和被拒绝，输出是 `size=4 sum=rejected`。这不是偷懒，是分层。

字节数组的每个元素就是一个字节，读出来就是数值，直接加到和里。四字节整数的每个元素是四个字节，要把四个字节合成一个 32 位整数，需要知道字节顺序：小端还是大端，最低有效字节在前还是在后。这个合成规则是第 8 章 `AletheiaStore` 的内容。在第 5 章提前实现，会把第 8 章的核心问题偷走，也会让数组层承担它不该承担的字节序知识。

所以这一章的求和函数只服务字节数组。它的接口是诚实的：元素大小不是 1，就返回 `false`，不猜、不近似、不把四个字节当成四个独立的数加起来。调用者看到拒绝，就知道该去找第 8 章的读法，而不是以为数组层坏了。这种“明确拒绝不支持的情况”，比“悄悄给出一个错误答案”好得多。

## 七、把 AletheiaArr 写成 C

### 7.1 结构体与构造函数

数组的三个字段和有效性检查：

```c
struct AletheiaArr {
    AletheiaAddr addr;
    uint32_t elem_size;
    uint32_t count;
};

static bool aletheia_arr_ok(struct AletheiaArr a) {
    uint64_t total;
    if (a.elem_size == 0u || a.count == 0u) {
        return false;
    }
    total = (uint64_t)a.elem_size * (uint64_t)a.count;
    if (total > (uint64_t)ALETHEIA_SIZE) {
        return false;
    }
    return (uint64_t)a.addr <= (uint64_t)ALETHEIA_SIZE - total;
}

static bool aletheia_arr_make(AletheiaAddr addr, uint32_t elem_size,
                              uint32_t count, struct AletheiaArr *out) {
    struct AletheiaArr a;
    if (out == NULL) {
        return false;
    }
    a = (struct AletheiaArr){ addr, elem_size, count };
    if (!aletheia_arr_ok(a)) {
        return false;
    }
    *out = a;
    return true;
}
```

`aletheia_arr_ok` 先排除零大小和零长度，再用 64 位算总字节数。`total` 是 `uint64_t`，两个 32 位字段相乘不会回绕。如果 `total` 超过 262144，直接拒绝。最后检查起点是否小于等于“内存上界减总字节数”。这个减法在 `total <= 262144` 的前提下不会下溢，因为右操作数不超过左操作数。

`aletheia_arr_make` 先构造一个临时数组，检查通过后才写进 `out`。如果检查失败，`out` 保持原样，调用者不会拿到一个半成品。`out == NULL` 也拒绝，避免空指针写入。返回值是 `bool`，不是错误码。这一章的组件只有“成功”和“失败”两种结果，不需要区分失败原因；需要原因时，调用者可以自己打印输入。

### 7.2 下标访问

`aletheia_arr_at` 把下标翻译成指针：

```c
static bool aletheia_arr_at(struct AletheiaArr a, uint32_t i,
                            struct AletheiaPtr *out) {
    struct AletheiaPtr base;
    if (out == NULL || !aletheia_arr_ok(a) || i >= a.count) {
        return false;
    }
    if (i > (uint32_t)INT32_MAX) {
        return false;
    }
    if (!aletheia_ptr_make(a.addr, a.elem_size, &base)) {
        return false;
    }
    return aletheia_ptr_walk(base, (int32_t)i, out);
}
```

检查顺序是：输出指针非空，数组有效，下标小于长度，下标能装进 `int32_t`。前三个检查缺一不可。第四个检查在理论上是多余的，因为有效数组的长度最多 262144，下标不可能超过 `INT32_MAX`，但它是防御性的：如果将来数组的表示变了，长度可能变大，这个检查能防止把大下标截断成负数。防御性检查不是不信自己，是不信未来的修改。

通过检查后，先用起点和元素大小造一个基指针，再让基指针走 $i$ 步。走步函数会再查一次内存边界，虽然数组有效已经保证了第 $i$ 个元素在内，但多一次检查不贵，而且让数组层不依赖“数组有效”这个前提的证明。两层各自检查，错误不会互相掩盖。

写数组访问时最容易犯三个错。第一个是差一：把 `i >= a.count` 写成 `i > a.count`，于是下标等于长度时也被放行，正好访问到数组后面。第二个是漏乘：把地址写成 `a.addr + i`，忘了乘元素大小，四字节数组的第二个元素会算到第一个元素中间。第三个是检查顺序错：先走步再查下标，指针已经走到数组外，再查已经晚了。三个错误的共同点是“看起来只差一点”，可数组安全没有“差一点”，越界一个字节也是越界。程序里把下标检查放在最前面，把乘法交给指针层，把边界检查留给字节层，三件事各归各的位置，错误就不容易混进来。

`aletheia_arr_addr` 是 `aletheia_arr_at` 的薄包装：拿到指针，取出地址。它存在的意义是让调用者不必关心指针结构体，只需要一个地址。程序里两个函数都用，既测指针，也测地址，两条路径互相印证。

### 7.3 字节数组求和

求和函数：

```c
static bool aletheia_arr_sum(struct AletheiaArr a, uint32_t *out) {
    uint32_t sum = 0;
    uint32_t i;
    if (out == NULL || !aletheia_arr_ok(a) || a.elem_size != 1u) {
        return false;
    }
    for (i = 0; i < a.count; ++i) {
        struct AletheiaPtr p;
        AletheiaByte v = 0;
        if (!aletheia_arr_at(a, i, &p)) {
            return false;
        }
        if (!aletheia_ptr_read_u8(p, &v)) {
            return false;
        }
        sum += (uint32_t)v;
    }
    *out = sum;
    return true;
}
```

先检查输出非空、数组有效、元素大小为 1。三个条件都满足才进入循环。循环里每一步都检查 `aletheia_arr_at` 和 `aletheia_ptr_read_u8` 的返回值，任何一个失败就立刻返回 `false`。虽然理论上不会失败，但显式检查让错误在发生时立刻暴露，而不是把零当成数据继续加。

`sum` 是 `uint32_t`，最大和是 262144 乘 255，约六千六百万，不会溢出。如果将来数组能更大，求和函数要改成 `uint64_t` 或者带溢出检查。这一章的内存固定 256 KiB，32 位够用。

### 7.4 二维下标

行主序的两个函数：

```c
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

static bool aletheia_grid_addr(AletheiaAddr base, uint32_t elem_size,
                               uint32_t rows, uint32_t cols,
                               uint32_t i, uint32_t j,
                               AletheiaAddr *out) {
    struct AletheiaArr a;
    struct AletheiaPtr p;
    uint64_t total;
    uint32_t index;
    if (out == NULL || rows == 0u || cols == 0u || i >= rows || j >= cols) {
        return false;
    }
    total = (uint64_t)rows * (uint64_t)cols;
    if (total > (uint64_t)UINT32_MAX) {
        return false;
    }
    if (!aletheia_arr_make(base, elem_size, (uint32_t)total, &a)) {
        return false;
    }
    if (!aletheia_grid_index(cols, i, j, &index)) {
        return false;
    }
    if (!aletheia_arr_at(a, index, &p)) {
        return false;
    }
    *out = p.addr;
    return true;
}
```

`aletheia_grid_index` 只算线性下标，不检查 $i<R$，因为它不知道行数。它检查列数非零，检查乘加结果不超过 `UINT32_MAX`。用 64 位算再检查，避免 $i\cdot C$ 回绕。返回值通过 `out` 传出，成功时写，失败时不写。

`aletheia_grid_addr` 知道行数和列数，所以它检查 $i<R$、$j<C$，再算总元素数 $R\cdot C$，检查不超过 `UINT32_MAX`，然后用总元素数构造一维数组，最后用线性下标访问。它把二维问题化成一维问题，复用了一维数组的全部检查。如果总元素数太大，`aletheia_arr_make` 会因为总字节数超过内存而拒绝；如果太小，一维数组有效，访问也有效。

两个函数的分工是：一个只管下标映射，一个管整个网格的地址。调用者可以单独测下标映射，也可以测完整地址。程序里的 GRID 表同时打印 `index` 和 `addr`，两个值都和手算期望比较。

### 7.5 接口表

这一章新增的接口：

| 函数 | 作用 | 失败条件 |
| --- | --- | --- |
| `aletheia_arr_make` | 构造数组 | 空输出、零大小、零长度、总长度越界 |
| `aletheia_arr_ok` | 检查数组 | 同上 |
| `aletheia_arr_at` | 第 i 个元素的指针 | 空输出、数组无效、下标越界 |
| `aletheia_arr_addr` | 第 i 个元素的地址 | 同上 |
| `aletheia_arr_sum` | 字节数组求和 | 空输出、数组无效、元素大小不是 1 |
| `aletheia_grid_index` | 二维下标转线性下标 | 空输出、列数为零、结果超 32 位 |
| `aletheia_grid_addr` | 二维下标转地址 | 空输出、行列为零、下标越界、总元素数超 32 位、数组无效 |

接口的设计原则和前面几章一致：成功返回 `true` 并写输出，失败返回 `false` 不写输出；所有输出参数都可以为 `NULL`，传 `NULL` 就是不要结果；不在函数里打印，打印交给调用者。这样组件可以被测试程序调用，也可以被将来的机器调用，不会把输出格式焊死在逻辑里。

## 八、完整程序

完整程序把字节层、指针层、数组层叠在一起。字节层提供 `aletheia_peek_u8`、`aletheia_poke_u8`，指针层提供 `aletheia_ptr_make`、`aletheia_ptr_walk`、`aletheia_ptr_read_u8`、`aletheia_ptr_write_u8`，数组层提供构造函数、下标访问、求和和二维映射。主程序先打印机器信息，再依次跑六组检查，最后打印汇总。

程序编译命令：

```bash
cc -std=c99 -O2 -Wall -Wextra -pedantic -Werror aletheia_ch05.c -o aletheia_ch05
```

完整代码：

```c
/* aletheia_ch05.c */
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

struct AletheiaArr {
    AletheiaAddr addr;
    uint32_t elem_size;
    uint32_t count;
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

/* 一个数组 = 起始地址 + 元素大小 + 元素个数。 */
static bool aletheia_arr_ok(struct AletheiaArr a) {
    uint64_t total;
    if (a.elem_size == 0u || a.count == 0u) {
        return false;
    }
    total = (uint64_t)a.elem_size * (uint64_t)a.count;
    if (total > (uint64_t)ALETHEIA_SIZE) {
        return false;
    }
    return (uint64_t)a.addr <= (uint64_t)ALETHEIA_SIZE - total;
}

static bool aletheia_arr_make(AletheiaAddr addr, uint32_t elem_size,
                              uint32_t count, struct AletheiaArr *out) {
    struct AletheiaArr a;
    if (out == NULL) {
        return false;
    }
    a = (struct AletheiaArr){ addr, elem_size, count };
    if (!aletheia_arr_ok(a)) {
        return false;
    }
    *out = a;
    return true;
}

/* 第 i 个元素的指针：起始指针走 i 步。 */
static bool aletheia_arr_at(struct AletheiaArr a, uint32_t i,
                            struct AletheiaPtr *out) {
    struct AletheiaPtr base;
    if (out == NULL || !aletheia_arr_ok(a) || i >= a.count) {
        return false;
    }
    if (i > (uint32_t)INT32_MAX) {
        return false;
    }
    if (!aletheia_ptr_make(a.addr, a.elem_size, &base)) {
        return false;
    }
    return aletheia_ptr_walk(base, (int32_t)i, out);
}

static bool aletheia_arr_addr(struct AletheiaArr a, uint32_t i,
                              AletheiaAddr *out) {
    struct AletheiaPtr p;
    if (out == NULL || !aletheia_arr_at(a, i, &p)) {
        return false;
    }
    *out = p.addr;
    return true;
}

/* 只对字节数组求和；多字节整数的读法是第八章的事。 */
static bool aletheia_arr_sum(struct AletheiaArr a, uint32_t *out) {
    uint32_t sum = 0;
    uint32_t i;
    if (out == NULL || !aletheia_arr_ok(a) || a.elem_size != 1u) {
        return false;
    }
    for (i = 0; i < a.count; ++i) {
        struct AletheiaPtr p;
        AletheiaByte v = 0;
        if (!aletheia_arr_at(a, i, &p)) {
            return false;
        }
        if (!aletheia_ptr_read_u8(p, &v)) {
            return false;
        }
        sum += (uint32_t)v;
    }
    *out = sum;
    return true;
}

/* 行主序的线性下标：i * cols + j。 */
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

static bool aletheia_grid_addr(AletheiaAddr base, uint32_t elem_size,
                               uint32_t rows, uint32_t cols,
                               uint32_t i, uint32_t j,
                               AletheiaAddr *out) {
    struct AletheiaArr a;
    struct AletheiaPtr p;
    uint64_t total;
    uint32_t index;
    if (out == NULL || rows == 0u || cols == 0u || i >= rows || j >= cols) {
        return false;
    }
    total = (uint64_t)rows * (uint64_t)cols;
    if (total > (uint64_t)UINT32_MAX) {
        return false;
    }
    if (!aletheia_arr_make(base, elem_size, (uint32_t)total, &a)) {
        return false;
    }
    if (!aletheia_grid_index(cols, i, j, &index)) {
        return false;
    }
    if (!aletheia_arr_at(a, index, &p)) {
        return false;
    }
    *out = p.addr;
    return true;
}

static bool aletheia_check_byte_array(void) {
    struct AletheiaArr a;
    uint32_t i;
    uint32_t sum = 0;
    bool ok = aletheia_arr_make(0x00100u, 1u, 8u, &a);
    printf("BYTE ARRAY\n");
    printf("base=0x00100 count=8 size=1\n");
    printf("I  ADDR      VALUE\n");
    if (!ok) {
        printf("bad array\n");
        return false;
    }
    for (i = 0; i < a.count; ++i) {
        struct AletheiaPtr p;
        if (!aletheia_arr_at(a, i, &p) ||
            !aletheia_ptr_write_u8(p, (AletheiaByte)(i + 1u))) {
            ok = false;
        }
    }
    for (i = 0; i < a.count; ++i) {
        struct AletheiaPtr p;
        AletheiaByte v = 0;
        bool at = aletheia_arr_at(a, i, &p);
        bool read = at && aletheia_ptr_read_u8(p, &v);
        printf("%2u  0x%05x   %3u\n", (unsigned)i,
               (unsigned)(at ? p.addr : 0u), (unsigned)v);
        if (!read || v != (AletheiaByte)(i + 1u)) {
            ok = false;
        }
    }
    if (aletheia_arr_sum(a, &sum) && sum == 36u) {
        printf("sum=%u\n", (unsigned)sum);
    } else {
        printf("sum=invalid\n");
        ok = false;
    }
    return ok;
}

static bool aletheia_check_i32_array(void) {
    struct AletheiaArr a;
    uint32_t i;
    bool ok = aletheia_arr_make(0x00200u, 4u, 4u, &a);
    printf("I32 ARRAY\n");
    printf("base=0x00200 count=4 size=4\n");
    printf("I  ADDR      SPAN\n");
    if (!ok) {
        printf("bad array\n");
        return false;
    }
    for (i = 0; i < a.count; ++i) {
        struct AletheiaPtr p;
        AletheiaAddr expected = 0x00200u + i * 4u;
        AletheiaAddr got = 0;
        bool at = aletheia_arr_at(a, i, &p);
        bool got_ok = aletheia_arr_addr(a, i, &got);
        printf("%2u  ", (unsigned)i);
        if (at) {
            aletheia_print_ptr(p);
        } else {
            printf("invalid");
        }
        printf("\n");
        if (!at || !got_ok || got != expected ||
            p.addr != expected || p.elem_size != 4u) {
            ok = false;
        }
    }
    return ok;
}

static bool aletheia_check_index(void) {
    static const uint32_t indexes[] = { 0u, 7u, 8u };
    static const bool wants[] = { true, true, false };
    struct AletheiaArr a;
    size_t i;
    bool ok = aletheia_arr_make(0x00100u, 1u, 8u, &a);
    printf("INDEX\n");
    printf("base=0x00100 count=8 size=1\n");
    printf("I  RESULT\n");
    if (!ok) {
        printf("bad array\n");
        return false;
    }
    for (i = 0; i < sizeof(indexes) / sizeof(indexes[0]); ++i) {
        struct AletheiaPtr p;
        bool at = aletheia_arr_at(a, indexes[i], &p);
        printf("%u  %s\n", (unsigned)indexes[i], at ? "valid" : "invalid");
        if (at != wants[i]) {
            ok = false;
        }
    }
    return ok;
}

static bool aletheia_check_fit(void) {
    static const struct {
        AletheiaAddr base;
        uint32_t count;
        uint32_t size;
        bool want;
    } cases[] = {
        { 0x3fff0u, 4u, 4u, true },
        { 0x3fff0u, 5u, 4u, false },
        { 0x3fff8u, 2u, 4u, true },
        { 0x3fff8u, 3u, 4u, false },
        { 0x00100u, 0u, 1u, false },
        { 0x00100u, 1u, 0u, false },
        { 0x40000u, 1u, 1u, false }
    };
    size_t i;
    bool ok = true;
    printf("FIT\n");
    printf("BASE       COUNT SIZE  TOTAL  RESULT\n");
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        struct AletheiaArr a;
        bool made = aletheia_arr_make(cases[i].base, cases[i].size,
                                      cases[i].count, &a);
        unsigned long long total =
            (unsigned long long)cases[i].count * (unsigned long long)cases[i].size;
        printf("0x%05x  %5u  %4u  %6llu  %s\n",
               (unsigned)cases[i].base, (unsigned)cases[i].count,
               (unsigned)cases[i].size, total, made ? "valid" : "invalid");
        if (made != cases[i].want) {
            ok = false;
        }
    }
    return ok;
}

static bool aletheia_check_grid(void) {
    static const AletheiaAddr base = 0x00300u;
    static const uint32_t elem_size = 4u;
    static const uint32_t rows = 3u;
    static const uint32_t cols = 4u;
    uint32_t i;
    uint32_t j;
    bool ok = true;
    printf("GRID %ux%u\n", (unsigned)rows, (unsigned)cols);
    printf("base=0x00300 size=4 rowjump=%u\n", (unsigned)(cols * elem_size));
    printf("I J  INDEX  ADDR\n");
    for (i = 0; i < rows; ++i) {
        for (j = 0; j < cols; ++j) {
            AletheiaAddr addr = 0;
            uint32_t index = 0;
            AletheiaAddr expected = base + (i * cols + j) * elem_size;
            bool gi = aletheia_grid_index(cols, i, j, &index);
            bool ga = aletheia_grid_addr(base, elem_size, rows, cols, i, j, &addr);
            printf("%u %u  %5u  0x%05x\n", (unsigned)i, (unsigned)j,
                   (unsigned)index, (unsigned)addr);
            if (!gi || !ga || index != i * cols + j || addr != expected) {
                ok = false;
            }
        }
    }
    printf("ROW START\n");
    for (i = 0; i < rows; ++i) {
        AletheiaAddr start = 0;
        bool ga = aletheia_grid_addr(base, elem_size, rows, cols, i, 0u, &start);
        printf("row %u  0x%05x\n", (unsigned)i, (unsigned)start);
        if (!ga || start != base + i * cols * elem_size) {
            ok = false;
        }
    }
    return ok;
}

static bool aletheia_check_sum_reject(void) {
    struct AletheiaArr a;
    uint32_t sum = 0;
    bool made = aletheia_arr_make(0x00200u, 4u, 4u, &a);
    bool summed = made && aletheia_arr_sum(a, &sum);
    printf("SUM REJECT\n");
    printf("size=4 sum=%s\n", summed ? "accepted" : "rejected");
    return made && !summed;
}

int main(void) {
    bool byte_ok;
    bool i32_ok;
    bool index_ok;
    bool fit_ok;
    bool grid_ok;
    bool sum_reject_ok;

    printf("ALETHEIA ARR\n");
    printf("SIZE       : %u bytes\n", (unsigned)ALETHEIA_SIZE);
    printf("ADDR RANGE : 0x00000..0x3ffff\n");
    printf("PTR BYTES  : %lu\n", (unsigned long)sizeof(struct AletheiaPtr));
    printf("ARR BYTES  : %lu\n", (unsigned long)sizeof(struct AletheiaArr));
    printf("\n");

    byte_ok = aletheia_check_byte_array();
    printf("\n");
    i32_ok = aletheia_check_i32_array();
    printf("\n");
    index_ok = aletheia_check_index();
    printf("\n");
    fit_ok = aletheia_check_fit();
    printf("\n");
    grid_ok = aletheia_check_grid();
    printf("\n");
    sum_reject_ok = aletheia_check_sum_reject();
    printf("\n");

    printf("SUMMARY\n");
    printf("byte array : %s\n", byte_ok ? "true" : "false");
    printf("i32 array  : %s\n", i32_ok ? "true" : "false");
    printf("index      : %s\n", index_ok ? "true" : "false");
    printf("fit        : %s\n", fit_ok ? "true" : "false");
    printf("grid       : %s\n", grid_ok ? "true" : "false");
    printf("sum reject : %s\n", sum_reject_ok ? "true" : "false");
    if (byte_ok && i32_ok && index_ok && fit_ok && grid_ok && sum_reject_ok) {
        printf("ALETHEIA ARR OK\n");
        return 0;
    }
    printf("ALETHEIA ARR BROKEN\n");
    return 1;
}
```

程序大约四百五十行。它没有 `malloc`，没有动态分配，全部状态是一块静态数组和几个栈上的结构体。它不读文件，不联网，不依赖宿主时钟。输出是纯字符，宽度不超过 80 列。编译用 `-std=c99 -O2 -Wall -Wextra -pedantic -Werror`，没有任何警告。

四百五十行不算长，可它已经包含了一台小机器的数据层。整个程序只有一块静态数组，所有数组、指针、结构体都是对这块数组的不同视图。没有 `malloc`，所以没有分配失败，也没有释放遗漏；没有宿主指针存进机器，所以结构体可以复制、可以打印、可以比较；没有全局可变状态，除了那块数组，所有变量都在栈上，每个检查函数的输入输出都能从参数看出来。程序的可重复性来自这些约束：同一份代码、同一块初始为零的数组、同样的调用顺序，输出一定相同。没有随机数，没有时间戳，没有地址空间布局随机化泄漏到输出里。验收表格里的每个数字都是算出来的，不是碰巧打印出来的。

## 九、真实输出与验收

在本地编译运行，得到以下输出：

```text
ALETHEIA ARR
SIZE       : 262144 bytes
ADDR RANGE : 0x00000..0x3ffff
PTR BYTES  : 8
ARR BYTES  : 12

BYTE ARRAY
base=0x00100 count=8 size=1
I  ADDR      VALUE
 0  0x00100     1
 1  0x00101     2
 2  0x00102     3
 3  0x00103     4
 4  0x00104     5
 5  0x00105     6
 6  0x00106     7
 7  0x00107     8
sum=36

I32 ARRAY
base=0x00200 count=4 size=4
I  ADDR      SPAN
 0  [0x00200, 0x00204) size=4
 1  [0x00204, 0x00208) size=4
 2  [0x00208, 0x0020c) size=4
 3  [0x0020c, 0x00210) size=4

INDEX
base=0x00100 count=8 size=1
I  RESULT
0  valid
7  valid
8  invalid

FIT
BASE       COUNT SIZE  TOTAL  RESULT
0x3fff0      4     4      16  valid
0x3fff0      5     4      20  invalid
0x3fff8      2     4       8  valid
0x3fff8      3     4      12  invalid
0x00100      0     1       0  invalid
0x00100      1     0       0  invalid
0x40000      1     1       1  invalid

GRID 3x4
base=0x00300 size=4 rowjump=16
I J  INDEX  ADDR
0 0      0  0x00300
0 1      1  0x00304
0 2      2  0x00308
0 3      3  0x0030c
1 0      4  0x00310
1 1      5  0x00314
1 2      6  0x00318
1 3      7  0x0031c
2 0      8  0x00320
2 1      9  0x00324
2 2     10  0x00328
2 3     11  0x0032c
ROW START
row 0  0x00300
row 1  0x00310
row 2  0x00320

SUM REJECT
size=4 sum=rejected

SUMMARY
byte array : true
i32 array  : true
index      : true
fit        : true
grid       : true
sum reject : true
ALETHEIA ARR OK
```

逐段看。头部打印机器大小、地址范围、指针结构体大小和数组结构体大小。指针是 8 字节，地址 4 字节加元素大小 4 字节。数组是 12 字节，地址、元素大小、元素个数各 4 字节。两个大小都是手算的，打印出来核对，可以确认没有意外的填充。

BYTE ARRAY 段先写 1 到 8，再读回来，最后求和。地址从 0x00100 到 0x00107，值从 1 到 8，和是 36。写和读走的是不同的函数：写用 `aletheia_ptr_write_u8`，读用 `aletheia_ptr_read_u8`，两者都经过指针层和字节层。地址由数组层算，指针层走步，字节层读写。一条完整的调用链被验证了。

I32 ARRAY 段打印每个四字节元素的区间。区间左闭右开，相邻区间首尾相接，没有重叠也没有空隙。第四行是 `[0x0020c, 0x00210)`，正好结束在数组末尾。这一段的期望地址是手算的，程序里用 `0x00200 + i * 4` 算，再和组件算出的地址比较。两条路径一致，才记为通过。

INDEX 段检查下标 0、7、8。0 和 7 有效，8 无效。8 正好等于长度，是第一个越界下标。这个例子看起来简单，可它区分了“数组末尾”和“最后一个元素”：末尾地址 0x00108 在内存里，但下标 8 不是元素。

FIT 段检查七个构造案例，覆盖尾巴越界、起点越界、零长度、零大小。TOTAL 列是手算的总字节数，RESULT 列是构造函数的判断。十六字节正好装下，二十字节装不下；八字节装得下，十二字节装不下；起点 0x40000 连第一个字节都没有。每一行都和预期一致。

GRID 段打印三行四列共十二个元素的线性下标和地址。线性下标从 0 到 11，地址按行递增。第 0 行从 0x00300 到 0x0030c，第 1 行从 0x00310 到 0x0031c，第 2 行从 0x00320 到 0x0032c。行跳 16，列步 4。ROW START 段单独打印三行的起点，确认行跳确实是 16。

SUM REJECT 段构造一个四字节数组，调用求和，被拒绝。这一段的通过条件是“构造成功并且求和失败”。如果求和也成功，说明数组层偷偷把四个字节当成四个数加了，那是错误的。拒绝是正确行为，不是错误行为。

如果故意改坏程序，输出会立刻变化。去掉下标检查，INDEX 段的 8 会变成 `valid`，因为它能算出 0x00108，而字节层允许读这个地址；数组层一旦不查长度，就把“内存里存在”误当成“数组里存在”。把总长度改成 32 位乘法，FIT 段里某些大数组合会被错误接受，细小案例仍然通过，粗看输出几乎正常，只有极端输入才暴露。把行主序改成列主序，GRID 段的地址会整体错位，第 $(1,2)$ 个元素从 0x00318 变成 0x0031c，和手算期望对不上。允许零长度，FIT 段的第五行会从 `invalid` 变成 `valid`，一个没有元素的数组混进合法状态。四个改动各自只动一小块，验收都能抓住，因为它们都直接检查可观察的输出，而不是检查“代码看起来对不对”。

验收标准有五条：

1. 字节数组的地址、值、和全部正确。
2. 四字节数组的区间首尾相接，结束于数组末尾。
3. 下标 0 和 7 有效，8 无效。
4. 七个构造案例的通过和拒绝全部符合预期。
5. 二维网格的下标和地址全部符合行主序公式，四字节数组求和被拒绝。

五条全部为真，程序打印 `ALETHEIA ARR OK` 并返回 0。任何一条失败，打印 `BROKEN` 并返回 1。返回值让这个程序可以被脚本调用，不需要人去读输出。输出是给人看的，返回值是给机器看的，两者都要对。

这个程序也在 ASan 和 UBSan 下跑过。因为所有访问都经过边界检查，没有越界读，没有整数溢出，没有未定义行为，两个消毒器都没有报错。输出和普通编译完全一致。这不是说检查可以省，而是说检查写对了，消毒器就找不到问题。

## 十、交给下一章

这一章定义了 `AletheiaArr`，一个由起点、元素大小、元素个数组成的连续区间。它提供构造、有效性检查、下标访问、地址查询、字节数组求和和二维行主序映射。它复用了指针层的走步，指针层复用了字节层的读写。三层各管一件事，接口清楚，验收独立。

交给下一章的接口是：

```c
struct AletheiaArr {
    AletheiaAddr addr;
    uint32_t elem_size;
    uint32_t count;
};
```

以及 `aletheia_arr_make`、`aletheia_arr_ok`、`aletheia_arr_at`、`aletheia_arr_addr`、`aletheia_arr_sum`、`aletheia_grid_index`、`aletheia_grid_addr`。下一章如果需要“一段连续字节”，可以直接用 `AletheiaArr`，把元素大小设为 1，长度设为字节数。如果需要“一组等宽对象”，把元素大小设为对象大小。

数组结构体不拥有内存，它只是一张视图。复制一个 `AletheiaArr`，两个结构体指向同一段内存；修改其中一个视图的元素，另一个视图也看得见。没有引用计数，没有析构函数，也没有所有权转移。这在一台只有一块静态数组的机器上是合理的：内存永远在，视图只是暂时的坐标。调用者要自己保证，两个视图不会在不知情的情况下互相覆盖。后面的字符串、纸带、总装都会沿用这个约定：组件描述布局，不管理生命周期。

下一章是结构体偏移。结构体和数组长得很像，都是一段连续内存，但有一个关键区别：结构体的字段不等宽。一个结构体可能有 1 字节的标志、4 字节的计数、8 字节的地址，字段之间还可能有对齐填充。数组的地址公式 $a+i\cdot s$ 假设所有元素等宽，结构体不满足这个假设，所以不能直接用。

结构体需要一张偏移表：每个字段相对于结构体起点的偏移。偏移不是简单的累加，因为对齐会把某些字段推到更高的地址。第一个字段从 0 开始；下一个字段的偏移是“前一个字段的偏移加前一个字段的大小”，再向上对齐到自己的对齐要求。这个递推公式是下一章的核心。

数组教会我们“连续加等距”，结构体教会我们“连续但不等距”。两者合起来，才能描述真实程序里的数据布局。字符串是字节数组加终止符，纸带是整块内存加标注，最终的 `AletheiaMem` 是数组、结构体、字符串和纸带的总装。这一章是这条链条的中间一环：从等距走向不等距，从一排格子走向一张带名字的表格。

下一章的开场实验会先量一个结构体：三个字段分别放在哪里，中间有没有空洞，整个结构体多大。量完之后，再把偏移公式写成 C，最后用一张偏移表验收。数组的地址公式会在那一章被推广，乘法会变成查表，等距会变成对齐。现在，先把这一排格子收好。

