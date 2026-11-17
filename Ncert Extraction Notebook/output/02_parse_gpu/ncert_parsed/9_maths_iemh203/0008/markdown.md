\*3. Divisors occur in pairs. For instance, the divisors of 18 are (1, 18), (2, 9) and (3, 6).

(i) If we write out divisors in pairs, how many numbers do we have to examine between 1 and n to find all the divisors of n?

(ii) If we list out the divisors in pairs, will our gcd algorithm still work in the manner we have described?

## 11.3.1 Improving the Algorithm

## Compute both lists of divisors together

In the algorithm above, we first check all numbers between 1 and m to find the divisors of m. Then we start again with 1 and check all numbers between 1 and n to find the divisors of n. This means we have to scan m + n possible divisors.

We can combine these two scans into one. Let max(m, n) be the maximum of m and n. We run through each j from 1 to max(m, n).

• If j divides m we add j to the list of divisors of m.

• If j divides n we add j to the list of divisors of n.

This reduces the number of possible divisors to be checked from m + n to max(m, n).

## Directly compute the list of common divisors

If we combine the scans, we can directly compute the list of common divisors, instead of first computing the divisors of each number and then combining the lists.

• For each number j from 1 to max(m, n), if j divides both m and n, add j to the list of common divisors.

In fact, a common divisor cannot be larger than the smaller of the two numbers, so we can check for common divisors up to the minimum of m and n rather than the maximum.

For each number j from 1 to min(m, n), if j divides both m and n, add j to the list of common divisors.

## Do away with lists

Do we need to maintain the list of all common divisors? Each time we find a larger common divisor, the ones that we have found earlier are useless!