# 结构体偏移

> 第六章。零件：`AletheiaStruct`。结构体不是几个变量，是一张带空洞的地址表。

## 一、回访：数组留下的等距

第五章把数组写成“起点加元素大小加元素个数”。第 $i$ 个元素的地址是 $a+i\cdot s$，所有元素等距、连续、同样大。这个公式能成立，靠的是一个很强的前提：每个元素占的字节数一样。只要元素大小一样，第几个元素就能用乘法直接算出来，不需要额外的表。

结构体打破了这个前提。一个结构体里的字段可以一个字节，也可以四个字节、八个字节。它们还可能有不同的对齐要求。字段大小不一样，就没有一个统一的步长，不能用乘法从字段编号直接算地址。数组的公式在这里失效了，得换一种表示：给每个字段记一个偏移，访问时查表。

这一章要做的事，说穿了只有一句：把数组公式里的 $i\cdot s$ 换成 $\operatorname{offset}(f)$。数组用乘法，结构体用查表。表是提前算好的，算法是“前一个字段的末尾，向上对齐到当前字段的对齐要求”。对齐会在字段之间留下空洞，空洞不是浪费，是让每个字段落在它该在的地址上。

上一章的数组还有一个性质：整个数组的大小是 $s\cdot n$，没有尾部空洞。结构体不一样，最后一个字段结束后，整个结构体还要再补齐一次，补到最大对齐的整数倍。这个尾部补齐看起来多余，可它是“结构体数组”能保持对齐的关键。没有它，第二个结构体的字段就会错位。这一章会把这件事推一遍。

先从一个小实验开始。四个字段：一个字节的标志，四个字节的计数，一个字节的代码，八个字节的时间戳。把它们紧挨着放，偏移是 0、1、5、6，总长 14。可四字节计数落在偏移 1，八字节时间戳落在偏移 6，都不是各自对齐的整数倍。加上对齐之后，偏移变成 0、4、8、16，总长 24。多了十个字节的空洞，换来每个字段都落在对齐的位置上。

这个实验会引出三个问题：对齐到底怎么算，偏移怎么递推，结构体总大小为什么还要再补一次。三个问题都有公式，也都能落到 C 的一行代码里。数组教会我们“等距”，结构体教会我们“不等距但可查表”。两种布局合起来，才够描述真实的数据。

## 二、开场实验：四个字段，两个空洞

先不写结构体，只把四个字段的规格列出来：

```text
字段   大小   对齐
flag    1      1
count   4      4
code    1      1
stamp   8      8
```

如果完全紧挨着放，第一个字段从 0 开始，第二个从 1 开始，第三个从 5 开始，第四个从 6 开始，末尾是 14。这个布局没有空洞，payload 是 14 字节。可它有两个问题：`count` 的偏移是 1，不是 4 的倍数；`stamp` 的偏移是 6，不是 8 的倍数。按对齐规则，这两个字段都“站歪了”。

加上对齐之后，第一个字段仍在 0。第二个字段要从 1 向上推到 4 的倍数，得到 4，中间留下 $[1,4)$ 三个字节的空洞。第二个字段占 $[4,8)$，末尾是 8。第三个字段对齐要求是 1，从 8 开始正好，占 $[8,9)$，末尾是 9。第四个字段要从 9 向上推到 8 的倍数，得到 16，中间留下 $[9,16)$ 七个字节的空洞。第四个字段占 $[16,24)$，末尾是 24。24 已经是 8 的倍数，结构体总大小就是 24。

payload 还是 14，空洞是 $3+7=10$，总大小 $14+10=24$。十个空洞字节里没有数据，可它们的位置是确定的，不是随机的。任何一个按同样规则计算的程序，都会得到同样的偏移和同样的大小。布局是数据格式的一部分，不是编译器的自由发挥。

现在把字段换个顺序：先放八字节时间戳，再放四字节计数，再放两个一字节字段。偏移变成 0、8、12、13，末尾 14。14 向上对齐到 8 的倍数，得到 16，尾部留 $[14,16)$ 两个字节。payload 还是 14，空洞只有 2，总大小 16。同样四个字段，换一个顺序，结构体从 24 字节缩到 16 字节。

这个对比说明两件事。第一，对齐产生的空洞大小取决于字段顺序，把大对齐的字段放在前面，通常能减少空洞。第二，结构体大小不一定是 payload 之和，末尾可能还有尾部空洞。重排字段不是免费的：字段顺序变了，代码里按名字访问不受影响，可按偏移访问、按二进制格式读写的代码会受影响。布局一旦公开，就不能随便改。

真实程序里，结构体布局经常是文件格式或网络协议的一部分。一个文件头可能有魔数、版本、标志、长度、时间戳，每个字段的位置和大小都写在规范里。读文件的程序按偏移去取字段，不会按名字，因为文件里没有名字。如果写文件的程序换了一个字段顺序，读文件的程序不会知道，它会把版本号读成长度，把时间戳读成标志。二进制格式的兼容性，本质上就是布局的兼容性。你可以新增字段、保留旧字段，但不能随意移动旧字段，除非同时升级版本号并写迁移代码。

这也是为什么这一章把偏移表打印出来。打印出来的表就是一份可以核对的规范：哪个字段在哪个偏移，占几个字节，对齐多少，空洞在哪里。两个程序如果对同一份表达成一致，就能读同一块内存；如果表不一致，哪怕字段名一样，读出来的东西也可能完全不同。数组的公式是隐式的，所有元素自动等距；结构体的布局是显式的，必须有人把表写下来。显式带来麻烦，也带来可检查性。

开场实验的结论是：结构体等于起点加一张偏移表，偏移由“前一个字段末尾向上对齐”递推得到，总大小由“最后一个字段末尾向上对齐到最大对齐”得到。数组的等距是这张表的一个特例：所有字段大小相同、对齐相同，偏移就是 $i\cdot s$。结构体把特例推广成一般情况。

## 三、对齐与偏移

### 3.1 什么是对齐

一个字段的对齐要求是一个正整数 $a$，通常取 1、2、4、8、16。字段的偏移 $o$ 满足

$$
o \bmod a = 0
$$

就说这个字段是“按 $a$ 对齐”的。换句话说，$o$ 是 $a$ 的整数倍。四字节字段的偏移应该是 4 的倍数，八字节字段的偏移应该是 8 的倍数。一字节字段的对齐要求是 1，任何偏移都是 1 的倍数，所以一字节字段永远对齐。

为什么要有对齐？一个原因是硬件。很多处理器读四字节字时要求地址是 4 的倍数，读八字节要求 8 的倍数；不对齐的访问可能变慢，也可能直接触发异常。另一个原因是布局的一致性：如果每个多字节字段都从自己的对齐边界开始，那么按字段类型读写时，地址计算简单，边界也整齐。即使一台机器支持任意字节地址访问，保持对齐仍然能让布局规则统一，让不同程序对同一份数据有同样的解释。

Aletheia 的字节层能读任意地址的一个字节，所以从“能不能读”的角度看，不对齐也能读。可这一章仍然要求对齐。理由不是硬件强制，而是布局纪律：后面的多字节读写、结构体数组、纸带标注都要依赖“字段从对齐边界开始”这个约定。约定一旦立下，检查就要严格，不能因为当前机器能读就放行。

对齐要求必须是 2 的幂。这个限制不是数学上的必然，是工程上的选择。2 的幂可以用位运算快速判断和补齐，1、2、4、8、16 覆盖了常见的标量类型。C 语言里每个完整对象类型都有一个对齐要求，可以用 `_Alignof` 查询；结构体的对齐要求是成员对齐要求的最大值。这一章的规则和 C 的自然对齐一致，但不用宿主编译器去查，而是把对齐写进规格表。写进表里的好处是跨平台：不管宿主是 32 位还是 64 位，这张表都是同一份，算出的偏移也是同一份。对齐 3、5、6 这样的数也能定义，但补齐公式要除法和取模，检查也更麻烦。这一章的 `aletheia_align_up` 明确拒绝非 2 的幂，BAD 表里的 `align 3` 就是这条规则的验收。

### 3.2 向上对齐公式

把一个数 $n$ 向上补齐到 $a$ 的整数倍，记作

$$
\operatorname{align}(n,a)=\left\lceil\frac{n}{a}\right\rceil a
$$

这个公式的意思是：找到不小于 $n$ 的最小 $a$ 的倍数。$n=1,a=4$ 时，结果是 4；$n=4,a=4$ 时，结果还是 4，已经对齐的数不需要再补；$n=5,a=4$ 时，结果是 8；$n=9,a=8$ 时，结果是 16。

用整数运算写，向上取整可以变成向下取整加一：

$$
\left\lceil\frac{n}{a}\right\rceil=\left\lfloor\frac{n+a-1}{a}\right\rfloor
$$

所以

$$
\operatorname{align}(n,a)=\left\lfloor\frac{n+a-1}{a}\right\rfloor a
$$

这个式子在 $n$ 已经是 $a$ 的倍数时也对：$n=4,a=4$，$(4+3)/4$ 向下取整是 1，乘 4 得 4。加 $a-1$ 再除，正好把“刚好整除”的情况留在原地，把“差一点”的情况推到下一个倍数。

当 $a$ 是 2 的幂时，还有更快的写法：

$$
\operatorname{align}(n,a)=(n+a-1)\ \&\ \sim(a-1)
$$

`&` 是按位与，`~` 是按位取反。$a-1$ 的二进制是低位全 1，取反后低位全 0，与运算就把低位清零，相当于向下取整到 $a$ 的倍数。先加 $a-1$ 再清零，就变成向上取整。比如 $a=4$，$a-1=3$ 是二进制 `11`，取反是 `...11111100`；$n=5$ 加 3 得 8，与掩码后还是 8。$n=4$ 加 3 得 7，与掩码后是 4。这个写法要求 $a$ 是 2 的幂，否则掩码清掉的不是完整的低位，结果没有意义。

程序里的 `aletheia_align_up` 用 64 位做加法和掩码，再检查结果是否超过 32 位。$n$ 接近 `UINT32_MAX` 时，$n+a-1$ 可能超过 32 位，用 32 位算会回绕，回绕后可能变成一个小数，骗过检查。ALIGN 表最后一行的 $n=4294967293$、$a=8$ 就是这种例子：真实结果超过 32 位，函数必须拒绝，不能返回一个回绕后的值。

### 3.3 偏移递推

有了对齐函数，字段偏移可以递推。设字段 $0$ 到 $k$ 的规格是 $(s_0,a_0)$ 到 $(s_k,a_k)$，偏移记作 $o_0$ 到 $o_k$。第一个字段从结构体起点开始：

$$
o_0=0
$$

第 $k$ 个字段的偏移是“前一个字段的末尾”向上对齐到自己的对齐要求：

$$
o_k=\operatorname{align}(o_{k-1}+s_{k-1},a_k),\quad k\ge1
$$

前一个字段的末尾是 $o_{k-1}+s_{k-1}$。如果它正好是 $a_k$ 的倍数，当前字段就紧挨着放，没有空洞；如果不是，就向上推到下一个倍数，中间的空洞大小是

$$
p_k=o_k-(o_{k-1}+s_{k-1})
$$

这个 $p_k$ 是非负的，因为向上对齐只会往后推，不会往前拉。第一个字段的空洞定义为 0，因为 $o_0=0$，它从起点开始，前面没有东西。

递推的每一步只依赖前一个字段的末尾和当前字段的对齐要求，不依赖后面。这意味着可以顺序扫描一遍规格表，边算边填偏移。时间复杂度是字段数的一次方，空间复杂度是一张字段表。字段数最多八个，常数很小，不需要更聪明的算法。

数组的偏移可以套进这个递推：所有字段大小都是 $s$，对齐都是 $a$，且 $s$ 是 $a$ 的倍数。$o_0=0$，$o_1=\operatorname{align}(s,a)=s$，$o_2=\operatorname{align}(2s,a)=2s$，依此类推，$o_k=k\cdot s$。数组公式是结构体递推在“所有字段等宽且自然对齐”时的特例。这个视角把两章连起来：数组不是另一种东西，是结构体的一种整齐情况。

### 3.4 结构体总大小与尾部空洞

最后一个字段的末尾是：

$$
\operatorname{end}(s)=o_{n-1}+s_{n-1}
$$

结构体的对齐要求是所有字段对齐要求的最大值：

$$
a_{\max}=\max(a_0,a_1,\dots,a_{n-1})
$$

结构体总大小不是 $\operatorname{end}(s)$，而是

$$
\operatorname{size}(s)=\operatorname{align}(\operatorname{end}(s),a_{\max})
$$

也就是把末尾再向上补齐到最大对齐的整数倍。末尾和总大小之间的空洞叫尾部空洞：

$$
p_{\text{tail}}=\operatorname{size}(s)-\operatorname{end}(s)
$$

为什么需要尾部空洞？因为结构体经常放进数组。数组第 $i$ 个元素的结构体起点是

$$
b_i=\operatorname{base}+i\cdot\operatorname{size}(s)
$$

结构体内部的字段地址是

$$
\operatorname{addr}(i,f)=b_i+\operatorname{offset}(f)
$$

如果 $\operatorname{size}(s)$ 不是 $a_{\max}$ 的倍数，那么 $i\cdot\operatorname{size}(s)$ 可能破坏对齐。哪怕第 0 个结构体的每个字段都对齐，第 1 个结构体的字段也可能歪掉。把总大小补齐到 $a_{\max}$ 的倍数，$i\cdot\operatorname{size}(s)$ 就总是 $a_{\max}$ 的倍数，每个元素内部的字段都能保持对齐。

还有一个前提：数组的基地址本身要按 $a_{\max}$ 对齐。如果基地址是 0x00401，那么第 0 个结构体的四字节字段在 0x00405，仍然歪。程序里的数组实验用 0x00440 和 0x00458，两个都是 8 的倍数，满足这个前提。真实分配器分配结构体数组时，也要保证基地址对齐。这一章的组件只检查结构体本身，基地址的对齐由调用者保证，验收里会显式检查。

### 3.5 字段区间和空洞

第 $k$ 个字段占的区间是：

$$
[\operatorname{base}+o_k,\ \operatorname{base}+o_k+s_k)
$$

左闭右开，长度是 $s_k$。相邻字段之间如果有空洞，空洞区间是

$$
[\operatorname{base}+o_{k-1}+s_{k-1},\ \operatorname{base}+o_k)
$$

这个区间可能为空，当 $o_k=o_{k-1}+s_{k-1}$ 时，两个字段首尾相接，没有空洞。尾部空洞是

$$
[\operatorname{base}+\operatorname{end}(s),\ \operatorname{base}+\operatorname{size}(s))
$$

所有字段区间互不重叠，所有空洞区间也互不重叠，字段和空洞合起来正好覆盖整个结构体。这是结构体布局的“划分”性质：结构体是一段连续内存，每个字节要么属于某个字段，要么属于某个空洞，没有第三种。

payload 是字段大小之和：

$$
\operatorname{payload}(s)=\sum_{k=0}^{n-1}s_k
$$

padding 是所有空洞之和，包括字段间空洞和尾部空洞：

$$
\operatorname{padding}(s)=\operatorname{size}(s)-\operatorname{payload}(s)
$$

于是

$$
\operatorname{size}(s)=\operatorname{payload}(s)+\operatorname{padding}(s)
$$

这个等式看起来是废话，可它是验收里的一个重要检查：如果程序算出的 payload 加 padding 不等于总大小，说明偏移表或空洞计算有错。输出里的 `PAYLOAD ... PADDING ... TAIL ...` 行就是这条等式。

## 四、偏移表与不变量

### 4.1 AletheiaStruct 的三层

结构体的描述分三层。第一层是规格：每个字段的大小和对齐要求，这是输入。第二层是偏移：每个字段相对结构体起点的位置，这是计算结果。第三层是结构体本身：基地址、总大小、字段数、偏移表，这是可传递的描述。

`AletheiaStruct` 把第三层打包成一个结构体：

```c
struct AletheiaField {
    uint32_t offset;
    uint32_t size;
    uint32_t align;
};

struct AletheiaStruct {
    AletheiaAddr addr;
    uint32_t size;
    uint32_t field_count;
    struct AletheiaField fields[8];
};
```

字段表直接嵌在结构体里，最多八个字段。没有指针，没有动态分配，复制一个 `AletheiaStruct` 就是复制整张表。为什么定八个？因为这一卷的结构体都很小，八个足够覆盖标志、计数、代码、时间戳、地址、长度这些常见字段。定长数组让结构体大小可预测，也避免了“字段表放在哪里、谁释放”的问题。字段数超过八个，构造函数直接拒绝，调用者可以拆成嵌套结构体。

`AletheiaField` 是 12 字节：偏移、大小、对齐各 4 字节。`AletheiaStruct` 是 108 字节：基地址 4 字节，总大小 4 字节，字段数 4 字节，字段表 $8\times12=96$ 字节，合计 108。程序头部打印 `FIELD BYTES : 12` 和 `STRUCT BYTES: 108`，读者可以核对。这个大小对一台 256 KiB 的机器来说可以接受，一个描述符占 108 字节，八个描述符还不到 1 KiB。

描述符本身也是一块内存，也有布局。它的字段表是宿主 C 的数组，`AletheiaField` 的对齐和填充由宿主编译器决定。我们不给描述符再造一个描述符，否则会无穷回归：描述符的描述符又需要描述符。这里的边界是：描述符是宿主侧的工具，用来描述机器内存；它自己的布局由宿主 C 保证，只在本程序里使用。如果将来要把描述符也放进机器，就必须为它写一张固定的偏移表，按字节读写，不能再依赖宿主结构体。到那时，这一章的偏移表正好可以用来描述描述符自己。现在不做，是因为没有必要，也是因为递归描述会让第一章的字节层重新变成唯一的地基。

### 4.2 五条不变量

一个有效的 `AletheiaStruct` 要满足五条不变量：

1. 字段数在 1 到 8 之间，总大小大于零。
2. 基地址加总大小不超过 262144，整个结构体落在内存里。
3. 每个字段的大小大于零，对齐是 2 的幂，偏移是自身对齐的整数倍。
4. 第一个字段的偏移是 0，字段按偏移递增，互不重叠，且都落在总大小以内。
5. 总大小是最大对齐的整数倍，保证结构体数组的每个元素都对齐。

第 3 条里的“偏移是自身对齐的整数倍”就是 $o_k\bmod a_k=0$。第 4 条里的“互不重叠”是 $o_k\ge o_{k-1}+s_{k-1}$。第 5 条是 $\operatorname{size}(s)\bmod a_{\max}=0$。这些条件合起来，保证结构体的每个字段都能被安全访问，结构体数组的每个元素也能保持对齐。

注意，`aletheia_struct_ok` 检查的是这些不变量，不是“偏移必须等于递推算出的最小值”。一个手工构造的结构体可以在字段之间留更多空洞，只要仍然对齐、不重叠、落在总大小内，`ok` 就会接受。这是有意的：有效性描述的是“能不能安全访问”，不是“布局是否最紧凑”。构造函数 `aletheia_offset_table` 产生的是最紧凑的规范布局；`ok` 允许更松的布局，方便将来手工调整。验收里两者分开：LAYOUT 表检查规范布局的具体偏移，BAD 表检查非法输入被拒绝。

手工构造一个非法描述符很容易。把第二个字段的偏移从 4 改成 2，四字节字段就不再是 4 的倍数，`ok` 会在偏移对齐那一行返回 `false`。把第三个字段的偏移从 8 改成 6，它就和第二个字段的区间 $[4,8)$ 重叠，`ok` 会在不重叠检查那一行返回 `false`。把第一个字段的偏移从 0 改成 4，结构体起点前面空出四个字节，`ok` 会在“第一个字段偏移为 0”那一行返回 `false`。把总大小从 24 改成 20，最后一个字段的区间 $[16,24)$ 就超出总大小，`ok` 会在字段区间检查那一行返回 `false`。每一种改动只破坏一条不变量，检查顺序决定哪一条先报错，但最终结果都是拒绝。这种“一条不变量对应一个检查”的写法，让失败原因可以定位，不需要在一大段条件里猜。

### 4.3 为什么不用宿主结构体

宿主 C 也有结构体，`sizeof(struct Sample)` 也能给出大小，`offsetof` 也能给出偏移。为什么还要自己算一张表？原因有三个。

第一，宿主的布局规则不完全是标准规定的。字段顺序和第一个字段偏移 0 是标准保证的，可字段之间插多少填充、结构体总大小怎么补，标准只给了约束，具体值由 ABI 决定。同一个结构体，在 32 位和 64 位平台上可能大小不同，在 ARM 和 x86 上也可能不同。书里的机器要跨平台可重复，就不能把宿主布局当成规范。

第二，Aletheia 的结构体描述要能放进机器。宿主结构体里有编译器插入的填充，这些填充对机器来说不可见；机器需要一张显式的偏移表，才能按字节访问字段。`offsetof` 是编译期宏，机器内部没有编译器，用不了。自己算表，表就是数据，可以存、可以打印、可以检查。

第三，自己算表能验收。宿主结构体的大小是编译器给的，你只能相信它；自己算表，每一步都能打印，偏移、空洞、总大小都能和手算对照。教学上，看得见的计算比看不见的约定更有价值。工程上，跨平台的数据格式本来就应该显式定义布局，不能依赖编译器。

这并不是说宿主结构体不能用。宿主程序里用结构体组织代码很方便，`offsetof` 也是标准宏。这一章的程序只是把布局规则显式化，用一张表代替编译器的隐式填充。读者可以把表打印出来，和宿主 `sizeof`、`offsetof` 对照，看看两者是否一致。一致是好事，不一致也不是错，因为书里的规则是自洽的。

## 五、手工推演

### 5.1 自然顺序的偏移

拿开场实验的四个字段，按自然顺序走一遍递推。

字段 0：`flag`，大小 1，对齐 1。偏移 $o_0=0$，末尾 $0+1=1$，空洞 0。

字段 1：`count`，大小 4，对齐 4。前一个末尾是 1，向上对齐到 4 的倍数，得到 4。偏移 $o_1=4$，空洞 $4-1=3$，末尾 $4+4=8$。

字段 2：`code`，大小 1，对齐 1。前一个末尾是 8，向上对齐到 1 的倍数还是 8。偏移 $o_2=8$，空洞 0，末尾 9。

字段 3：`stamp`，大小 8，对齐 8。前一个末尾是 9，向上对齐到 8 的倍数，得到 16。偏移 $o_3=16$，空洞 $16-9=7$，末尾 $16+8=24$。

末尾 24 已经是最大对齐 8 的倍数，总大小 24，尾部空洞 0。payload 是 $1+4+1+8=14$，padding 是 $3+0+7+0=10$，$14+10=24$。偏移表是 0、4、8、16。字段区间是 $[0x00400,0x00401)$、$[0x00404,0x00408)$、$[0x00408,0x00409)$、$[0x00410,0x00418)$。空洞是 $[0x00401,0x00404)$ 和 $[0x00409,0x00410)$。

注意字段 1 和字段 2 的偏移差是 4，但它们的大小是 4 和 1。字段 1 的末尾是 8，字段 2 从 8 开始，正好接上。如果字段 2 是四字节，它也会从 8 开始，因为 8 已经是 4 的倍数。偏移递推不是“前一个偏移加前一个大小”这么简单，它还要看当前字段的对齐要求。前一个末尾恰好对齐时，当前字段紧挨着；不对齐时，才补空洞。

### 5.2 重排后的偏移

把顺序换成 `stamp`、`count`、`flag`、`code`。

字段 0：`stamp`，大小 8，对齐 8。偏移 0，末尾 8，空洞 0。

字段 1：`count`，大小 4，对齐 4。前一个末尾 8 是 4 的倍数，偏移 8，空洞 0，末尾 12。

字段 2：`flag`，大小 1，对齐 1。前一个末尾 12，偏移 12，空洞 0，末尾 13。

字段 3：`code`，大小 1，对齐 1。前一个末尾 13，偏移 13，空洞 0，末尾 14。

末尾 14，最大对齐 8，向上对齐到 16，总大小 16，尾部空洞 2。payload 14，padding 2，$14+2=16$。偏移表是 0、8、12、13。字段区间是 $[0x00420,0x00428)$、$[0x00428,0x0042c)$、$[0x0042c,0x0042d)$、$[0x0042d,0x0042e)$，尾部空洞是 $[0x0042e,0x00430)$。

同样的字段，同样的 payload，自然顺序 24 字节，重排后 16 字节，省了 8 字节。省下来的不是数据，是空洞。把大对齐的字段放前面，小字段放后面，空洞通常更少。这条经验不是绝对的，最优顺序要按对齐和大小排，但“大的先放”是一个好的起点。

重排有代价。字段顺序是布局的一部分，如果一份二进制数据是按自然顺序写的，你按重排后的表去读，就会把 `count` 读到 `stamp` 的位置。结构体描述的字段顺序必须和数据的实际顺序一致，不能只看名字。程序里的两张 LAYOUT 表用不同的基地址和不同的顺序，各自验收，互不干扰。

### 5.3 结构体数组的步长

结构体数组的第 $i$ 个元素从 $\operatorname{base}+i\cdot\operatorname{size}(s)$ 开始。自然顺序的结构体大小是 24，基地址 0x00440。第 0 个元素在 0x00440，第 1 个在 $0x00440+24=0x00458$，第 2 个在 0x00470，依此类推。每个元素内部的字段偏移都是 0、4、8、16，所以第 1 个元素的字段地址是：

`flag`：$0x00458+0=0x00458$，对齐 1，成立。

`count`：$0x00458+4=0x0045c$，对齐 4，$0x45c\bmod4=0$，成立。

`code`：$0x00458+8=0x00460$，对齐 1，成立。

`stamp`：$0x00458+16=0x00468$，对齐 8，$0x468\bmod8=0$，成立。

四个字段全部对齐，输出里的 ARRAY STRIDE 表两行都是 `ok ok ok ok`。这个 `ok` 不是随便打印的，程序对每个字段算了 $(base+offset)\bmod align$，为 0 才打印 `ok`。

如果结构体大小不是 24，而是 14，第 1 个元素就从 $0x00440+14=0x0044e$ 开始。`count` 的地址是 $0x0044e+4=0x00452$，$0x452\bmod4=2$，不对齐。`stamp` 的地址是 $0x0044e+16=0x0045e$，$0x45e\bmod8=6$，也不对齐。只差一个尾部补齐，整个数组的对齐就崩了。尾部空洞不是浪费，是结构体数组的“防错垫片”。

这个推演还说明，结构体大小必须是最大对齐的倍数，而不是“最后一个字段的对齐”的倍数。自然顺序的最大对齐是 8，末尾 24 已经是 8 的倍数，所以尾部空洞为 0。重排后的末尾是 14，不是 8 的倍数，补到 16。如果最大对齐是 4，末尾 14 补到 16，尾部空洞还是 2，可补齐的目标变成了 4 的倍数。总大小的规则只用最大对齐，不用每个字段各自的对齐。

嵌套结构体可以套进同一套规则。一个内层结构体作为外层字段时，它的大小是内层总大小，它的对齐是内层最大对齐。偏移递推把内层当成一个普通的“大小 $s$、对齐 $a$”的字段，先对齐再放。如果内层总大小已经补齐到自己的最大对齐，外层再按内层的对齐要求摆放，内层的每个字段就仍然对齐。嵌套不会破坏规则，只会让规则多套一层。数组、结构体、结构体数组、嵌套结构体，都是“起点加偏移表”的不同组合，底层永远是字节和地址。

### 5.4 对齐表的推演

ALIGN 表有十二行，逐个看：

$n=0,a=1$，0 已经是 1 的倍数，结果 0。

$n=1,a=4$，1 不是 4 的倍数，向上到 4。

$n=3,a=4$，3 向上到 4。

$n=4,a=4$，4 已经对齐，结果 4。

$n=5,a=4$，5 向上到 8。

$n=6,a=8$，6 向上到 8。

$n=13,a=8$，13 向上到 16。

$n=262136,a=8$，262136 是 8 的倍数，结果不变。

$n=262140,a=8$，262140 除以 8 余 4，向上到 262144。

$n=262141,a=8$，262141 除以 8 余 5，向上到 262144。

$n=3,a=3$，3 不是 2 的幂，拒绝。

$n=4294967293,a=8$，加 7 后超过 32 位，拒绝。

前九行是正常对齐，后两行是非法输入。$262140$ 和 $262141$ 都补到 $262144$，这个数正好是内存大小。如果结构体末尾在这个位置，总大小 262144 还能装下；如果基地址不是 0，就会越界。对齐函数只负责把数推到倍数，不负责检查内存；内存检查在偏移表里做。

最后一行是溢出测试。`UINT32_MAX` 是 4294967295，$4294967293+7=4294967300$，超过 32 位。32 位加法会回绕成 4，掩码后还是 4，看起来像一个合法的对齐结果。程序用 64 位算，发现结果大于 `UINT32_MAX`，返回 `false`。这个例子和第四章的指针乘法、第五章的数组总长是同一个主题：先宽后窄，先算后查，别让回绕骗过边界检查。

### 5.5 失败案例

BAD 表有六个案例，每个都对应一条不变量。

零字段：字段数为 0，结构体没有内容，拒绝。

零大小字段：字段大小为 0，没有字节可访问，拒绝。

零对齐：对齐为 0，任何数都不能“是 0 的倍数”来定义对齐，拒绝。

对齐 3：不是 2 的幂，补齐公式的掩码不成立，拒绝。

九个字段：超过 `ALETHEIA_MAX_FIELDS`，字段表装不下，拒绝。

尾部越界：基地址 0x3fff8，三个八字节字段，总大小至少 24，$0x3fff8+24=0x40010$，超过 0x40000，拒绝。

六个案例的失败原因不同，返回值都是 `false`。调用者不需要区分原因，只需要知道“没构造出来”。如果程序打印 `accepted`，说明对应的检查漏了，SUMMARY 的 `reject` 会变成 `false`，最终打印 `BROKEN`。失败演示比成功演示更重要：成功只说明一条路径能走通，失败说明边界真的被挡住了。一个永远不触发的检查，和没有检查，在测试里看起来一样；只有喂给它一个非法输入，才知道它有没有工作。BAD 表的六个案例就是六次“喂非法输入”，每次只破坏一条规则，看构造函数是否在对应的位置拒绝。全拒绝，说明六条规则都被执行了；有任何一条被接受，说明那条规则漏了，或者被后面的规则意外放过。

## 六、把 AletheiaStruct 写成 C

### 6.1 规格、字段、结构体

三个结构体分别表示输入、输出和整体：

```c
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
    struct AletheiaField fields[8];
};
```

`AletheiaFieldSpec` 是构造函数的输入，只有大小和对齐，没有偏移，因为偏移是算出来的。`AletheiaField` 是输出，多了偏移。`AletheiaStruct` 把基地址、总大小、字段数和字段表放在一起，形成一个自包含的描述符。字段表是值数组，不是指针，所以描述符可以按值传递、按值复制、按值返回。

字段表最多八个，宏 `ALETHEIA_MAX_FIELDS` 定义这个上限。构造函数检查 $n\le8$，检查失败就拒绝，不会写越界。字段表的每个元素 12 字节，整个描述符 108 字节。这个大小在程序头部打印，读者可以核对。

### 6.2 对齐函数

```c
static bool aletheia_align_up(uint32_t n, uint32_t a, uint32_t *out) {
    uint64_t v;
    if (out == NULL || a == 0u || (a & (a - 1u)) != 0u) {
        return false;
    }
    v = ((uint64_t)n + (uint64_t)a - 1u) & ~((uint64_t)a - 1u);
    if (v > (uint64_t)UINT32_MAX) {
        return false;
    }
    *out = (uint32_t)v;
    return true;
}
```

三个检查：输出非空，对齐非零，对齐是 2 的幂。`(a & (a - 1u)) == 0` 是判断 2 的幂的标准写法：2 的幂的二进制只有一个 1，减一后变成低位全 1，两者按位与为 0。$a=0$ 时 $a-1$ 回绕成全 1，必须单独排除，所以前面先查 `a == 0u`。

核心一行是加 $a-1$ 再与掩码。`(uint64_t)n` 和 `(uint64_t)a` 把加法提升到 64 位，避免 $n+a-1$ 在 32 位回绕。掩码 `~((uint64_t)a - 1u)` 在 64 位里做，低位清零的范围正确。最后检查结果是否超过 `UINT32_MAX`，超过就拒绝。返回值通过 `out` 传出，成功才写。

这个函数只做对齐，不做内存检查。$n=262140,a=8$ 会返回 262144，哪怕 262144 正好是内存上界；它也不知道后面还有没有空间。内存检查是偏移表的责任，对齐函数保持单一职责。

### 6.3 偏移表

偏移表函数是这一章的核心：

```c
static bool aletheia_offset_table(AletheiaAddr base,
                                  const struct AletheiaFieldSpec *spec,
                                  uint32_t n,
                                  struct AletheiaStruct *out) {
    struct AletheiaStruct s;
    uint64_t cursor = 0;
    uint32_t max_align = 1u;
    uint32_t i;
    if (out == NULL || spec == NULL || n == 0u || n > ALETHEIA_MAX_FIELDS) {
        return false;
    }
    s.addr = base;
    s.size = 0u;
    s.field_count = n;
    for (i = 0; i < n; ++i) {
        uint32_t offset;
        uint64_t end;
        if (spec[i].size == 0u || spec[i].align == 0u) {
            return false;
        }
        if ((spec[i].align & (spec[i].align - 1u)) != 0u) {
            return false;
        }
        if (cursor > (uint64_t)UINT32_MAX) {
            return false;
        }
        if (!aletheia_align_up((uint32_t)cursor, spec[i].align, &offset)) {
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
        uint64_t total =
            (cursor + (uint64_t)max_align - 1u) & ~((uint64_t)max_align - 1u);
        if (total > (uint64_t)UINT32_MAX) {
            return false;
        }
        if ((uint64_t)base + total > (uint64_t)ALETHEIA_SIZE) {
            return false;
        }
        s.size = (uint32_t)total;
    }
    *out = s;
    return true;
}
```

`cursor` 是“前一个字段的末尾”，初始为 0。每一轮先检查当前字段的大小和对齐合法，再把 `cursor` 向上对齐，得到当前字段的偏移。`end` 是偏移加大小，用 64 位算，检查不超过 32 位。然后写入字段表，更新 `cursor`，更新最大对齐。

循环结束后，`cursor` 是最后一个字段的末尾，`max_align` 是最大对齐。总大小是把 `cursor` 向上对齐到 `max_align`，同样用 64 位算。最后检查 `base + total` 不超过 262144。这个检查用 64 位，因为 `base` 和 `total` 都可能是 32 位的大数，32 位加法会回绕。

函数先构造一个临时结构体 `s`，全部检查通过后才写 `*out`。失败时 `out` 保持原样，调用者不会拿到半成品。这个模式和前几章的构造函数一致：要么完整成功，要么完全不改输出。

`aletheia_offset_table` 产生的是规范布局：每个字段都放在“前一个末尾向上对齐”的最小位置，总大小是“末尾向上对齐到最大对齐”的最小值。规范布局的好处是唯一：同样的规格表，无论谁来算，结果都一样。规范布局不是唯一合法的布局，`aletheia_struct_ok` 允许字段之间多留空洞。可在这一章里，所有构造函数都走规范布局，验收也只打印规范布局。唯一性让输出可对照，读者不用猜“这个空洞是故意的还是算错了”。

偏移表是数据，不是编译期魔法。它可以被打印、被比较、被存进机器、被另一个程序读取。后面的总装章节会把偏移表和纸带标注放在一起，让一台机器能描述自己的数据结构。宿主编译器不需要参与，`offsetof` 不需要出现，布局的每一步都能在运行时检查。这是“古法”的一部分：不把关键约定交给看不见的编译器，而是把它写成能读、能验的代码和数据。

### 6.4 有效性检查

`aletheia_struct_ok` 不重新计算偏移，而是检查已有字段表是否满足不变量：

```c
static bool aletheia_struct_ok(const struct AletheiaStruct *s) {
    uint32_t max_align = 1u;
    uint32_t i;
    if (s == NULL || s->field_count == 0u ||
        s->field_count > ALETHEIA_MAX_FIELDS || s->size == 0u) {
        return false;
    }
    if ((uint64_t)s->addr + (uint64_t)s->size > (uint64_t)ALETHEIA_SIZE) {
        return false;
    }
    for (i = 0; i < s->field_count; ++i) {
        struct AletheiaField f = s->fields[i];
        if (f.size == 0u || f.align == 0u ||
            (f.align & (f.align - 1u)) != 0u) {
            return false;
        }
        if ((f.offset & (f.align - 1u)) != 0u) {
            return false;
        }
        if (i == 0u && f.offset != 0u) {
            return false;
        }
        if ((uint64_t)f.offset + (uint64_t)f.size > (uint64_t)s->size) {
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
```

检查顺序是：字段数和总大小，整体内存边界，逐字段的大小、对齐、偏移对齐，第一个字段偏移为 0，字段区间在总大小内，字段不重叠，最后检查总大小是最大对齐的倍数。每一步都用 64 位算加法，避免偏移加大小回绕。

`f.offset & (f.align - 1u)` 是判断偏移是否对齐的位运算，等价于 $f.\text{offset}\bmod f.\text{align}=0$。`s->size & (max_align - 1u)` 同理，判断总大小是否是最大对齐的倍数。这两个检查只在 `align` 是 2 的幂时有意义，前面已经检查过，所以可以直接用掩码。

`ok` 接受字段之间有额外空洞的布局。它不要求偏移等于递推的最小值，只要求不重叠、对齐、在总大小内。这种“宽松的有效性”让描述符可以被手工构造，也允许将来在字段之间插入保留区。构造函数产生规范布局，`ok` 检查安全布局，两个层次分开。

### 6.5 字段指针与结构体数组

字段指针复用第四章的 `AletheiaPtr`：

```c
static bool aletheia_field_ptr(const struct AletheiaStruct *s, uint32_t i,
                               struct AletheiaPtr *out) {
    struct AletheiaField f;
    if (s == NULL || out == NULL || !aletheia_struct_ok(s) ||
        i >= s->field_count) {
        return false;
    }
    f = s->fields[i];
    return aletheia_ptr_make(s->addr + f.offset, f.size, out);
}
```

先检查描述符有效、下标在范围内，再用基地址加偏移造一个指针，元素大小是字段大小。`s->addr + f.offset` 不会溢出，因为 `ok` 已经保证 $addr+size\le262144$，而 $offset+size\le size$。`aletheia_ptr_make` 会再检查一次，两层检查各自成立。

结构体数组的元素地址由 `aletheia_struct_at` 算：

```c
static bool aletheia_struct_at(const struct AletheiaStruct *s, uint32_t i,
                               AletheiaAddr *out) {
    uint64_t addr;
    if (s == NULL || out == NULL || !aletheia_struct_ok(s)) {
        return false;
    }
    addr = (uint64_t)s->addr + (uint64_t)i * (uint64_t)s->size;
    if (addr + (uint64_t)s->size > (uint64_t)ALETHEIA_SIZE) {
        return false;
    }
    *out = (AletheiaAddr)addr;
    return true;
}
```

第 $i$ 个元素的地址是 $base+i\cdot size$，用 64 位算，检查整个元素落在内存里。这个函数不知道数组有多少个元素，只检查内存边界；调用者要自己限制 $i$ 的范围，或者另写一个带长度的数组描述符。验收里只用 $i=0$ 和 $i=1$，两个元素都在 0x00440 到 0x00470 之间，安全。

ARRAY STRIDE 表检查每个元素的每个字段是否对齐。程序算 $(base+offset)\bmod align$，为 0 打印 `ok`，否则打印 `bad`。这个检查不依赖 `ok`，而是独立算一遍，相当于用手算的公式再验一次。

## 七、完整程序

完整程序把字节层、指针层和结构体层叠在一起。字节层提供读写，指针层提供“地址加大小”，结构体层提供偏移表和字段访问。程序先打印机器信息，再跑六组检查：对齐表、自然布局、重排布局、字段指针、结构体数组、失败案例，最后打印汇总。

编译命令：

```bash
cc -std=c99 -O2 -Wall -Wextra -pedantic -Werror aletheia_ch06.c -o aletheia_ch06
```

完整代码：

```c
/* aletheia_ch06.c */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define ALETHEIA_SIZE ((uint32_t)256 * 1024)
#define ALETHEIA_ADDR_MAX ALETHEIA_SIZE
#define ALETHEIA_MAX_FIELDS 8u

typedef uint8_t AletheiaByte;
typedef uint32_t AletheiaAddr;

struct AletheiaPtr {
    AletheiaAddr addr;
    uint32_t elem_size;
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
    printf("[0x%05x,0x%05x) size=%u",
           (unsigned)p.addr,
           (unsigned)(p.addr + p.elem_size),
           (unsigned)p.elem_size);
}

/* 向上对齐：把 n 推到 a 的整数倍。a 必须是 2 的幂。 */
static bool aletheia_align_up(uint32_t n, uint32_t a, uint32_t *out) {
    uint64_t v;
    if (out == NULL || a == 0u || (a & (a - 1u)) != 0u) {
        return false;
    }
    v = ((uint64_t)n + (uint64_t)a - 1u) & ~((uint64_t)a - 1u);
    if (v > (uint64_t)UINT32_MAX) {
        return false;
    }
    *out = (uint32_t)v;
    return true;
}

/* 偏移递推：先补齐，再放字段，最后把整个结构体补齐到最大对齐。 */
static bool aletheia_offset_table(AletheiaAddr base,
                                  const struct AletheiaFieldSpec *spec,
                                  uint32_t n,
                                  struct AletheiaStruct *out) {
    struct AletheiaStruct s;
    uint64_t cursor = 0;
    uint32_t max_align = 1u;
    uint32_t i;
    if (out == NULL || spec == NULL || n == 0u || n > ALETHEIA_MAX_FIELDS) {
        return false;
    }
    s.addr = base;
    s.size = 0u;
    s.field_count = n;
    for (i = 0; i < n; ++i) {
        uint32_t offset;
        uint64_t end;
        if (spec[i].size == 0u || spec[i].align == 0u) {
            return false;
        }
        if ((spec[i].align & (spec[i].align - 1u)) != 0u) {
            return false;
        }
        if (cursor > (uint64_t)UINT32_MAX) {
            return false;
        }
        if (!aletheia_align_up((uint32_t)cursor, spec[i].align, &offset)) {
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
        uint64_t total =
            (cursor + (uint64_t)max_align - 1u) & ~((uint64_t)max_align - 1u);
        if (total > (uint64_t)UINT32_MAX) {
            return false;
        }
        if ((uint64_t)base + total > (uint64_t)ALETHEIA_SIZE) {
            return false;
        }
        s.size = (uint32_t)total;
    }
    *out = s;
    return true;
}

static bool aletheia_struct_ok(const struct AletheiaStruct *s) {
    uint32_t max_align = 1u;
    uint32_t i;
    if (s == NULL || s->field_count == 0u ||
        s->field_count > ALETHEIA_MAX_FIELDS || s->size == 0u) {
        return false;
    }
    if ((uint64_t)s->addr + (uint64_t)s->size > (uint64_t)ALETHEIA_SIZE) {
        return false;
    }
    for (i = 0; i < s->field_count; ++i) {
        struct AletheiaField f = s->fields[i];
        if (f.size == 0u || f.align == 0u ||
            (f.align & (f.align - 1u)) != 0u) {
            return false;
        }
        if ((f.offset & (f.align - 1u)) != 0u) {
            return false;
        }
        if (i == 0u && f.offset != 0u) {
            return false;
        }
        if ((uint64_t)f.offset + (uint64_t)f.size > (uint64_t)s->size) {
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

static bool aletheia_field_ptr(const struct AletheiaStruct *s, uint32_t i,
                               struct AletheiaPtr *out) {
    struct AletheiaField f;
    if (s == NULL || out == NULL || !aletheia_struct_ok(s) ||
        i >= s->field_count) {
        return false;
    }
    f = s->fields[i];
    return aletheia_ptr_make(s->addr + f.offset, f.size, out);
}

static bool aletheia_struct_at(const struct AletheiaStruct *s, uint32_t i,
                               AletheiaAddr *out) {
    uint64_t addr;
    if (s == NULL || out == NULL || !aletheia_struct_ok(s)) {
        return false;
    }
    addr = (uint64_t)s->addr + (uint64_t)i * (uint64_t)s->size;
    if (addr + (uint64_t)s->size > (uint64_t)ALETHEIA_SIZE) {
        return false;
    }
    *out = (AletheiaAddr)addr;
    return true;
}

static bool aletheia_check_align(void) {
    static const struct {
        uint32_t n;
        uint32_t a;
        bool want;
        uint32_t result;
    } cases[] = {
        { 0u, 1u, true, 0u },
        { 1u, 4u, true, 4u },
        { 3u, 4u, true, 4u },
        { 4u, 4u, true, 4u },
        { 5u, 4u, true, 8u },
        { 6u, 8u, true, 8u },
        { 13u, 8u, true, 16u },
        { 262136u, 8u, true, 262136u },
        { 262140u, 8u, true, 262144u },
        { 262141u, 8u, true, 262144u },
        { 3u, 3u, false, 0u },
        { 4294967293u, 8u, false, 0u }
    };
    size_t i;
    bool ok = true;
    printf("ALIGN\n");
    printf("N           A  RESULT\n");
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        uint32_t got = 0u;
        bool up = aletheia_align_up(cases[i].n, cases[i].a, &got);
        printf("%-10u %2u  ", (unsigned)cases[i].n, (unsigned)cases[i].a);
        if (up) {
            printf("%u\n", (unsigned)got);
        } else {
            printf("invalid\n");
        }
        if (up != cases[i].want || (up && got != cases[i].result)) {
            ok = false;
        }
    }
    return ok;
}

static bool aletheia_print_layout(const struct AletheiaStruct *s) {
    uint64_t cursor = 0;
    uint64_t payload = 0;
    uint64_t padding = 0;
    uint32_t max_align = 1u;
    uint32_t i;
    bool ok = true;
    for (i = 0; i < s->field_count; ++i) {
        if (s->fields[i].align > max_align) {
            max_align = s->fields[i].align;
        }
    }
    printf("base=0x%05x size=%u align=%u\n", (unsigned)s->addr,
           (unsigned)s->size, (unsigned)max_align);
    printf("I OFFSET SIZE ALIGN SPAN              PAD\n");
    for (i = 0; i < s->field_count; ++i) {
        struct AletheiaField f = s->fields[i];
        uint64_t pad = (uint64_t)f.offset - cursor;
        payload += f.size;
        padding += pad;
        printf("%u %6u %4u %5u [0x%05x,0x%05x) %3u\n", (unsigned)i,
               (unsigned)f.offset, (unsigned)f.size, (unsigned)f.align,
               (unsigned)(s->addr + f.offset),
               (unsigned)(s->addr + f.offset + f.size), (unsigned)pad);
        if (pad > 0u && f.offset == 0u) {
            ok = false;
        }
        cursor = (uint64_t)f.offset + (uint64_t)f.size;
    }
    {
        uint64_t tail = (uint64_t)s->size - cursor;
        printf("PAYLOAD %u PADDING %u TAIL %u ALIGN %u\n",
               (unsigned)payload, (unsigned)padding, (unsigned)tail,
               (unsigned)max_align);
        padding += tail;
        if (payload + padding != s->size) {
            ok = false;
        }
        if ((s->size & (max_align - 1u)) != 0u) {
            ok = false;
        }
    }
    if (!aletheia_struct_ok(s)) {
        ok = false;
    }
    return ok;
}

static bool aletheia_check_naive(void) {
    static const struct AletheiaFieldSpec spec[] = {
        { 1u, 1u }, { 4u, 4u }, { 1u, 1u }, { 8u, 8u }
    };
    struct AletheiaStruct s;
    bool made = aletheia_offset_table(0x00400u, spec,
                                      (uint32_t)(sizeof(spec) / sizeof(spec[0])),
                                      &s);
    bool ok = made;
    printf("LAYOUT NAIVE\n");
    if (!made) {
        printf("bad layout\n");
        return false;
    }
    ok = aletheia_print_layout(&s) && ok;
    if (s.fields[0].offset != 0u || s.fields[1].offset != 4u ||
        s.fields[2].offset != 8u || s.fields[3].offset != 16u ||
        s.size != 24u) {
        ok = false;
    }
    return ok;
}

static bool aletheia_check_packed(void) {
    static const struct AletheiaFieldSpec spec[] = {
        { 8u, 8u }, { 4u, 4u }, { 1u, 1u }, { 1u, 1u }
    };
    struct AletheiaStruct s;
    bool made = aletheia_offset_table(0x00420u, spec,
                                      (uint32_t)(sizeof(spec) / sizeof(spec[0])),
                                      &s);
    bool ok = made;
    printf("LAYOUT PACKED\n");
    if (!made) {
        printf("bad layout\n");
        return false;
    }
    ok = aletheia_print_layout(&s) && ok;
    if (s.fields[0].offset != 0u || s.fields[1].offset != 8u ||
        s.fields[2].offset != 12u || s.fields[3].offset != 13u ||
        s.size != 16u) {
        ok = false;
    }
    return ok;
}

static bool aletheia_check_fields(void) {
    static const struct AletheiaFieldSpec spec[] = {
        { 1u, 1u }, { 4u, 4u }, { 1u, 1u }, { 8u, 8u }
    };
    static const AletheiaByte fills[] = { 0x11u, 0x22u, 0x33u, 0x44u };
    struct AletheiaStruct s;
    uint32_t i;
    bool ok = aletheia_offset_table(0x00400u, spec,
                                    (uint32_t)(sizeof(spec) / sizeof(spec[0])),
                                    &s);
    printf("FIELDS\n");
    printf("I  PTR               FILL\n");
    if (!ok) {
        printf("bad layout\n");
        return false;
    }
    for (i = 0; i < s.field_count; ++i) {
        struct AletheiaPtr p;
        uint32_t k;
        if (!aletheia_field_ptr(&s, i, &p)) {
            ok = false;
            continue;
        }
        printf("%u  ", (unsigned)i);
        aletheia_print_ptr(p);
        printf(" 0x%02x\n", (unsigned)fills[i]);
        for (k = 0; k < p.elem_size; ++k) {
            struct AletheiaPtr q;
            if (!aletheia_ptr_make(p.addr + k, 1u, &q) ||
                !aletheia_ptr_write_u8(q, fills[i])) {
                ok = false;
            }
        }
        for (k = 0; k < p.elem_size; ++k) {
            struct AletheiaPtr q;
            AletheiaByte v = 0u;
            if (!aletheia_ptr_make(p.addr + k, 1u, &q) ||
                !aletheia_ptr_read_u8(q, &v) || v != fills[i]) {
                ok = false;
            }
        }
    }
    return ok;
}

static bool aletheia_check_array(void) {
    static const struct AletheiaFieldSpec spec[] = {
        { 1u, 1u }, { 4u, 4u }, { 1u, 1u }, { 8u, 8u }
    };
    struct AletheiaStruct s;
    uint32_t i;
    bool ok = aletheia_offset_table(0x00440u, spec,
                                    (uint32_t)(sizeof(spec) / sizeof(spec[0])),
                                    &s);
    printf("ARRAY STRIDE\n");
    if (!ok) {
        printf("bad layout\n");
        return false;
    }
    printf("base=0x00440 size=%u\n", (unsigned)s.size);
    printf("I  ADDR      F0 F1 F2 F3\n");
    for (i = 0; i < 2u; ++i) {
        AletheiaAddr base = 0u;
        uint32_t j;
        if (!aletheia_struct_at(&s, i, &base)) {
            printf("%u  invalid\n", (unsigned)i);
            ok = false;
            continue;
        }
        printf("%u  0x%05x  ", (unsigned)i, (unsigned)base);
        for (j = 0; j < s.field_count; ++j) {
            bool aligned =
                ((base + s.fields[j].offset) & (s.fields[j].align - 1u)) == 0u;
            printf("%s", aligned ? "ok" : "bad");
            if (!aligned) {
                ok = false;
            }
            if (j + 1u < s.field_count) {
                printf(" ");
            }
        }
        printf("\n");
    }
    return ok;
}

static bool aletheia_check_bad(void) {
    static const struct AletheiaFieldSpec ok_spec[] = {
        { 1u, 1u }, { 4u, 4u }
    };
    static const struct AletheiaFieldSpec zero_size[] = { { 0u, 1u } };
    static const struct AletheiaFieldSpec zero_align[] = { { 1u, 0u } };
    static const struct AletheiaFieldSpec bad_align[] = { { 1u, 3u } };
    static const struct AletheiaFieldSpec many[] = {
        { 1u, 1u }, { 1u, 1u }, { 1u, 1u }, { 1u, 1u }, { 1u, 1u },
        { 1u, 1u }, { 1u, 1u }, { 1u, 1u }, { 1u, 1u }
    };
    static const struct AletheiaFieldSpec big[] = {
        { 8u, 8u }, { 8u, 8u }, { 8u, 8u }
    };
    struct AletheiaStruct s;
    bool ok = true;
    printf("BAD\n");
    {
        bool made = aletheia_offset_table(0x00400u, ok_spec, 0u, &s);
        printf("zero fields : %s\n", made ? "accepted" : "rejected");
        if (made) ok = false;
    }
    {
        bool made = aletheia_offset_table(0x00400u, zero_size, 1u, &s);
        printf("zero size   : %s\n", made ? "accepted" : "rejected");
        if (made) ok = false;
    }
    {
        bool made = aletheia_offset_table(0x00400u, zero_align, 1u, &s);
        printf("zero align  : %s\n", made ? "accepted" : "rejected");
        if (made) ok = false;
    }
    {
        bool made = aletheia_offset_table(0x00400u, bad_align, 1u, &s);
        printf("align 3     : %s\n", made ? "accepted" : "rejected");
        if (made) ok = false;
    }
    {
        bool made = aletheia_offset_table(0x00400u, many, 9u, &s);
        printf("too many    : %s\n", made ? "accepted" : "rejected");
        if (made) ok = false;
    }
    {
        bool made = aletheia_offset_table(0x3fff8u, big, 3u, &s);
        printf("tail over   : %s\n", made ? "accepted" : "rejected");
        if (made) ok = false;
    }
    return ok;
}

int main(void) {
    bool align_ok;
    bool naive_ok;
    bool packed_ok;
    bool fields_ok;
    bool array_ok;
    bool bad_ok;

    printf("ALETHEIA STRUCT\n");
    printf("SIZE        : %u bytes\n", (unsigned)ALETHEIA_SIZE);
    printf("ADDR RANGE  : 0x00000..0x3ffff\n");
    printf("FIELD BYTES : %lu\n", (unsigned long)sizeof(struct AletheiaField));
    printf("STRUCT BYTES: %lu\n", (unsigned long)sizeof(struct AletheiaStruct));
    printf("\n");

    align_ok = aletheia_check_align();
    printf("\n");
    naive_ok = aletheia_check_naive();
    printf("\n");
    packed_ok = aletheia_check_packed();
    printf("\n");
    fields_ok = aletheia_check_fields();
    printf("\n");
    array_ok = aletheia_check_array();
    printf("\n");
    bad_ok = aletheia_check_bad();
    printf("\n");

    printf("SUMMARY\n");
    printf("align  : %s\n", align_ok ? "true" : "false");
    printf("naive  : %s\n", naive_ok ? "true" : "false");
    printf("packed : %s\n", packed_ok ? "true" : "false");
    printf("fields : %s\n", fields_ok ? "true" : "false");
    printf("stride : %s\n", array_ok ? "true" : "false");
    printf("reject : %s\n", bad_ok ? "true" : "false");
    if (align_ok && naive_ok && packed_ok && fields_ok && array_ok && bad_ok) {
        printf("ALETHEIA STRUCT OK\n");
        return 0;
    }
    printf("ALETHEIA STRUCT BROKEN\n");
    return 1;
}
```

程序大约五百五十行。它没有 `malloc`，没有宿主结构体布局依赖，没有 `offsetof`。所有偏移都是自己算的，所有字段访问都经过 `AletheiaPtr`，所有读写都经过字节层。编译用 `-std=c99 -O2 -Wall -Wextra -pedantic -Werror`，没有警告。

## 八、真实输出与验收

在本地编译运行，得到以下输出：

```text
ALETHEIA STRUCT
SIZE        : 262144 bytes
ADDR RANGE  : 0x00000..0x3ffff
FIELD BYTES : 12
STRUCT BYTES: 108

ALIGN
N           A  RESULT
0           1  0
1           4  4
3           4  4
4           4  4
5           4  8
6           8  8
13          8  16
262136      8  262136
262140      8  262144
262141      8  262144
3           3  invalid
4294967293  8  invalid

LAYOUT NAIVE
base=0x00400 size=24 align=8
I OFFSET SIZE ALIGN SPAN              PAD
0      0    1     1 [0x00400,0x00401)   0
1      4    4     4 [0x00404,0x00408)   3
2      8    1     1 [0x00408,0x00409)   0
3     16    8     8 [0x00410,0x00418)   7
PAYLOAD 14 PADDING 10 TAIL 0 ALIGN 8

LAYOUT PACKED
base=0x00420 size=16 align=8
I OFFSET SIZE ALIGN SPAN              PAD
0      0    8     8 [0x00420,0x00428)   0
1      8    4     4 [0x00428,0x0042c)   0
2     12    1     1 [0x0042c,0x0042d)   0
3     13    1     1 [0x0042d,0x0042e)   0
PAYLOAD 14 PADDING 0 TAIL 2 ALIGN 8

FIELDS
I  PTR               FILL
0  [0x00400,0x00401) size=1 0x11
1  [0x00404,0x00408) size=4 0x22
2  [0x00408,0x00409) size=1 0x33
3  [0x00410,0x00418) size=8 0x44

ARRAY STRIDE
base=0x00440 size=24
I  ADDR      F0 F1 F2 F3
0  0x00440  ok ok ok ok
1  0x00458  ok ok ok ok

BAD
zero fields : rejected
zero size   : rejected
zero align  : rejected
align 3     : rejected
too many    : rejected
tail over   : rejected

SUMMARY
align  : true
naive  : true
packed : true
fields : true
stride : true
reject : true
ALETHEIA STRUCT OK
```

逐段看。头部打印机器大小、地址范围、字段结构体大小和结构体描述符大小。`AletheiaField` 是 12 字节，偏移、大小、对齐各 4 字节。`AletheiaStruct` 是 108 字节，基地址、总大小、字段数各 4 字节，字段表 $8\times12=96$ 字节。两个大小都和手算一致。

ALIGN 段打印十二个对齐案例。前九个是正常值，`262136` 保持原样，`262140` 和 `262141` 都补到 `262144`。第十行 `3 3` 被拒绝，因为 3 不是 2 的幂。第十二行 `4294967293 8` 也被拒绝，因为加 7 后超过 32 位。这一段验证了公式、位运算和溢出检查。

LAYOUT NAIVE 段打印自然顺序的偏移表。四个字段的偏移是 0、4、8、16，大小是 1、4、1、8，对齐是 1、4、1、8。空洞出现在 `count` 前 3 字节、`stamp` 前 7 字节。payload 14，padding 10，tail 0，总大小 24，最大对齐 8。每一行的 PAD 列都是手算的，`PAYLOAD + PADDING = 24`。

LAYOUT PACKED 段打印重排后的偏移表。偏移是 0、8、12、13，payload 还是 14，字段间空洞为 0，尾部空洞 2，总大小 16。同样四个字段，布局更紧。`TAIL 2` 是 `[0x0042e,0x00430)` 两个字节，用来把总大小补到 8 的倍数。

FIELDS 段打印每个字段的指针和填充值。`flag` 的指针是 `[0x00400,0x00401)`，`count` 是 `[0x00404,0x00408)`，`code` 是 `[0x00408,0x00409)`，`stamp` 是 `[0x00410,0x00418)`。程序把每个字段的每个字节填成同一个模式，再逐字节读回。这一步不解释多字节值的含义，只验证字段指针覆盖的字节范围正确，读写都落在范围内。

ARRAY STRIDE 段检查两个结构体元素的字段对齐。第 0 个元素在 0x00440，第 1 个在 0x00458，步长 24。四个字段在两个元素里都是 `ok`。这个 `ok` 是独立算的 $(base+offset)\bmod align$，不是从 `ok` 函数抄来的。如果总大小没有补齐到 8 的倍数，第 1 个元素的行会出现 `bad`。

故意改坏程序，输出会给出不同的失败信号。把总大小从 24 改成 14，LAYOUT NAIVE 的 `size` 会变成 14，ARRAY STRIDE 第 1 行的 `stamp` 列会变成 `bad`，因为 $0x0044e+16=0x0045e$ 不是 8 的倍数。把对齐函数里的掩码换成取模加法，对齐 3 的输入可能被接受，ALIGN 表最后几行会变。把偏移递推里的“对齐到当前字段”改成“直接累加大小”，自然顺序的偏移会变成 0、1、5、6，FIELDS 的区间和 ARRAY STRIDE 的对齐都会出错。把 `aletheia_struct_ok` 的不重叠检查删掉，手工构造一个重叠描述符会被接受，BAD 表虽然测不到，但有效性检查的证明就少了一条。四个改动各自只动一小块，验收都能从输出里看出来，因为每一组检查都直接打印可观察的值。

BAD 段打印六个失败案例，全部 `rejected`。零字段、零大小、零对齐、非 2 的幂对齐、字段太多、尾部越界，六种非法状态都被构造函数挡住。`SUMMARY` 里 `reject : true`，说明这一类全部符合预期。

验收标准有六条：

1. 对齐函数对九个正常输入给出正确结果，对非 2 的幂和溢出输入拒绝。
2. 自然顺序的偏移是 0、4、8、16，总大小 24，payload 14，padding 10。
3. 重排后的偏移是 0、8、12、13，总大小 16，payload 14，padding 2。
4. 四个字段的指针区间和大小正确，逐字节填充和读回一致。
5. 两个结构体元素的每个字段都对齐。
6. 六个非法构造案例全部被拒绝。

六条全部为真，程序打印 `ALETHEIA STRUCT OK` 并返回 0。任何一条失败，打印 `BROKEN` 并返回 1。输出是纯字符，最宽一行 41 列，远低于 80 列。重复运行输出完全一致，没有随机数、时间戳或宿主地址。

输出格式也刻意保持简单。所有数字用 `%u` 或 `%05x` 打印，不用浮点，不用千位分隔符，不受区域设置影响。字段没有名字，只有编号和偏移，所以表格宽度不会因为名字长短变化。最宽一行 41 列，是在 `[0x00404,0x00408)` 这种区间打印上。如果以后给字段加名字，宽度会增加，超过 80 列就要拆行或者缩短列名。这一章选择编号而不是名字，一是因为机器里的字段表不存字符串，二是因为编号列宽固定，输出更容易对照。名字留给注释和正文，偏移和区间留给程序。

这个程序也在 ASan 和 UBSan 下跑过。所有地址都经过 `AletheiaPtr` 和字节层检查，没有越界读写；所有加法、乘法和对齐都用 64 位防回绕，没有有符号溢出。两个消毒器都没有报错，输出和普通编译一致。

## 九、交给下一章

这一章定义了 `AletheiaStruct`，一个由基地址、总大小、字段数和字段表组成的布局描述符。它提供构造、有效性检查、字段指针和结构体数组元素地址。`aletheia_align_up` 负责向上对齐，`aletheia_offset_table` 负责偏移递推和总大小补齐，`aletheia_struct_ok` 负责检查五条不变量。

交给下一章的接口是：

```c
struct AletheiaField {
    uint32_t offset;
    uint32_t size;
    uint32_t align;
};

struct AletheiaStruct {
    AletheiaAddr addr;
    uint32_t size;
    uint32_t field_count;
    struct AletheiaField fields[8];
};
```

以及 `aletheia_align_up`、`aletheia_offset_table`、`aletheia_struct_ok`、`aletheia_field_ptr`、`aletheia_struct_at`。下一章如果需要“一段带字段的连续内存”，可以直接构造 `AletheiaStruct`，按字段名或字段下标访问。如果需要“一组等距的结构体”，用 `AletheiaStruct` 的 `size` 做步长，用 `aletheia_struct_at` 算元素地址。

下一章是字符串。字符串和结构体有相似之处：都是一段连续内存，都需要长度或终止符来确定边界。区别在于，结构体的边界由偏移表给出，字符串的边界由一个特殊的终止字节 `0` 给出。字符本身是字节，一个汉字在 UTF-8 里占三个字节，一个英文字母占一个字节。字符串的长度有两种：字节数和字符数，两者不一定相等。下一章会把这两种长度分开，写 `aletheia_strlen`，再做原地反转。

字符串还会用到这一章的字段指针：一个字符串描述符可能包含起始地址、字节长度、容量这些字段，正好可以放进 `AletheiaStruct`。不过字符串的字段很少，下一章会用更简单的结构体，直接把地址和长度放在一起。结构体偏移的教训会保留：字段有大小，有对齐，有空洞，访问要按偏移算，不能按名字猜地址。

这一章从等距走向不等距，从乘法走向查表，从无空洞走向有空洞。下一章会从“有长度”走向“有终止符”，从结构体字段走向字节序列。先把这张偏移表收好，它是后面所有复合数据的基础。
