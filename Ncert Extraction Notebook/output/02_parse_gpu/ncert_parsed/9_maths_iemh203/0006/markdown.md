divisors(81000) = [1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 18, 20, 24, 25, 27, 30, 36, 40, 45, 50, 54, 60, 72, 75, 81, 90, 100, 108, 120, 125, 135, 150, 162, 180, 200, 216, 225, 250, 270, 300, 324, 360, 375, 405, 450, 500, 540, 600, 648, 675, 750, 810, 900, 1000, 1080, 1125, 1350, 1500, 1620, 1800, 2025, 2250, 2700, 3000, 3240, 3375, 4050, 4500, 5400, 6750, 8100, 9000, 10125, 13500, 16200, 20250, 27000, 40500, 81000]

It is no longer so simple to just inspect the lists to find the largest element common to both of them! We need to do this systematically.

We compute a new list, the list of common divisors. As before, when we compute the list of divisors, this list is initially empty. For each divisor in the first list, we check if it belongs to the second list. If it does, we add it to the list of common divisors. Notice that 1 divides every number, so the list of common divisors will have at least one entry, 1.

Using this, we can compute the list of common divisors of 54000 and 81000, to be [1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 18, 20, 24, 25, 27, 30, 36, 40, 45, 50, 54, 60, 72, 75, 90, 100, 108, 120, 125, 135, 150, 180, 200, 216, 225, 250, 270, 300, 360, 375, 450, 500, 540, 600, 675, 750, 900, 1000, 1080, 1125, 1350, 1500, 1800, 2250, 2700, 3000, 3375, 4500, 5400, 6750, 9000, 13500, 27000].

Since we know that each list of divisors is in increasing order, it must be the case that the list of common divisors is also in increasing order. Hence the largest common divisor is the rightmost element in the list. In other words the gcd of 54000 and 81000 is 27000.

## 11.2.3 First Algorithm for gcd

Combining the steps above, we can write out a complete algorithm to compute the gcd of two numbers m and n. This makes use of the earlier algorithm to compute the list of divisors of a number.

```txt
Algorithm to find gcd(m, n)
1. Let divisors-of-m be the list obtained by computing
divisors(m)
Let divisors-of-n be the list obtained by computing
divisors(n)
3. Start with an empty list common-divisors
```