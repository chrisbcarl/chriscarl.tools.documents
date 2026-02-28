---
header-includes: |
title: >
  Paper:
  Example
subtitle:
author: Chris Carl <chris.carl@sjsu.edu>
toc: true
# template: default
# geometry: "margin=1in"
# ieee
abstract: This is an example "paper" that demonstrates MY PERSONAL METHODOLOGY for dealing with latex in IEEE, Chicago, APA, and other formats.
keywords: Some, unordered, list of terms, will, be sorted, later
# custom
doublespaced: false
course: SJSU 2025F - XXXX 6969 - Writing Class
authors:
    - name: Chris Carl
      email: chris.carl@sjsu.edu
      institution: San Jose State University
      location: San Jose, CA, United States of America
      occupation: Masters of Science in Computer Engineering Student
---

<!--
Updates:
    2026-01-03 18:44 - paper - text actually reads like english and makes some godamn sense
    2025-12-21 16:01 - paper - started

Examples:
    python scripts/research-aid-2.py `
        scripts/examples/inputs/paper.md `
        --bibliography scripts/examples/inputs/bibliography.md `
        --template ieee `
        --output-dirpath scripts/examples/outputs/research-aid-2/ieee

    python scripts/research-aid-2.py `
        scripts/examples/inputs/paper.md `
        --bibliography scripts/examples/inputs/bibliography.md `
        --template chicago `
        --output-dirpath scripts/examples/outputs/research-aid-2/chicago

-->

# Introduction
If you'd like to make a large section, feel free to type as normal underneath it.

URL [placeholdertext.org](https://placeholdertext.org/english-placeholder-text/) that should work

"Quotations" are adjusted accordingly, normally you'd need a backtick to get the opening quote, and a `''` to get the closing.

If you want *italicized*, use the two asterisks as normal.

If you want **bolded**, use the four asterisks as normal.

If you want ***bolded and italicized***, use the six asterisks as normal.

Here's how I do basic citations with a bibliography.

Bibliography citations like basic <CitekeyArticle>, paged <Citekey-Inproceedings, 66>, section and page range <CitekeyBook, s69-99>, or chapters <CitekeyBooklet, Some Chapter Inside, 66-69>.

![image.jpg](./image.jpg)

![image online via <Aimage>](https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/LambdaPlaques.jpg/960px-LambdaPlaques.jpg)

Referencing the figure with Fig. <image.jpg> and  without correct figure prefix <960px-LambdaPlaques.jpg>.

Literals are allowed `<>` and include the `BibTex`.

Inline math is supported like $y = Ax + b$ as well as $\forall x \in X$. Or you can make explicit equations like Eq <eq-rm-ilp> and Eq <eq-profit>.

$$
%\label{eq-rm-ilp}
\begin{equation}
\begin{aligned}
&\underset{p(v_i), x_{ij1}, x_{ij2}, y_{ij}}{\max{}}  \displaystyle\sum_i^N \displaystyle\sum_i^M y_{ij}  \\
\text{s.t. } & p(v_i) > p(v_j) \ge 0, v_i \ge v_j \\
& p(v_i) + p(v_j) \ge p(v_i + v_j), \forall v_i, v_j \\
& x_{ij2} \cdot u_{ij} \le p(v_i) \le x_{ij1} \cdot u_{ij} + x_{ij2} \cdot L,  \\
& x_{ij1} + x_{ij2} = 1,  \\
& 0 \le x_{ij1}; x_{ij2} \le 1,  \\
& y_{ij} \le x_{ij1} \cdot L,  \\
& y_{ij} \le p(v_i),  \\
& y_{ij} \ge p(v_i)-L \cdot (1 - x_{ij1})  \\
& y_{ij} \ge 0  \\
\end{aligned}
\end{equation}
$$

$$
%\label{eq-profit}
\begin{equation}
\begin{aligned}
U(p_s, c)   &= R(p_s) - E(c) \\
            &= Mp_s \Psi(p_s) - N\displaystyle\sum_{c_k \in c} c_k \Phi_k(c_k)
\end{aligned}
\end{equation}
$$

$$
%\label{regular-aligned}
\begin{aligned}
\text{plz}  &= 1, 2, 3 \\
            &= 4, 5, 6 \\
\end{aligned}
$$


#### Quotes

caption: Some Quote which cites <CitekeyTechreport> and also cites <CitekeyPhdthesis>
label: quote-some
> Break weather bad file goal, use capital but polite suddenly honestly tired into open. Probably highway story laugh up tower around possible dark strongly still alive usually, music mountain classroom really too goal.
>
> Wide short direction probably will <CitekeyTechreport> watch faith information May week here empty fake water hard join house soon private safe!
>
> Citizen politely closed across bad different city like mind surface mountain famous partly. Week earth too nurse available walk market safe, deep team house alive lamp speed pillow bright rarely little north.
>
>> By - Lorem Ipsum <CitekeyPhdthesis>



#### Tables
You need to include packages `tabularx,booktabs` if you want tables. For IEEE, I offer two situations--a single column table like Table <tbl-1-col>, but double column tables like Table <tbl-2-col> are also supported. Currently any table with $\text{cols} > 3$ will be set up as a double column table else single column table.

caption: Single Column Table <CitekeyPhdthesis>
label: tbl-1-col
|Column   |Also Column  |
|---------|-------------|
|1        |a            |
|2        |b            |


Tables have a specific referencing mechanism which is entirely custom and not portable. It's simply the best I could do on a shoestring...

caption: Two Column Table <CitekeyUnpublished>
label: tbl-2-col
|Numbers  |Alphabet     |variables    |sum          |multiplicat  |
|---------|-------------|-------------|-------------|-------------|
|1        |a            |x            |+            |*            |
|2        |b            |y            |-            |/            |


#### Code
They can be cited using the code- prefix like Listing <code-python>, Listing <code-java>, Listing <code-cpp>.

```
this
    should
        be
            printed
                verbatim
```

caption: Listing with Python in it.
label: code-python
```python
def func():
    print('hello world')

# Note how if you have a really really long comment or something that definitely goes over the column limit, it will be re-indented in an attempt to save itself.
func()
```

caption: Listing with Java in it.
label: code-java
```java
public class Main {
    public static int main(String[] args) {
        System.out.println("hello world");
        return 0;
    }
}
```

caption: Listing with C++ in it.
label: code-cpp
```c++
#include <iostream>
using std::cout;
using std::endl;

int main(int argc, char** argv) {
    cout << "hello world" << endl;
    return 0;
}
```

#### Interdoc Citations
You can reference other sections in your own document. I call these "href" and the following list is all hyperlinked regardless of output format.

1. Section <introduction>
    - Section <Tables>
    - Section <Code>
2. Section <Lorem-Ipsum>
    - Section <Lots-of-Lorem>

# Lorem Ipsum
If you don't have a lot of text, things like figures and double column tables tend to occupy single pages on their own. Just be aware of this.

## Lots of Lorem
Break weather bad file goal, use capital but polite suddenly honestly tired into open. Probably highway story laugh up tower around possible dark strongly still alive usually, music mountain classroom really too goal. Wide short direction probably will watch faith information May week here empty fake water hard join house soon private safe! Citizen politely closed across bad different city like mind surface mountain famous partly. Week earth too nurse available walk market safe, deep team house alive lamp speed pillow bright rarely little north.


# Appendix


## Backup Material
Tunnel hospital then close him, laugh daughter year economy often, bright message three, student planet. Sunny fake soft warm move bank friend, evening heavy bright Thursday color salty light alive force sixteen neighbor again. Wet friend open forget black bored its rough close crowded roof a. Run slowly hospital she knife create lake bank tree, empty hard. Ocean funny not dream sleepy, bridge already how, big letter factory stone your hopeful: go easy smooth black high year?


## For your curiosity
Room angry better gently this wait high gray pillow friendly three food complex travel try clock education service. Film rainy energy, sun great an one as count truly empty often justice, run fast save lake an station camera. Difficult open hopeful transparent fairly change table cry one sun park white again hope false knowledge hospital, slightly decision. November surely learn south any factory science firmly complex farm, laugh huge. Industry home by than, exactly hot soon, quiet law safely teacher.
