Let us keep track of a quantity called most-recent-common-divisor. We know that 1 is always a common divisor, so we can start with most-recent-common-divisor set to 1. We then scan all numbers from 2 to min(m, n).

• For each k from 2 to min(m, n), if k divides both m and n, update most-recent-common-divisor to k.

At the end of this scan,

**Example:** Let m = 6, n = 12.

– min(6, 12) = 6

Initially set most-recent-common-divisor to 1 – k = 2 divides both 6 and 12.

**Update:** most-recent-common-divisor to 2. – k = 3 divides both 6 and 12.

**Update:** most-recent-common-divisor to 3. k = 4 doesnot divide 6.

most-recent-common-divisor remains 3.

– k = 5 doesnot divide 6.

most-recent-common-divisor remains 3.

– k = 6 divides both 6 and 12.

**Update**: most-recent-common-divisor to 6.

Scan complete. gcd(6, 12) = 6

most-recent-common-divisor directly gives us the gcd.

## Exercise Set 11.3

1. How would our original algorithm change if we computed the divisors of n by examining the numbers from 1 to n in reverse order, from n down to 1?

2. What about the last algorithm described above? What happens when we look at common divisors starting from min(m, n) and work backwards to 1?

## 11.3.2 Analysing these Algorithms

We started with a very basic algorithm. Since this was derived directly from the definition of gcd, it is easy to justify that the result it computes is actually the gcd.

Each successive refinement that we have proposed improves the efficiency but does not substantially change what is being computed. Hence, we can argue that all of the algorithms we have seen so far compute the correct value.

How efficient are these algorithms? Even in the final version, where we eliminated lists, we had to examine all numbers from 1 to min(m, n). This is similar to what we saw when adding numbers by counting. If the smaller number goes from 3 digits to 4 digits, we have to scan 10 times as many values to find the common divisors. If we go from 3 digits to 5 digits, the work grows by a factor of 100.