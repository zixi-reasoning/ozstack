# 变量是区间

> 第二章。零件：`AletheiaSpan`。
>
> 一个字节有了位置，还要有长度。变量不是一个点，是一段从起点到终点的连续字节。

## 一、一个字节不知道自己的长度

上一章结束时，我们手里有四样东西：一个字节，一个地址，一次读，一次写。我们把 0x41 写到 0x00008，再读回来；把 0xff 写到 0x0000c，再加一，看它回到 0。终端打印出来的每一行都对得上。

那是一台很小的机器，小到只认识颗粒和位置。它不知道变量，不知道类型，也不知道一个东西从哪里开始、到哪里结束。它只会说：这个地址上有一个字节。

现在我要问一个第一章回答不了的问题：0x00008 号地址上住着的那个字节，属于一个多大的东西？

它可能是一个一字节的字符变量。它也可能是一个四字节整数的第一个字节。它还可能是一个八字节结构体的一个角。你只给我一个地址和一个字节，我没有办法判断。字节本身不携带长度，地址本身也不携带长度。位置只回答从哪里开始，不回答到哪里结束。

第一章的 `peek` 只能读一个字节。要读四个字节，你得调用四次 `peek`，再决定这四次的结果怎么拼成一个数。拼法是第八章的事。今天先解决更前面的问题：你凭什么知道要读四次，而不是两次或者八次？答案不在字节里，在变量的边界里。边界先于解释，长度先于数值。

这不是一个小问题。没有长度，你就不知道一个变量到哪里为止，不知道下一个变量从哪里开始，不知道一次读写会不会踩到别人的地。第一章的边界只守到 256 KiB 的边上；这一章要守到每一个变量的边上。

我先做一个思想实验。看这一段字节：

```text
0x00100  11 11 11 11 22 22 33 44
```

这八个字节是同一块地。现在给它画三种边界。

第一种，八个一字节的变量：`[0x00100,0x00101)`、`[0x00101,0x00102)`，一直到 `[0x00107,0x00108)`。

第二种，两个四字节的变量：`[0x00100,0x00104)` 和 `[0x00104,0x00108)`。

第三种，一个八字节的变量：`[0x00100,0x00108)`。

三种画法，字节一个都没变。变的只是边界。哪一种对？在没有画出边界之前，三种都对，三种也都不完整。边界不是字节自带的，是人画上去的；变量就是一条画好的边界。

所以这一章要做的，不是造一个新机器，也不是发明一个新类型。这一章只做一件事：把“一条边界”变成一个可以传递、可以检查、可以打印的值。第一章给了我们 `AletheiaByte` 和 `AletheiaAddr`，这一章给它们配一个长度，名字叫 `AletheiaSpan`。

## 二、名字不是地址

在 C 源码里，变量是有名字的。你可以写：

```c
uint32_t x;
uint16_t y;
uint8_t z;
```

然后你写 `x = 1;`，编译器知道 `x` 在哪里，知道它占几个字节，知道怎么把 1 放进去。你写 `y = 2;`，编译器也知道。

可是程序跑起来以后，机器看不见 `x`、`y`、`z` 这三个名字。名字在编译之后就没了。机器手里只有地址和长度：某一段地是四个字节，另一段地是两个字节，再一段是一个字节。名字是给人和编译器看的，不是给机器看的。

这句话要说得再准一点。变量在机器里剩下两样东西：一段区间，和区间里的字节。名字是第三样，它活在源码里，活在调试器里，活在符号表里，但它不活在内存里。你把程序烧进一块没有符号表的板子，变量还在，名字没了。

这就是为什么我把这一章的零件叫 `AletheiaSpan`，不叫 `AletheiaVar`。span 是机器能检查的那一半：起点、长度、区间。variable 还要多两样东西：名字，和生命期。名字今天我们用一个表记下来，只是为了打印；生命期要等到栈那一章。今天先把机器能检查的那一半做对。

我们可以把这件事写成三个层次：

- 区间（span）：一段地址，记作 $[a,a+s)$，$a$ 是起点，$s$ 是长度。
- 对象（object）：这段地址里实际放着的 $s$ 个字节。
- 变量（variable）：一个名字，在一段生命期里，绑定到某个对象上。

这三个层次不要混。区间是一个位置描述，它没有值；对象有值，值是字节；变量有名字，名字只在源码里有效。你以后写 `sizeof(x)`，拿到的是 $x$ 这个对象的区间长度；你写 `&x`，拿到的是区间的起点；你写 `x`，拿到的是对象的字节，再按类型解释。三件事，三个动作。

这个名字借自英文的 span，意思是“跨度”。它不是 C++ 的 `std::span`，也不是某个库的类型；这里只是一个很朴素的记录：起点和长度。名字不重要，两个字段才重要。你以后看到别的语言把区间叫 slice、range、view，先看它是不是也记着起点和长度，再看它有没有额外的所有权和生命周期规则。名字会变，两个数不会变。

调试器里的名字，也是这么来的。你在调试器里看到 `x = 4`，不是因为内存里有一个叫 `x` 的格子，而是因为调试信息告诉调试器：名字 `x` 对应从某个地址开始、长度为 4 的区间，请把那段字节按 `uint32_t` 解释。名字是调试信息，地址和长度是内存里的事实。你把调试信息删掉，内存一点没变，名字全没了。发布版程序不带你写的变量名，不是编译器小气，是名字本来就不住在内存里。

用一点记号。设名字的集合是 $\mathrm{Name}$，区间的集合是 $\mathrm{Span}$。一个环境是一个部分函数：

$$
\rho:\mathrm{Name}\rightharpoonup\mathrm{Span}
$$

$\rho(x)=[a_x,a_x+s_x)$ 的意思是，名字 $x$ 绑定到从 $a_x$ 开始、长度为 $s_x$ 的区间。部分函数的意思是，不是每个名字都有绑定：名字可能还没声明，可能已经出了作用域，可能拼错了。这和第一章的内存映射 $\mathcal{M}:A\rightharpoonup\mathbb{B}$ 是同一种写法。不是所有地址都有字节，也不是所有名字都有区间。

环境住在哪里？住在编译器里，住在调试器里，也可以住在我们自己的表里。表里每一行是 `{名字, 区间}`。名字是字符串，区间是两个整数。表本身占内存，但它占的是宿主程序的内存，不是 Aletheia 那块 256 KiB 的地。这个区别今天要记清楚：描述一块地的记录，不必住在那块地里。

## 三、区间 [a, a+s)

定义要写得干净。

设 $a$ 是起点，$s$ 是长度，$s>0$。一个长度为 $s$、起点为 $a$ 的区间记作：

$$
[a,a+s)=\{a,a+1,\ldots,a+s-1\}
$$

左边的方括号表示包含起点，右边的圆括号表示不包含终点。

拿变量表里的 `x` 举例：`x` 是 `[0x00100,0x00104)`。它包含 0x00100、0x00101、0x00102、0x00103 四个字节；不包含 0x00104。0x00104 是 `y` 的起点。如果 `x` 的区间写成闭区间 `[0x00100,0x00104]`，它就会和 `y` 共用一个字节，变量表当场就不成立了。半开区间不是记账习惯，它是让相邻变量刚好首尾相接、又不重叠的那条线。这个区间里有 $s$ 个整数，长度是：

$$
|[a,a+s)|=s=(a+s)-a
$$

区间里的第 $i$ 个字节，地址是：

$$
\operatorname{addr}(i)=a+i,\quad 0\le i<s
$$

注意 $i$ 的范围是 $0\le i<s$，不是 $0\le i\le s$。$i=s$ 时，地址是 $a+s$，那是终点的界碑，不是区间里的字节。这和第一章的地址上界是同一个习惯：合法地址是 $0$ 到 $N-1$，$N$ 是上界，不在集合里；对象的终点 $a+s$ 也是上界，不在对象里。

为什么用半开区间，不用闭区间 $[a,a+s]$？

第一，长度可以直接减。半开区间的长度是终点减起点，不用加一。闭区间的长度是终点减起点加一，每算一次都要记得那个加一。第一章已经说过，让机器和人记住一个没有意义的常数，是要付代价的。

第二，相邻的区间不重叠。$[a,a+s)$ 和 $[a+s,a+s+t)$ 在边界上碰头，但它们不共享任何字节。边界不是字节，是一道线。如果用闭区间，$a+s$ 这个字节同时属于左边和右边，拼接的时候要么去重，要么允许重叠，两种都很麻烦。

第三，空区间是自然的。$[a,a)$ 是空集，长度是 0。我们不把长度为 0 的区间当成变量，因为变量至少要占一个字节；但在做区间运算、求交集、写循环的时候，空区间会自然出现。让它有一个干净的表示，比给它开一个特例要好。

半开区间不是 C 发明的。1982 年，迪杰斯特拉写过一篇很短的笔记，编号 EWD831，题目叫《为什么编号应该从零开始》。他在里面比较了四种表示区间的写法，结论是：下界闭、上界开，也就是 $[a,b)$，在长度、切片、空区间和相邻区间这几件事上最不容易出错。四十多年过去，C 的数组、Python 的切片、Go 的切片，走的都是这条线。我们这台小机器也走这条线。

现在说长度从哪里来。C 里有一个运算符叫 `sizeof`：

$$
\operatorname{sizeof}(T)=s_T
$$

$T$ 是一个类型，$s_T$ 是这个类型的一个对象占多少字节。`sizeof` 不是函数，是运算符；对定长类型，它在编译时求值，不产生运行时调用。它的单位是字节。按 C 的定义，`sizeof(char)` 恒等于 1，其他类型的大小都是这个单位的倍数。

`sizeof` 返回的类型是 `size_t`，一个无符号整数类型，专门用来表示大小和下标。它不是地址。地址是位置，大小是数量；两者都是无符号整数，但含义不同。第一章的 `AletheiaAddr` 是 32 位，因为我们把机器的地址宽度钉死在 32 位；`size_t` 的宽度跟着平台走，64 位机器上通常是 64 位。宽度不同不是问题，但本书的规矩是：进入机器的量必须定宽。所以 `AletheiaSpan` 的长度用 `uint32_t`，和地址同宽，装得下 262144，也不随宿主变化。`size_t` 只留在宿主代码的循环下标里。

在这台机器上，我们只用定宽整数。`uint8_t` 是 1 字节，`uint16_t` 是 2 字节，`uint32_t` 是 4 字节。不要把 `int` 当成 4 字节：C 只保证 `int` 至少 16 位，不保证它是 32 位。定宽类型把这件事钉死，换一台机器，长度不变。

`sizeof` 还可以作用在表达式上。`sizeof x` 和 `sizeof(x)` 是同一个意思，都是问 `x` 这个对象的类型占多少字节。注意，`sizeof` 不会真的去读 `x` 的值；它只看类型。这一点很重要，因为你可以对一个未初始化的变量写 `sizeof`，不会读到垃圾。`sizeof` 问的是“这个类型有多大”，不是“这个变量里现在是什么”。

数组会让 `sizeof` 看起来有点奇怪。声明 `uint32_t a[4];`，`sizeof(a)` 是 16，不是 4，也不是指针的 8。因为 `a` 是一个数组对象，它的类型是“四个 `uint32_t` 的数组”，整个数组占 16 字节。等数组退化成指针，`sizeof` 才会变成指针的大小。这个区别，第五章会专门讲。今天只要记住：`sizeof` 量的是对象本身，不是指向对象的指针。

## 四、区间的法律

有了区间，就要有法律。第一条法律：这个区间是不是落在这块地里。

设地址空间是 $[0,N)$，$N=262144$。一个区间 $[a,a+s)$ 合法，当且仅当：

$$
\operatorname{valid}([a,a+s))\iff a<N\ \land\ s>0\ \land\ s\le N-a
$$

三个条件，缺一不可。$a<N$ 保证起点在地里；$s>0$ 保证它不是空区间；$s\le N-a$ 保证终点不越过上界。第三条不写成 $a+s\le N$，原因在代码里：$a+s$ 可能溢出。数学上 $a+s$ 是一个整数，不会溢出；机器上的地址是 32 位无符号整数，$a+s$ 超过 $2^{32}-1$ 就会回绕。先检查 $a<N$，再算 $N-a$，这个减法不会溢出，因为 $N-a>0$。然后拿 $s$ 和它比。顺序不能反。

举一个具体的例子。假设地址是 32 位，$a=0xFFFFFFF0$，$s=0x20$。如果写 $a+s\le N$，右边的加法会回绕成 $0x10$，$0x10\le N$ 成立，一个明显越界的区间会被放进来。用 $s\le N-a$，先算 $N-a$，因为 $a$ 已经大于 $N$，第一项就不成立，后面的减法根本不用做。溢出安全不是一句口号，它是把加法换成减法的直接结果。

下面两种写法只差一个符号，行为差得很远：

```c
/* 错的写法：两个 32 位无符号数相加可能回绕 */
if (addr + size <= ALETHEIA_ADDR_MAX) { /* ... */ }

/* 对的写法：先减，后比 */
if (aletheia_addr_ok(addr) && size <= ALETHEIA_ADDR_MAX - addr) {
    /* ... */
}
```

第一行里，如果 `addr` 和 `size` 都是 32 位无符号数，加法会在 32 位里回绕。有人会说，把 `size` 换成 `size_t`，在 64 位宿主上加法就被提升到 64 位，可能碰巧不回绕。这是把正确性寄托在宿主字宽上：换一台 32 位宿主，同一个 bug 就回来了。第二行不依赖提升：先确认 `addr` 是合法地址，再在 32 位无符号里做减法，差一定在 `[0,N]` 里。换一台宿主，第二行还是对的。

第二条法律：一个区间是否包含另一个区间。$[b,b+t)\subseteq[a,a+s)$ 当且仅当：

$$
[b,b+t)\subseteq[a,a+s)\iff a\le b\ \land\ b+t\le a+s
$$

用起点和长度写，不直接算终点：

$$
[b,b+t)\subseteq[a,a+s)\iff a\le b\ \land\ (b-a)\le s\ \land\ t\le s-(b-a)
$$

第一项保证内层起点不在外层左边；第二项保证内层起点没有越过外层终点；第三项保证内层的长度装得下剩余的空间。三项都可以用减法写，不用加法。先减，后比，这是这一章反复出现的写法。

举一个包含算法的边界例子。外层是 `[0x00100,0x00104)`，内层是 `[0x00105,0x00106)`。内层起点在外层右边，`delta = 5`，`delta > outer.size` 成立，返回假。如果不先比 `delta`，直接算 `outer.size - delta`，在无符号算术里会得到一个巨大的数，然后 `inner.size <= 巨大数` 成立，一个明明在外层右边的区间会被判成包含。无符号减法没有负数，只有回绕；先比后减，就是为了不让回绕发生。

第三条法律：两个区间是否重叠。两个半开区间不相交，当且仅当其中一个完全在另一个左边：

$$
[a,a+s)\cap[b,b+t)=\varnothing\iff b\ge a+s\ \lor\ a\ge b+t
$$

反过来，重叠就是：

$$
\operatorname{overlap}([a,a+s),[b,b+t))\iff a<b+t\ \land\ b<a+s
$$

注意两个都是严格小于。$a=b+t$ 表示 $a$ 的区间从 $b$ 的终点开始，两个区间相邻但不重叠；$b=a+s$ 同理。边界归右边，不归左边，这就是半开区间的规矩。

这些法律有一个共同点：它们只回答“在不在 256 KiB 里”和“两段地有没有交叉”，不回答“这段地是不是你的”。一个区间完全可能合法，也完全可能不和任何已登记的变量重叠，但它仍然不属于任何一个变量。合法性是宇宙的法律，归属是对象的法律。两本账，要分开记。

这就是这一章最重要的一句话：`aletheia_span_ok` 说这段地在 256 KiB 里，没说过这块地归你。你拿一个合法的区间去写，机器不会拦你；它只知道地址合法。要知道这块地归谁，你得自己维护一张表。表里没有的东西，机器不认识。

现在我们有了三条法律，再加上两个动作。第一个动作是填充：把一个区间的每个字节都写成一个值。

$$
\operatorname{fill}([a,a+s),v)\Rightarrow
\mathcal{M}'=\mathcal{M}[(a+i)\mapsto v]_{i=0}^{s-1}
$$

第二个动作是复制：把一个区间的字节逐个搬到另一个区间。

$$
\operatorname{copy}([d,d+s),[a,a+s))\Rightarrow
\mathcal{M}'=\mathcal{M}[(d+i)\mapsto\mathcal{M}(a+i)]_{i=0}^{s-1}
$$

复制有两个前提：两个区间一样长，而且不重叠。一样长是为了不丢字节也不多写；不重叠是为了避免方向问题。如果目标在源的前面，从前向后拷是对的；如果目标在源的后面，从前向后拷会把还没读的字节先覆盖掉。这种重叠拷贝需要一个更聪明的方向判断，今天不做。今天只把前提写清楚，不满足就拒绝。

## 五、为什么变量要带长度

现在回答一个更硬的问题：为什么变量不能只是一个起点？

一个起点只能告诉你从哪里开始。你要读它，不知道读几个字节；你要写它，不知道写到哪里停；你要检查边界，不知道边界在哪里。起点是一张没有写终点的车票，能上车，不知道在哪下车。写程序最怕这种票：它看起来能用，出了事查不到。

那为什么不用终点？只存终点，长度可以用终点减起点算出来。听起来可以，但有三个问题。

第一，终点是算出来的，起点和长度是独立的事实。你每做一次循环，都要算一次减法；每做一次比较，都要小心终点是不是越过了上界。算得越多，错的机会越多。

第二，终点是一个边界，不是一块地。你很容易把终点当成区间里的最后一个字节，然后写出少读一个字节或者多读一个字节的循环。半开区间的终点不在区间里，这件事靠注释记不住，要靠数据结构和接口来记。

第三，终点可能溢出。起点加长度在数学上总是有定义，在 32 位无符号算术里可能回绕。把起点和长度分开存，先检查起点和长度，再算终点，顺序是清楚的。把终点存起来，你反而要反过来推长度，还要处理终点小于起点的情况。

所以区间用起点加长度表示。终点是导出量，只在合法区间上计算：

$$
\operatorname{end}([a,a+s))=a+s
$$

而且这个导出量只在这条法律通过以后才算：

$$
\operatorname{valid}([a,a+s))\Rightarrow \operatorname{end}([a,a+s))\in(a,N]
$$

为什么终点落在 $(a,N]$？因为 $s>0$，所以 $a+s>a$；因为 $s\le N-a$，所以 $a+s\le N$。终点可以等于 $N$，但那时它已经出了地址空间，不是一块地。它是界碑。

再说类型。C 的编译器知道每个变量的类型，知道类型的大小，所以它可以在编译时把 `x` 换成“地址加偏移”，把 `sizeof(x)` 换成一个常数。这是编译器的本事。可是我们的机器是自己造的，机器运行时没有类型信息，只有字节。你给它一段区间，它不会问“这是 `uint32_t` 还是 `uint16_t`”，它只会数长度。类型是编译时的承诺，长度是运行时的检查。两者不能互相替代。

这也是为什么这一章的零件不叫“类型”。类型当然重要，但类型活在源码里；机器需要的是一个能带着走的长度。等你写分配器的时候，你会看到同样的事情：分配器不知道你要放整数还是放字符串，它只知道你要多少字节。长度是机器世界的通用语言。

那指针呢？指针不也是“地址加类型”吗？是，但指针还带着算术规则和解引用规则，那些是第四章的事。今天我们把指针拆开，只留下最硬的那一半：地址和长度。等第四章再把类型和算术装回去。先有区间，后有指针；顺序反了，你会以为指针天生就会加减。

最后一个问题：为什么变量之间不能重叠？

如果两个变量共享一个字节，你写其中一个，另一个就变了。机器不知道你本来想写哪一个，它只知道你写了一个地址。名字是你脑子里的东西，机器没有。变量重叠，等于把两个名字挂在同一块地上，然后指望写一个不影响另一个。这个指望没有依据。

以后会有合法的共享：两个指针指向同一个对象，两个视图解释同一段字节。但那是显式的共享，有类型，有规则，有地方可以查。今天先把默认规则立住：活着的变量，两两不重叠。重叠不是技巧，是错误。

你可能会问，既然归属这么重要，为什么不把名字或者主人塞进 `AletheiaSpan` 里？因为机器不认识名字。你塞进去一个字符串，机器还是要用字节来存它，还是要用地址来找到它，最后又回到同样的问题。主人是谁，是一个外部账本的问题，不是一段区间自身的问题。第二卷会把块头写进内存，那时候主人信息会变成内存里的几个字节，但那是分配器的设计，不是区间的定义。今天让区间保持笨，只记起点和长度；账本另外记。

还要分清区间和生命期。区间回答从哪里到哪里；生命期回答什么时候可以读写。一个变量死了，它的区间还在，那块地可以被下一个变量复用。区间不知道生命期，生命期也不改变区间。今天只守区间；生命期等栈那一章再守。

区间和生命期的分离，是后面很多设计的基础。分配器释放一块内存，释放的是生命期，不是区间；区间还在，那块地可以被下一次分配复用。栈帧退栈，退的是一整段区间，里面所有变量的生命期一起结束。你今天只要记住：看到 `[a,a+s)`，先问它在不在地址空间里，再问它属于谁、什么时候有效。三个问题，三层检查。

区间是这一卷的第一件正式工具。它不解决所有问题，但它把“多大”从一个形容词变成了一个数。以后你听到“这块缓冲区够不够”，第一反应不该是“应该够”，而是“起点在哪，长度多少，终点有没有越过 N”。

## 六、把区间写成 C

现在把法律写成代码。先写结构体：

```c
struct AletheiaSpan {
    AletheiaAddr addr;
    uint32_t size;
};
```

两个字段，一个起点，一个长度。没有类型，没有名字，没有所有权。它只描述一段地。

然后写构造函数和合法性检查：

```c
static struct AletheiaSpan aletheia_span_new(AletheiaAddr addr, uint32_t size) {
    struct AletheiaSpan s;
    s.addr = addr;
    s.size = size;
    return s;
}

static bool aletheia_span_ok(struct AletheiaSpan s) {
    if (s.size == 0) {
        return false;
    }
    if (!aletheia_addr_ok(s.addr)) {
        return false;
    }
    return s.size <= ALETHEIA_ADDR_MAX - s.addr;
}
```

`aletheia_span_new` 不检查合法性，它只是把两个数装进去。检查是 `aletheia_span_ok` 的事。为什么不在构造函数里检查？因为构造和验证是两件事。你需要构造一个非法的区间来做测试，需要构造一个越界的区间来演示失败，需要把用户的输入原样装进去再报告错误。构造函数一检查，这些事都做不了。让构造保持笨，让检查保持严，是接口设计的一条小规矩。

`aletheia_span_new` 按值返回结构体。结构体只有两个字段，按值返回不会复制一大块内存；编译器很可能把它放进两个寄存器。按值返回还有一个好处：调用者拿到的是一个独立的值，不需要担心谁拥有它、谁负责释放它。区间是值，不是资源。资源才需要所有权，值不需要。

`aletheia_span_ok` 按顺序做三件事。长度是不是 0；起点是不是在地址空间里；长度是不是超过剩余空间。第三条写的是 `s.size <= ALETHEIA_ADDR_MAX - s.addr`，不是 `s.addr + s.size <= ALETHEIA_ADDR_MAX`。前者不会溢出，后者可能回绕。`s.addr` 是 `uint32_t`，`ALETHEIA_ADDR_MAX` 也是；两者相减得到一个 `uint32_t`，因为已经先检查过 `s.addr < ALETHEIA_ADDR_MAX`，差是正的，不会回绕。`s.size` 也是 `uint32_t`，所以这次比较全程在 32 位无符号里完成，不需要任何收窄。

`struct AletheiaSpan` 里的长度用 `uint32_t`，不用 `size_t`。两者都能表示 262144，但 `size_t` 的宽度跟着宿主走，写进机器就不确定了；`uint32_t` 是定宽的，和 `AletheiaAddr` 同宽。地址和长度仍然是两个含义，用两个字段名区分：`addr` 是位置，`size` 是数量。接口不假设宿主字宽，所有进入机器的量都在 32 位里算。

接着写终点：

```c
static bool aletheia_span_end(struct AletheiaSpan s, AletheiaAddr *out) {
    if (!aletheia_span_ok(s) || out == NULL) {
        return false;
    }
    *out = (AletheiaAddr)(s.addr + s.size);
    return true;
}
```

终点不是随时能算的。只有合法的区间才有终点。函数先验证，再计算，最后通过输出参数把结果送回去。为什么不写一个直接返回 `a+s` 的函数？因为对非法区间，`a+s` 不是一个终点，只是一个碰巧算出来的数。给它一个名字，会让人以为它有意义。返回 `bool`，把“能不能算”和“算出来是多少”分开，这和第一章读字节时值和状态分开是同一个道理。

然后是包含和重叠：

```c
static bool aletheia_span_contains(struct AletheiaSpan outer,
                                   struct AletheiaSpan inner) {
    uint32_t delta;
    if (!aletheia_span_ok(outer) || !aletheia_span_ok(inner)) {
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

static bool aletheia_span_overlap(struct AletheiaSpan a,
                                  struct AletheiaSpan b) {
    AletheiaAddr a_end;
    AletheiaAddr b_end;
    if (!aletheia_span_end(a, &a_end) || !aletheia_span_end(b, &b_end)) {
        return false;
    }
    return a.addr < b_end && b.addr < a_end;
}
```

`contains` 先看内层起点是不是在外层左边，再看内层起点离外层起点有多远，最后看内层的长度装不装得下剩下的空间。`delta > outer.size` 这一句不能省：如果内层起点已经越过外层终点，`outer.size - delta` 会变成一个巨大的无符号数，后面的比较就会误判为真。先比 `delta`，再减，顺序不能反。

`overlap` 先算两个终点，再用两个严格小于判断。`a.addr < b_end` 的意思是 $a$ 的起点在 $b$ 的终点左边；`b.addr < a_end` 的意思是 $b$ 的起点在 $a$ 的终点左边。两个都成立，两个区间才交叉。只有一边成立，是包含；两边都不成立，是分离。非法区间没有终点，`overlap` 对它返回假；所以在查重叠之前，表里的区间必须先合法。

最后是填充和复制：

```c
static bool aletheia_span_fill(struct AletheiaSpan s, AletheiaByte value) {
    size_t i;
    if (!aletheia_span_ok(s)) {
        return false;
    }
    for (i = 0; i < s.size; ++i) {
        if (!aletheia_poke_u8((AletheiaAddr)(s.addr + i), value)) {
            return false;
        }
    }
    return true;
}

static bool aletheia_span_copy(struct AletheiaSpan dst,
                               struct AletheiaSpan src) {
    size_t i;
    if (!aletheia_span_ok(dst) || !aletheia_span_ok(src)) {
        return false;
    }
    if (dst.size != src.size) {
        return false;
    }
    if (aletheia_span_overlap(dst, src)) {
        return false;
    }
    for (i = 0; i < src.size; ++i) {
        AletheiaByte b = 0;
        if (!aletheia_peek_u8((AletheiaAddr)(src.addr + i), &b)) {
            return false;
        }
        if (!aletheia_poke_u8((AletheiaAddr)(dst.addr + i), b)) {
            return false;
        }
    }
    return true;
}
```

这两个函数都没有绕开第一章的字节层。它们做的，只是把 `poke` 和 `peek` 放进一个循环，循环的次数就是区间的长度。区间不是新的魔法，它是字节循环的一个名字。你看到 `fill`，应该能想到第一章的位运算和边界检查；你看到 `copy`，应该能想到两次读写和一次重叠判断。

复制先检查长度相等，再检查不重叠，最后逐字节搬运。如果中途某一次读写失败，函数立刻返回假。这时目标区间可能已经被写了一半。这是一个部分写入的问题，今天不处理。接口只说“返回假表示没有完成”，没有承诺“失败时目标不变”。要承诺原子性，需要额外的日志或者临时缓冲区，那是后面的事。今天先把规则说清楚，不假装它比实际更强。

现在把名字和区间连起来：

```c
struct AletheiaVar {
    const char *name;
    struct AletheiaSpan span;
};
```

`name` 是宿主 C 的字符串，只用于打印。机器本身不需要它。这张表是第一章没有的东西：第一台调试器。它把“人认识的名字”和“机器认识的区间”并排放着。你打印这张表，就是在看编译器脑子里的一小部分。

所有这些函数都标了 `static`。和第一章一样，`static` 在这里的意思是“只在这个文件里可见”。组件先把门关起来，等接口稳定了再决定开哪扇门。现在只有一个文件，标不标都能编过；标上以后，编译器知道这些名字不会被别的文件引用，可以做更激进的优化，也可以在你写错名字时立刻报错。

这张表住在宿主 C 的结构体里，不住在 256 KiB 数组里。它描述那块地，不占那块地。这个区别很重要，因为第二卷的块头会搬进地里。到那时，描述者会住进被描述的世界，分配器要在自己管理的字节里记录自己管了哪些字节。那会比今天复杂，但也会更有意思。

## 七、在纸上走一遍

拿一个最小的例子，手工走一遍。

我们在 0x00100 放四个变量：`x` 占四字节，`y` 占两字节，`z` 占一字节，`flag` 占一字节。它们的区间是：

- `x`：`[0x00100,0x00104)`，长度 4。
- `y`：`[0x00104,0x00106)`，长度 2。
- `z`：`[0x00106,0x00107)`，长度 1。
- `flag`：`[0x00107,0x00108)`，长度 1。

四个变量合起来，正好铺满 `[0x00100,0x00108)`，长度是 8。它们的长度加起来是 $4+2+1+1=8$，没有空洞，也没有重叠。这是一个很强的性质：这段地是一块完整的帧，四个变量是它的一个划分。

先看合法性。`x` 的起点 0x00100 小于 0x40000，长度 4 小于等于 0x40000 减 0x00100，合法。`y`、`z`、`flag` 同理。整块帧也合法。

再看包含。帧 `[0x00100,0x00108)` 包含 `x`：0x00100 不小于 0x00100，`x` 的终点 0x00104 不大于帧的终点 0x00108，成立。帧包含 `y`，也成立。`x` 包含 `y` 不成立：`y` 的起点 0x00104 在 `x` 里面，但 `y` 的终点 0x00106 在 `x` 的终点 0x00104 右边。用代码里的算法：`delta = 0x00104 - 0x00100 = 4`，`delta > x.size`？4 > 4 不成立；`y.size <= x.size - delta`？2 <= 0 不成立。返回假。这里正好是边界：`y` 从 `x` 的终点开始，所以它不在 `x` 里面。半开区间再次说话。

再看重叠。`x` 和 `y`：`x` 的终点是 0x00104，`y` 的起点也是 0x00104。`x.addr < y_end` 是 0x00100 < 0x00106，真；`y.addr < x_end` 是 0x00104 < 0x00104，假。一个真一个假，不重叠。`x` 和 `z`、`x` 和 `flag` 也都不重叠。四个变量两两不重叠，这是它们能同时活着的前提。

把同一段帧按三种单位重新分组，得到的区间是：

- 一字节一组：`[0x00100,0x00101)` 到 `[0x00107,0x00108)`，共八组。
- 四字节一组：`[0x00100,0x00104)` 和 `[0x00104,0x00108)`，共两组。
- 八字节一组：`[0x00100,0x00108)`，共一组。

三组描述的边界不同，覆盖的字节完全相同。0x00100 上的那个 0x11，在第一种分组里是第一个变量的全部，在第二种分组里是第一个变量的四分之一，在第三种分组里是唯一变量的八分之一。字节没有变，问题问的是你把它当成多大的对象。

然后填字节。`x` 填 0x11，`y` 填 0x22，`z` 填 0x33，`flag` 填 0x44。帧里变成：

```text
[0x00100, 0x00108) 11 11 11 11 22 22 33 44
```

这不是四个值，这是八个字节。`x` 的四个 0x11，`y` 的两个 0x22，`z` 的一个 0x33，`flag` 的一个 0x44。你现在还看不出这些字节表示什么数，因为解释是第三章的事。今天只看位置和长度。

复制 `x` 到 0x00200。源区间是 `[0x00100,0x00104)`，目标区间是 `[0x00200,0x00204)`。两个都合法，长度都是 4，不重叠。循环四次，目标变成 `11 11 11 11`。复制 `y` 到 0x00204，目标变成 `22 22`。

现在做几个失败实验。

第一个，复制 `x` 到 0x00102。目标是 `[0x00102,0x00106)`，和源 `[0x00100,0x00104)` 在 0x00102 和 0x00103 上重叠。函数发现重叠，返回假，一个字节都不搬。这不是小气，这是保护：如果它硬搬，源的前两个字节会被目标覆盖，后两个字节读到的是已经被改过的值，结果既不是原来的 `x`，也不是你想要的拷贝。

第二个，复制 `x` 到一个三字节的目标 `[0x00300,0x00303)`。长度不等，返回假。你可能会想，那就拷前三个字节吧。不行。复制一个对象，要么整个拷，要么不拷；拷一部分，得到的是一个既不是源也不是目标的东西。长度相等这个前提，是为了让结果有明确的含义。

第三个，写一个合法的、但越过了变量边界的区间。`too_long = [0x00100,0x00105)`，长度是 5。它合法吗？起点 0x00100 小于 0x40000，5 小于等于 0x40000 减 0x00100，合法。它和 `y` 重叠吗？`y` 是 `[0x00104,0x00106)`，`too_long` 的终点是 0x00105，0x00104 < 0x00105，确实重叠。现在拿 `too_long` 去填 0xaa。函数只检查合法性，不检查归属，所以它照填。填完以后，`y` 的第一个字节从 0x22 变成 0xaa，`y` 变成 `aa 22`。

这就是这一章最重要的一次失败。`span_ok` 说这段地合法，它没有说这段地归你。合法性只守 256 KiB 的边，不守变量的边。要守变量的边，你得有那张表，得在写之前查表。机器自己没有表，表是你维护的。你忘了查，机器不会替你查。

把 `y` 恢复成 `22 22`，继续。

注意这次覆写只坏了 `y` 的第一个字节，不是两个。`too_long` 是 `[0x00100,0x00105)`，它包含 0x00100、0x00101、0x00102、0x00103、0x00104 五个字节。`y` 是 `[0x00104,0x00106)`，两个字节。两个区间的交集只有 0x00104 一个字节。所以填完以后，`y` 是 `aa 22`，不是 `aa aa`。区间相交的长度，就是被改坏的字节数。这个数可以用交集算出来，也可以直接用眼睛数出来。

最后看边界。`last4 = [0x3fffc,0x40000)`，长度 4。起点合法，4 小于等于 0x40000 减 0x3fffc，也就是 4，合法。填 0xee，四个字节都写进去，最后一个字节在 0x3ffff，正是地址空间的最后一个地址。读 0x3ffff，得到 0xee。

`over4 = [0x3fffe,0x40002)`，长度 4。起点合法，但 0x40000 减 0x3fffe 等于 2，4 大于 2，不合法。`over4` 没有终点，也不能填。`empty = [0x00100,0x00100)`，长度 0，不合法。`outside = [0x40000,0x40001)`，起点已经是上界，不合法。

这些检查不是形式主义。它们把第一章的边界从“一个地址”扩展到“一段区间”。第一章守的是 $a<N$；这一章守的是 $a<N$ 且 $s\le N-a$。代码里多了一个减法，机器就多挡住了一类越界。

`last4` 的合法性和 `over4` 的非法性只差两个字节。`last4` 的起点是 0x3fffc，剩下 4 个字节，正好装下长度 4；`over4` 的起点是 0x3fffe，剩下 2 个字节，装不下长度 4。一个是刚好贴边，一个是越过两个字节。边界检查的价值，就在这两个字节上。你写 `<=` 还是 `<`，你算 `N-a` 还是 `N-a+1`，差别都落在这种地方。

## 八、把 AletheiaSpan 拼起来

现在把前面的片段拼成一个完整程序。

这个程序只做一件事：在一块 256 KiB 的静态字节区上，把同一段地按几种方式分组，建立一张变量表，做包含、重叠、复制、填充和边界检查。它不分配内存，不调用外部库，不生成任何图像。它只打印字符。

代码块第一行是建议文件名。你把它复制到一个空文件里，按这个名字保存，就可以编译。

```c
/* aletheia_ch02.c */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define ALETHEIA_SIZE ((uint32_t)256 * 1024)
#define ALETHEIA_ADDR_MAX ALETHEIA_SIZE

typedef uint8_t AletheiaByte;
typedef uint32_t AletheiaAddr;

/* 这台机器假定一个字节八位；前提不成立就不编译。 */
typedef char aletheia_check_byte[(sizeof(AletheiaByte) == 1) ? 1 : -1];
typedef char aletheia_check_u16[(sizeof(uint16_t) == 2) ? 1 : -1];
typedef char aletheia_check_u32[(sizeof(uint32_t) == 4) ? 1 : -1];

struct AletheiaSpan {
    AletheiaAddr addr;
    uint32_t size;
};

struct AletheiaVar {
    const char *name;
    struct AletheiaSpan span;
};

static AletheiaByte aletheia_mem[ALETHEIA_SIZE];

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

static struct AletheiaSpan aletheia_span_new(AletheiaAddr addr, uint32_t size) {
    struct AletheiaSpan s;
    s.addr = addr;
    s.size = size;
    return s;
}

static bool aletheia_span_ok(struct AletheiaSpan s) {
    if (s.size == 0) {
        return false;
    }
    if (!aletheia_addr_ok(s.addr)) {
        return false;
    }
    return s.size <= ALETHEIA_ADDR_MAX - s.addr;
}

static bool aletheia_span_end(struct AletheiaSpan s, AletheiaAddr *out) {
    if (!aletheia_span_ok(s) || out == NULL) {
        return false;
    }
    *out = (AletheiaAddr)(s.addr + s.size);
    return true;
}

static bool aletheia_span_contains(struct AletheiaSpan outer,
                                   struct AletheiaSpan inner) {
    uint32_t delta;
    if (!aletheia_span_ok(outer) || !aletheia_span_ok(inner)) {
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

static bool aletheia_span_overlap(struct AletheiaSpan a,
                                  struct AletheiaSpan b) {
    AletheiaAddr a_end;
    AletheiaAddr b_end;
    if (!aletheia_span_end(a, &a_end) || !aletheia_span_end(b, &b_end)) {
        return false;
    }
    return a.addr < b_end && b.addr < a_end;
}

static bool aletheia_span_fill(struct AletheiaSpan s, AletheiaByte value) {
    size_t i;
    if (!aletheia_span_ok(s)) {
        return false;
    }
    for (i = 0; i < s.size; ++i) {
        if (!aletheia_poke_u8((AletheiaAddr)(s.addr + i), value)) {
            return false;
        }
    }
    return true;
}

static bool aletheia_span_copy(struct AletheiaSpan dst,
                               struct AletheiaSpan src) {
    size_t i;
    if (!aletheia_span_ok(dst) || !aletheia_span_ok(src)) {
        return false;
    }
    if (dst.size != src.size) {
        return false;
    }
    if (aletheia_span_overlap(dst, src)) {
        return false;
    }
    for (i = 0; i < src.size; ++i) {
        AletheiaByte b = 0;
        if (!aletheia_peek_u8((AletheiaAddr)(src.addr + i), &b)) {
            return false;
        }
        if (!aletheia_poke_u8((AletheiaAddr)(dst.addr + i), b)) {
            return false;
        }
    }
    return true;
}

static void aletheia_print_span(const char *name, struct AletheiaSpan s) {
    AletheiaAddr end;
    if (!aletheia_span_end(s, &end)) {
        printf("%-5s invalid  addr=0x%05x  size=%u\n",
               name, (unsigned)s.addr, (unsigned)s.size);
        return;
    }
    printf("%-5s [0x%05x, 0x%05x)  size=%u\n",
           name, (unsigned)s.addr, (unsigned)end, (unsigned)s.size);
}

static void aletheia_print_bytes(struct AletheiaSpan s) {
    size_t i;
    AletheiaAddr end;
    if (!aletheia_span_end(s, &end)) {
        printf("invalid\n");
        return;
    }
    printf("[0x%05x, 0x%05x) ", (unsigned)s.addr, (unsigned)end);
    for (i = 0; i < s.size; ++i) {
        AletheiaByte b = 0;
        if (aletheia_peek_u8((AletheiaAddr)(s.addr + i), &b)) {
            printf("%02x ", (unsigned)b);
        }
    }
    printf("\n");
}

static void aletheia_check(const char *label, bool ok) {
    printf("%-20s: %s\n", label, ok ? "true" : "false");
}

static const struct AletheiaVar aletheia_vars[] = {
    { "x",    { 0x00100u, sizeof(uint32_t) } },
    { "y",    { 0x00104u, sizeof(uint16_t) } },
    { "z",    { 0x00106u, sizeof(uint8_t) } },
    { "flag", { 0x00107u, sizeof(uint8_t) } },
};

#define ALETHEIA_VAR_COUNT \
    (sizeof(aletheia_vars) / sizeof(aletheia_vars[0]))

static void aletheia_print_vars(void) {
    size_t i;
    printf("%-6s%-9s%-9s%4s\n", "NAME", "BEGIN", "END", "SIZE");
    for (i = 0; i < ALETHEIA_VAR_COUNT; ++i) {
        AletheiaAddr end = 0;
        if (aletheia_span_end(aletheia_vars[i].span, &end)) {
            printf("%-6s0x%05x  0x%05x  %4u\n",
                   aletheia_vars[i].name,
                   (unsigned)aletheia_vars[i].span.addr,
                   (unsigned)end,
                   (unsigned)aletheia_vars[i].span.size);
        }
    }
}

static bool aletheia_vars_contiguous(void) {
    size_t i;
    AletheiaAddr end;
    if (!aletheia_span_end(aletheia_vars[0].span, &end)) {
        return false;
    }
    for (i = 1; i < ALETHEIA_VAR_COUNT; ++i) {
        if (aletheia_vars[i].span.addr != end) {
            return false;
        }
        if (!aletheia_span_end(aletheia_vars[i].span, &end)) {
            return false;
        }
    }
    return true;
}

static bool aletheia_vars_disjoint(void) {
    size_t i;
    size_t j;
    for (i = 0; i < ALETHEIA_VAR_COUNT; ++i) {
        for (j = i + 1; j < ALETHEIA_VAR_COUNT; ++j) {
            if (aletheia_span_overlap(aletheia_vars[i].span,
                                      aletheia_vars[j].span)) {
                return false;
            }
        }
    }
    return true;
}

static void aletheia_print_grouping(const char *label, AletheiaAddr base,
                                    size_t unit) {
    size_t offset;
    printf("%s\n", label);
    for (offset = 0; offset < 8; offset += unit) {
        printf("  [0x%05x, 0x%05x)\n",
               (unsigned)(base + (AletheiaAddr)offset),
               (unsigned)(base + (AletheiaAddr)(offset + unit)));
    }
}

static void aletheia_print_overlap(void) {
    size_t i;
    size_t j;
    printf("%-5s", "");
    for (j = 0; j < ALETHEIA_VAR_COUNT; ++j) {
        printf("%-5s", aletheia_vars[j].name);
    }
    printf("\n");
    for (i = 0; i < ALETHEIA_VAR_COUNT; ++i) {
        printf("%-5s", aletheia_vars[i].name);
        for (j = 0; j < ALETHEIA_VAR_COUNT; ++j) {
            const char *mark;
            if (i == j) {
                mark = "-";
            } else if (aletheia_span_overlap(aletheia_vars[i].span,
                                             aletheia_vars[j].span)) {
                mark = "yes";
            } else {
                mark = "no";
            }
            printf("%-5s", mark);
        }
        printf("\n");
    }
}

int main(void) {
    struct AletheiaSpan frame = aletheia_span_new(0x00100u, 0x8u);
    struct AletheiaSpan x = aletheia_vars[0].span;
    struct AletheiaSpan y = aletheia_vars[1].span;
    struct AletheiaSpan z = aletheia_vars[2].span;
    struct AletheiaSpan flag = aletheia_vars[3].span;
    struct AletheiaSpan x_copy = aletheia_span_new(0x00200u, 0x4u);
    struct AletheiaSpan y_copy = aletheia_span_new(0x00204u, 0x2u);
    struct AletheiaSpan last4 = aletheia_span_new(0x3fffcu, 0x4u);
    struct AletheiaSpan over4 = aletheia_span_new(0x3fffeu, 0x4u);
    struct AletheiaSpan empty = aletheia_span_new(0x00100u, 0x0u);
    struct AletheiaSpan outside = aletheia_span_new(0x40000u, 0x1u);
    struct AletheiaSpan too_long = aletheia_span_new(0x00100u, 0x5u);
    struct AletheiaSpan short_copy = aletheia_span_new(0x00300u, 0x3u);
    AletheiaByte value = 0;

    printf("ALETHEIA SPAN\n");
    printf("SIZE       : %u bytes\n", (unsigned)ALETHEIA_SIZE);
    printf("ADDR RANGE : 0x00000..0x3ffff\n");
    printf("sizeof(u8) : %lu\n", (unsigned long)sizeof(uint8_t));
    printf("sizeof(u16): %lu\n", (unsigned long)sizeof(uint16_t));
    printf("sizeof(u32): %lu\n", (unsigned long)sizeof(uint32_t));
    printf("\n");

    printf("FRAME\n");
    aletheia_print_span("frame", frame);
    aletheia_print_vars();
    aletheia_check("vars contiguous", aletheia_vars_contiguous());
    aletheia_check("vars disjoint", aletheia_vars_disjoint());
    printf("\n");

    printf("GROUPING\n");
    aletheia_print_grouping("8 x 1", 0x00100u, 0x1u);
    aletheia_print_grouping("2 x 4", 0x00100u, 0x4u);
    aletheia_print_grouping("1 x 8", 0x00100u, 0x8u);
    printf("\n");

    (void)aletheia_span_fill(x, 0x11u);
    (void)aletheia_span_fill(y, 0x22u);
    (void)aletheia_span_fill(z, 0x33u);
    (void)aletheia_span_fill(flag, 0x44u);
    printf("BYTES\n");
    aletheia_print_bytes(frame);
    aletheia_print_span("x", x);
    aletheia_print_bytes(x);
    aletheia_print_span("y", y);
    aletheia_print_bytes(y);
    aletheia_print_span("z", z);
    aletheia_print_bytes(z);
    aletheia_print_span("flag", flag);
    aletheia_print_bytes(flag);
    printf("\n");

    printf("CONTAINS\n");
    aletheia_check("frame contains x", aletheia_span_contains(frame, x));
    aletheia_check("frame contains y", aletheia_span_contains(frame, y));
    aletheia_check("x contains y", aletheia_span_contains(x, y));
    aletheia_check("x contains x", aletheia_span_contains(x, x));
    printf("\n");

    printf("OVERLAP\n");
    aletheia_print_overlap();
    printf("\n");

    printf("COPY\n");
    aletheia_check("copy x to 0x00200",
                   aletheia_span_copy(x_copy, x));
    aletheia_check("copy y to 0x00204",
                   aletheia_span_copy(y_copy, y));
    printf("%-20s: ", "dst 0x00200");
    aletheia_print_bytes(x_copy);
    printf("%-20s: ", "dst 0x00204");
    aletheia_print_bytes(y_copy);
    aletheia_check("copy x to x+2",
                   aletheia_span_copy(aletheia_span_new(0x00102u, 0x4u), x));
    aletheia_check("copy x to 3 bytes",
                   aletheia_span_copy(short_copy, x));
    printf("\n");

    printf("BOUNDS\n");
    aletheia_print_span("last4", last4);
    aletheia_print_span("over4", over4);
    aletheia_print_span("empty", empty);
    aletheia_print_span("outside", outside);
    aletheia_check("last4 valid", aletheia_span_ok(last4));
    aletheia_check("last4 fill 0xee", aletheia_span_fill(last4, 0xeeu));
    (void)aletheia_peek_u8(0x3ffffu, &value);
    printf("%-20s: 0x%02x\n", "peek 0x3ffff", (unsigned)value);
    aletheia_check("over4 valid", aletheia_span_ok(over4));
    aletheia_check("over4 fill 0xee", aletheia_span_fill(over4, 0xeeu));
    aletheia_check("empty valid", aletheia_span_ok(empty));
    aletheia_check("outside valid", aletheia_span_ok(outside));
    printf("\n");

    printf("CLOBBER\n");
    aletheia_print_span("too_long", too_long);
    aletheia_check("too_long valid", aletheia_span_ok(too_long));
    aletheia_check("too_long overlaps y",
                   aletheia_span_overlap(too_long, y));
    (void)aletheia_span_fill(too_long, 0xaau);
    printf("%-20s: ", "y after fill");
    aletheia_print_bytes(y);
    (void)aletheia_span_fill(y, 0x22u);
    printf("%-20s: ", "y after restore");
    aletheia_print_bytes(y);

    return 0;
}
```

编译命令：

```bash
cc -std=c99 -O2 -Wall -Wextra -pedantic -o aletheia_ch02 aletheia_ch02.c
./aletheia_ch02
```

程序里有几个地方值得再看一眼。

`aletheia_check_byte`、`aletheia_check_u16`、`aletheia_check_u32` 是三个编译期检查。它们用数组长度为 1 或 -1 的写法，在 `sizeof` 不符合预期时直接让编译失败。C99 没有 `_Static_assert`，这是古法。它们不是运行时的断言，不会出现在输出里；它们是编译器的断言，编译不过，程序根本不存在。

`aletheia_print_grouping` 把同一段地按 1 字节、4 字节、8 字节三种单位切开，打印每一段的区间。这些区间只是描述，不是新的存储。它们告诉你：同一块地，边界可以画在不同地方。程序没有改变字节，只改变了看字节的方式。

`aletheia_vars` 是那张变量表。四项，每项一个名字和一个区间。`sizeof(uint32_t)` 在编译时给出 4，所以 `x` 的长度是 4；`y` 是 2；`z` 和 `flag` 是 1。起点是手写的，因为今天我们自己做编译器的活。等以后写分配器，起点会由分配器算出来。

`aletheia_vars_contiguous` 和 `aletheia_vars_disjoint` 是两个表级检查。前者检查四个变量是不是首尾相接，后者检查两两是否重叠。它们是这一章的“表不变量”：一张变量表如果既不连续又有重叠，后面的实验就没有意义。

`main` 里的每一个失败返回都被 `aletheia_check` 打印出来。你可以忽略返回值，但你不应该忽略。写失败和写成功，在调试时是两条完全不同的路。

整份程序只有一个数组、一组字节函数、一组区间函数和一张表。没有动态分配，没有文件，没有网络，没有随机数。它的行为完全由代码决定。同样的输入，跑一万次，输出一模一样。这种确定性，是后面所有实验的前提。

程序的输出分成九段，和这一章的问题对应：大小、帧、分组、字节、包含、重叠、复制、边界、覆写。每一段都只打印它要回答的那几个数，不打印无关的中间状态。这不是为了好看，是为了让失败的时候能一眼定位：如果 `vars disjoint` 变成假，问题一定在变量表；如果 `last4 fill` 变成假，问题一定在边界检查。

## 九、真实输出与验收

程序跑起来，终端打印：

```text
ALETHEIA SPAN
SIZE       : 262144 bytes
ADDR RANGE : 0x00000..0x3ffff
sizeof(u8) : 1
sizeof(u16): 2
sizeof(u32): 4

FRAME
frame [0x00100, 0x00108)  size=8
NAME  BEGIN    END      SIZE
x     0x00100  0x00104     4
y     0x00104  0x00106     2
z     0x00106  0x00107     1
flag  0x00107  0x00108     1
vars contiguous     : true
vars disjoint       : true

GROUPING
8 x 1
  [0x00100, 0x00101)
  [0x00101, 0x00102)
  [0x00102, 0x00103)
  [0x00103, 0x00104)
  [0x00104, 0x00105)
  [0x00105, 0x00106)
  [0x00106, 0x00107)
  [0x00107, 0x00108)
2 x 4
  [0x00100, 0x00104)
  [0x00104, 0x00108)
1 x 8
  [0x00100, 0x00108)

BYTES
[0x00100, 0x00108) 11 11 11 11 22 22 33 44 
x     [0x00100, 0x00104)  size=4
[0x00100, 0x00104) 11 11 11 11 
y     [0x00104, 0x00106)  size=2
[0x00104, 0x00106) 22 22 
z     [0x00106, 0x00107)  size=1
[0x00106, 0x00107) 33 
flag  [0x00107, 0x00108)  size=1
[0x00107, 0x00108) 44 

CONTAINS
frame contains x    : true
frame contains y    : true
x contains y        : false
x contains x        : true

OVERLAP
     x    y    z    flag 
x    -    no   no   no   
y    no   -    no   no   
z    no   no   -    no   
flag no   no   no   -    

COPY
copy x to 0x00200   : true
copy y to 0x00204   : true
dst 0x00200         : [0x00200, 0x00204) 11 11 11 11 
dst 0x00204         : [0x00204, 0x00206) 22 22 
copy x to x+2       : false
copy x to 3 bytes   : false

BOUNDS
last4 [0x3fffc, 0x40000)  size=4
over4 invalid  addr=0x3fffe  size=4
empty invalid  addr=0x00100  size=0
outside invalid  addr=0x40000  size=1
last4 valid         : true
last4 fill 0xee     : true
peek 0x3ffff        : 0xee
over4 valid         : false
over4 fill 0xee     : false
empty valid         : false
outside valid       : false

CLOBBER
too_long [0x00100, 0x00105)  size=5
too_long valid      : true
too_long overlaps y : true
y after fill        : [0x00104, 0x00106) aa 22 
y after restore     : [0x00104, 0x00106) 22 22 
```

第一段告诉你这块地有多大，一个定宽类型占几个字节。`sizeof(u8)` 是 1，`sizeof(u16)` 是 2，`sizeof(u32)` 是 4。这三个数不是猜的，是编译期定下的。

第二段是帧和变量表。帧从 0x00100 到 0x00108，长度 8。四个变量首尾相接，长度分别是 4、2、1、1。`vars contiguous` 和 `vars disjoint` 都是真。这两行是表级不变量，不是某一个变量的性质。

第三段是分组。同样八个字节，按 1 字节切是八段，按 4 字节切是两段，按 8 字节切是一段。区间不同，字节相同。这就是“变量是区间”的最直观证据。

第四段是字节。帧里是 `11 11 11 11 22 22 33 44`。下面四组分别打印每个变量的区间和它覆盖的字节。`x` 的区间是 `[0x00100,0x00104)`，四个 `11`；`y` 是 `[0x00104,0x00106)`，两个 `22`；`z` 是一个 `33`；`flag` 是一个 `44`。每一组字节都是帧的一段连续切片。

第五段是包含。帧包含 `x` 和 `y`；`x` 不包含 `y`；`x` 包含它自己。最后一条是自反性：一个区间当然包含自己，`delta` 是 0，长度等于剩余空间。

第六段是重叠矩阵。四个变量两两不重叠。矩阵的对角线是 `-`，因为一个变量和自己不算重叠，它和自己相等。非对角线全是 `no`。这张表是手工检查的替代品：你不需要用眼睛一行一行比，让机器比。

第七段是复制。`x` 复制到 0x00200，`y` 复制到 0x00204，都成功，目标字节和源一样。复制 `x` 到 0x00102 失败，因为重叠；复制 `x` 到三字节目标失败，因为长度不等。这两次失败都发生在搬运之前，所以目标没有被写。

第八段是边界。`last4` 合法，填充成功，0x3ffff 读出来是 0xee。`over4` 不合法，填充失败。`empty` 和 `outside` 也不合法。`last4` 的终点正好是 0x40000，也就是地址上界；它本身不在区间里，但它的前一个字节 0x3ffff 在区间里。这是半开区间在地址空间边界上的样子。

第九段是覆写。`too_long` 是合法的，但它和 `y` 重叠。填 0xaa 之后，`y` 的第一个字节变成 0xaa；恢复之后，`y` 回到 `22 22`。这一段是故意做坏的，目的是让你看见：合法性检查和归属检查是两件事。

这份输出里没有一个宿主地址。变量表里的 0x00100、0x00200、0x3fffc 都是我们自己写死的机器地址，不是宿主栈上的地址。宿主栈地址每次运行都可能变，打印出来就不能复现。我们不打印它，只打印我们自己的地址空间。这也是为什么同一份程序跑一万次，输出一模一样：它没有随机数，没有时间，没有地址随机化，没有外部输入。

验收可以写成四句话：所有合法区间的终点都能算出来；所有非法区间都被拒绝；包含和重叠的答案与纸上推的一致；复制和填充只碰区间内的字节。四条都过，组件才算立住。少一条，后面用它的人就得替你补检查。

验收不是口号，是清单。清单上的每一条，都要能在终端里看见，或者能用一条命令验证。

验收项如下：

- `sizeof(uint8_t)` 等于 1。
- `sizeof(uint16_t)` 等于 2。
- `sizeof(uint32_t)` 等于 4。
- 帧是 `[0x00100,0x00108)`，长度 8。
- 四个变量首尾相接，两两不重叠。
- `frame` 包含 `x` 和 `y`，`x` 不包含 `y`。
- `x` 复制到 0x00200 成功，字节一致。
- 重叠复制失败，长度不等复制失败。
- 0x3fffc 起四字节的区间合法，填充后 0x3ffff 是 0xee。
- 0x3fffe 起四字节的区间非法，填充失败。
- 长度为 0 的区间非法，起点等于 0x40000 的区间非法。
- `too_long` 合法但和 `y` 重叠，填充会改坏 `y`。
- 编译零警告。
- 地址检查器无报错。
- 重复运行输出一致。
- 没有 `malloc`，没有第三方库，没有图像文件。

编译时用这套命令：

```bash
cc -std=c99 -O2 -Wall -Wextra -pedantic -o aletheia_ch02 aletheia_ch02.c
```

再用地址检查器跑一遍：

```bash
cc -std=c99 -g -fsanitize=address,undefined -fno-omit-frame-pointer \
  -Wall -Wextra -pedantic -o aletheia_ch02_asan aletheia_ch02.c
./aletheia_ch02_asan
```

两次输出应该一样。地址检查器没有报错，说明这段代码没有越界，没有未定义行为，没有在边界上偷偷踩一脚。

## 十、交给下一章

这一章只做了一件事：给一个字节配上一个长度。

我们定义了区间，定义了合法、包含、不重叠，定义了填充和复制。我们把名字和区间分成两个层次，把合法性检查和归属检查分成两本账。我们在终端里看见了同一段地的三种切法，看见了一个变量被复制，看见了一次合法的越界，看见了一个字节被另一个变量踩坏。这些都很小，但它们是从“一个字节”走向“一个变量”的第一步。

下一章要拿走的接口是：

- `struct AletheiaSpan`：起点加长度。
- `aletheia_span_new`：构造一个区间，不检查。
- `aletheia_span_ok`：区间是否在地址空间里。
- `aletheia_span_end`：合法区间的终点。
- `aletheia_span_contains`：一个区间是否包含另一个。
- `aletheia_span_overlap`：两个区间是否重叠。
- `aletheia_span_fill`：把一个区间填成一个字节。
- `aletheia_span_copy`：把一个区间的字节搬到另一个同长、不重叠的区间。
- `struct AletheiaVar`：名字到区间的绑定，今天只用于打印。

下一章的问题是：一个区间里的字节，怎样表示一个负数？`x` 里有四个 0x11，它是多少？如果我把最后一位改成 1，它是变大还是变小？正数和负数在同一段字节里怎么分开？这些问题，第一章的 `AletheiaByte` 回答不了，这一章的 `AletheiaSpan` 也回答不了。它们需要第三样东西：解释。

下一章会拿 `AletheiaSpan` 去圈住一个四字节的整数，然后问：这四个字节里的哪一位是符号位？0xff 是 255 还是 -1？`AletheiaByte` 只给出 0 到 255，`AletheiaSpan` 只给出起点和长度，两个都不回答解释问题。解释要靠第三条规则：补码。到那时，地址还是地址，区间还是区间，变的只是我们读那段字节的方式。
