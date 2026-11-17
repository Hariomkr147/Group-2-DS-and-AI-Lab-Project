How do we solve it? We apply the same strategy: reduce it to gcd(x, y) where x = min(n, m – n) and y is the difference between n and m – n.

When do we stop? Suppose we compute the gcd of a number with itself, say gcd(23, 23). The answer should clearly be 23. When we reduce this we get gcd(23, 0). In other words, if we reach gcd(m, 0), the answer is m.

```txt
Euclid’s algorithm for gcd(m,n)
1. If m < n, reverse the numbers and compute gcd(n,m)
2. If n = 0, report the answer as m
```

Let us apply this algorithm to gcd(375, 825), the problem that we saw before.

Since 375 < 825, Step 1 asks us to reverse the numbers and compute gcd(825, 375).

Since 825 – 375 = 450, Step 3 asks us to reduce the problem to computing gcd(375, 450).

Since 375 < 450, Step 1 asks us to reverse the numbers and compute gcd(450, 375).

• Step 3 asks us to reduce the problem to computing gcd(375, 75).

• Step 3 asks us to reduce the problem to computing gcd(75, 300).

Since 75 < 300, Step 1 asks us to reverse the numbers and compute gcd(300, 75).

• Step 3 asks us to reduce the problem to computing gcd(75, 225).

Since 75 < 225, Step 1 asks us to reverse the numbers and compute gcd(225, 75).

• Step 3 asks us to reduce the problem to computing gcd(75, 150).

Since 75 < 150, Step 1 asks us to reverse the numbers and compute gcd(150, 75).

• Step 3 asks us to reduce the problem to computing gcd(75, 75).

• Step 3 asks us to reduce the problem to computing gcd(75, 0).

• Since n = 0, Step 2 tells us the answer is 75.

In the example above, we reduced the problem 7 times before finding the answer. Are we close to our original goal of finding an algorithm where the effort is proportional to the number of digits? Unfortunately, no.