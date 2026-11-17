? If (a, b, c) is a Baudhāyana triple, then (ka, kb, kc) is also a Baudhāyana triple where k is any positive integer. Is this statement true?

This statement can be shown to be true in the same way. Since (a, b, c) is a Baudhāyana triple, we have $a ^ { 2 }   + b ^ { 2 } = c ^ { 2 }$ . We need to check whether $( k a ) ^ { 2 } + ( k b ) ^ { 2 } = \tilde { ( k c ) ^ { 2 } }$

$$
(ka)^{2}=ka\times ka=k^{2} a^{2}, \text { and } (kb)^{2}=kb\times kb=k^{2} b^{2}.
$$

$$
\mathrm{S}0,(ka)^{2}+(kb)^{2}=k^{2}a^{2}+k^{2}b^{2}.
$$

Taking out the common factor, we have

$$
( k a ) ^ { 2 } + ( k b ) ^ { 2 } = k ^ { 2 }   ( a ^ { 2 } + b ^ { 2 } ) .
$$

Since $a ^ { 2 } + b ^ { 2 } = c ^ { 2 } ,$ , we have

$$
(ka)^{2}+(kb)^{2}=k^{2}\ c^{2}=(kc)^{2}.
$$

Thus, (ka, kb, kc) is a Baudhāyana triple if $( a ,   b ,   c )$ is a Baudhāyana triple. We call $( k a , k b , k c )$ a **scaled version** of $( a , b , c )$

A Baudhāyana triple that does not have any common factor greater than 1 is called a **primitive Baudhāyana triple**. So, (3, 4, 5) is primitive, whereas (9,12,15) is not.

？ Is (5, 12, 13) a primitive Baudhāyana triple? What are the other primitive Baudhāyana triples with numbers less than or equal to 20?

？ Generate 5 scaled versions of each of these primitive triples. Are these scaled versions primitive?

？ If (a, b, c) is non-primitive, and the integers have f — greater than 1 — as a common factor, then is $\left( \frac{a}{f}, \frac{b}{f}, \frac{c}{f} \right)$ a Baudhāyana triple? Check this statement for (9, 12, 15). Justify this statement.

If we can find all the primitive triples, we can find all the Baudhāyana triples.

## ？ How do we generate more primitive triples?

We know the relation between the sum of consecutive odd numbers and square numbers.

$$
\begin{array} { c } { 1 = 1 ^ { 2 } } \\ { 1 + 3 = 2 ^ { 2 } } \\ { 1 + 3 + 5 = 3 ^ { 2 } } \end{array}
$$

The sum of the first n odd numbers is $n ^ { 2 } ,$ . Let us express this algebraically.

For this, we need to know the nth odd number. What is it? The nth odd number is $2 n - 1$ . So,

$$
\underbrace{1+3+5+\cdots+(2n-3)}_{ Sum of first   (n-1)   odd numbers } + \underbrace{n^2}_{}
$$