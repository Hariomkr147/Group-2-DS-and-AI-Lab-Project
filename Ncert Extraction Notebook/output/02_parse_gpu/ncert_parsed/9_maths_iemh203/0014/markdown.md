## End-of-Chapter Exercises

1. Compute the following using the improved version of Euclid’s algorithm.

(i) gcd(375, 825)

(ii) gcd(51000, 81000)

(iii) gcd(1789287, 237656)

(iv) gcd(2587392, 157656)

2. Assume that $m \geq n .$ Verify that d divides m and n if and only if d divides both n and m mod n.

3. Write an algorithm prime(n) to check if n is prime. (**Hint:** A prime number p has exactly two distinct factors, 1 and p. Can you make use of divisors(n) to write out prime(n)?)

\*4. Write an algorithm primedivisors(n) to compute the list of divisors of n that are prime numbers. (**Hint:** Compute divisors(n) and then filter out the primes in this list.)

\*5. We can also find the gcd of two numbers by computing prime factorisation of both the numbers. Try to write an algorithm to compute the prime factorisation of a number.

(i) The prime factorisation of 180 is $2 ^ { 2 } \times 3 ^ { 2 } \times 5 ^ { 1 }$ . How would you represent this?

(ii) How would you compare the prime factorisations of two numbers?

## Chapter Summary

• An **algorithm** is a systematic procedure to solve a problem.

• Algorithms consist of basic steps that we know how to execute.

We may execute the same step a number of times; for instance, for each j in 1, 2, ..., n, check if j is a divisor of n.

A step in an algorithm may be conditional; for instance, add j to the list of divisors of n only if j divides n.

When we describe an algorithm to solve a problem, we need to justify that it is correct.

We can also analyse how many steps an algorithm takes, in terms of the size of its input, and decide how efficient it is.