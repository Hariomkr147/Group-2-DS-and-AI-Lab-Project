a rule that can predict the next few prime numbers?

**Exercise:** Consider the expression $t _ { n } = 3 n - 7 .$

(i) Find its first, second, third, 12<sup>th</sup>, 18<sup>th</sup> and $5 0 ^ { \mathrm { t h } }$ terms.

(ii) Which term of the sequence is 332?

(iii) Is 557 a term of this sequence? Why or why not?

## 8.3 Recursive Rule for a Sequence

So far, we have used a formula in terms of n for the $n ^ { t h }$ term as the explicit rule for a sequence. There is another way of writing the rule for a sequence. Consider the sequence 1, 4, 7, 10, 13, The $n ^ { t h }$ term is $t_{n} = 3n - 2$ (verify this for yourself). Note that each term is 3 more than its previous term. Thus, $t_{2} = t_{1} + 3, \quad t_{3} = t_{2} + 3$ $t _ { _ { 4 } } \: = \: t _ { _ { 3 } } + \: 3$ and so on. In general, we can say $t_{n} = t_{n - 1} + 3 \mathrm{for} - n \geq 2$ Or we can describe the sequence as $t_{1} = 1, t_{n} = t_{n - 1} + 3$ , where n can take the values 2, 3, 4, … This way of describing a sequence by relating terms to previous terms is known as a **recursive rule** or **recursive formula**. If you know earlier terms of the sequence, then you can find the next terms using the rule. Note that the earlier terms need to be known to us to use the recursive rule to find the next terms.

**Example 3:** Find the first four terms of the sequence given by the recursive rule

$u_{1}=1,u_{n}=2u_{n-1}+3\ \mathrm{for}\ n\geq2.$ . Is 133 a term of this sequence?

We successively insert the values of n as 2, 3, 4, etc., and compute the values of each term.

$$
u_{2}=2u_{1}+3=2\times 1+3=5
$$

$$
u_{3} = 2u_{2} + 3 = 2 \times 5 + 3 = 13
$$

$$
u_{4} = 2u_{3} + 3 = 2 \times 13 + 3 = 29
$$

Thus, the first four terms of the sequence are 1, 5, 13, 29. Calculating subsequent terms, we can check if 133 is a term of this sequence.

**Example 4:** Find the first four terms of the sequence given by the recursive rule $s_{1}=3,s_{n}=s_{n-1}(s_{n-1}-1)$ for $n \geq 2$

Substitute the values of n as 2, 3, 4, etc., and compute the values of each term as follows.

$$
s_{2}=s_{1}(s_{1}-1)=3\times(3-1)=3\times2=6
$$

$$
s_{3}=s_{2}(s_{2}-1)=6\times(6-1)=6\times5=30
$$

$$
s_{4}=s_{3}(s_{3}-1)=30\times(30-1)=30\times29=870
$$