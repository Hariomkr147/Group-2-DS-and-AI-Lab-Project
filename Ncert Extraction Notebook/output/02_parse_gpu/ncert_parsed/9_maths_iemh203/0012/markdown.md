Consider gcd(99, 2). This will reduce successively to gcd(97, 2), gcd(95, 2), gcd(93, 2), … , gcd(5, 2), gcd(3, 2), gcd(2, 1), gcd(1, 1), and gcd(1, 0) eventually giving us the answer 1. In general, if we start with an odd number 2k + 1, gcd(2k + 1, 2) will require about k reductions before we get the answer 1. This means the number of steps is proportional to the value we start with, rather than the number of digits used to write down the value.

## 11.3.4 Āryabhaṭa’s Division Algorithm

In Indian treatises like Āryabhaṭa’s Āryabhaṭīya (499 CE), we see the “long division” method for finding GCD using Indian place value numerals. It makes an efficient use of repeated “division by remainder” in place of repeated subtraction. For example, when one starts with 99 and subtracts 2 repeatedly, what remains, once one cannot subtract 2 anymore, is the remainder when 99 is divided by 2.

Hence, to improve the performance of Euclid’s algorithm, we can change the reduction step: instead of reducing gcd(m, n) to gcd(n, m – n), we reduce it to gcd(n, m mod n), where m mod n stands for the remainder when m is divided by n. For example, 17 mod 5 is 2 and 33 mod 7 is 5.

We saw earlier that a divisor d ‘tiles’ both m and n if and only if it ‘tiles’ both n and m – n. In a similar way, we can argue that d ‘tiles’ m and n if and only if it tiles m and m mod n. This justifies reducing gcd(m, n) to gcd(n, m mod n).

Here is the modified algorithm. Notice that the only change is in the third statement. The stopping condition is the same as before.

```txt
1. If m < n, reverse the numbers and compute gcd(n,m)
2. If n = 0, report the answer as m
3. Otherwise, reduce the problem to computing gcd(n, m mod n)
```

Consider the earlier example gcd(99, 2) that took a long time to converge. Here is what happens when we execute the improved algorithm.

• Step 3 asks us to reduce the problem to computing gcd(2, 1).

• Step 3 asks us to reduce the problem to computing gcd(1, 0).

Since n = 0, Step 2 tells us the answer is 1.

In other words, we needed only two reduction steps to get to the final answer. Check that this would happen for any similar problem of the form gcd(2k + 1, 2).