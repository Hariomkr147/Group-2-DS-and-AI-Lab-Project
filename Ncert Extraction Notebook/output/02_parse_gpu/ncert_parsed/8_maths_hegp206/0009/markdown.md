![](images/page_8_image_0.jpg)

Let us approach this problem systematically. There are six ways to place three digits:

We can fill the first box with 2, 3 or 5.

• For each of these choices, we have 2 ways of filling the remaining 2 digits.

• The six options are $2 3 \times 5 , 2 5 \times 3 , 3 2 \times 5 , 3 5 \times 2 , 5 2 \times 3 , 5 3 \times 2 .$

How do we find the largest product among these six options?

We can group them in pairs where the multiplier is the same.

• 35 × 2 and 53 × 2

• 25 × 3 and 52 × 3

• 23 × 5 and 32 × 5

In each pair, the one with the larger multiplicand generates the larger product, so we can reduce the comparison to these three expressions.

$5 3 \times 2$

$5 2 \times 3$

$3 2 \times 5$

It is clear that $5 2 \times 3$ is bigger than 53 × 2, so we only need to compare 52 × 3 and 32 × 5. Let us expand these.

• 32 × 5 = (3 × 10 × 5) + (2 × 5)

• 52 × 3 = (5 × 10 × 3) + (2 × 3)

The first terms in both expressions are the same. The second term shows that 32 × 5 is larger, and hence the largest of the six possible products we can form with 2, 3 and 5.

？ In this case, we used the largest digit as the multiplier. The other two digits were arranged in decreasing order to form the multiplicand. Will this always be the case? Let us find out using algebra.

Suppose p, q, and r are the three digits such that $p < q < r .$

As before, we have six possible products, which we group by the multiplier:

$q r \times p , \underline { r } q \times p$

$pr \times q,rp \times q$

$p q \times r , q p \times r$

In each pair, the multiplicand with the larger tens digit forms the larger product. So we have three products to compare:

$r q \times p$

$r p \times q$

$q p \times r$