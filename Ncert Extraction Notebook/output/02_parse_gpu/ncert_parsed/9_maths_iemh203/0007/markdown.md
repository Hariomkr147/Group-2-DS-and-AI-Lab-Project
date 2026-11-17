4. For each number x in the list of divisors-of-m

\- If x also appears in the list of divisors-of-n,add x to the list common-divisors

```txt
5. Report the rightmost element of the list common-
divisors as gcd(m,n)
```

When we execute this algorithm for gcd(375, 825) we check whether each of the divisors [1, 3, 5, 15, 25, 75, 125, 375] of 375 appears in the list of divisors [1, 3, 5, 11, 15, 25, 33, 55, 75, 165, 275, 825] of 825. We see that 1, 3, 5, 15, 25 and 75 are in the second list while 125 and 375 are not. So we compute the list of common divisors to be [1, 3, 5, 15, 25, 75]. Since 75 is the rightmost element in this list, gcd(375, 825) = 75.

## 11.3 Data Structures

When we execute an algorithm, we compute intermediate quantities, such as the list divisors-of-m and the list divisors-of-n. To keep track of these values, we use names such as divisors-of-m and divisorsof-n, respectively, so that we can refer to them later in the algorithm. As we remarked earlier, assigning names to intermediate values is important for writing down algorithms concisely.

Also, these intermediate values are typically more complicated than just simple numbers. In this case, we maintain lists of numbers and, in fact, lists that are arranged in ascending order. A **list** is an example of a **data structure**. Data structures allow us to organise information in a manner that helps make an algorithm more efficient. We will explore this idea in higher grades.

## Exercise Set 11.2

1. Suppose List 1 and List 2 are two lists of numbers in increasing order.

(i) Write an algorithm to find elements in List 1 that are not present in List 2.

(ii) Write an algorithm to find elements in List 2 that are not present in List 1.

2. Describe an algorithm to compute the least common multiple (lcm) of two numbers.