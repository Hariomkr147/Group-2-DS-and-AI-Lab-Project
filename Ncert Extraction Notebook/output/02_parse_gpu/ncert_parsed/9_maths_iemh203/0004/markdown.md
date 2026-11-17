```txt
Algorithm to find the divisors of n
1. Start with an empty list-of-divisors.
2. For each number j in the sequence 1,2,3,...,n
– if j divides n, add j to the list-of-divisors.
```

## 11.2.1 Computing the Divisors of a Number

Suppose we want to compute gcd(375, 825).

How do we find the divisors of 375? The divisors of a number are just the factors of that number. Clearly any divisor, or factor, must lie between 1 and 375. The simplest way to find the divisors is to check each number between 1 and 375 and see if it divides 375.

We also have to keep track of the divisors of 375 so that we can compare them with the divisors of 825. We can maintain each of these in a sequence, or a **list**. How do we create the list of divisors of a number? When we start, we do not know any divisors, so the list of divisors is initially empty. Every time we find a new divisor, we add it at the end of the list.

divisors of any number n.

Notice how we use names list-of-divisors and j to identify the values that we keep track of in this algorithm. If we do not use j to identify the number we are checking next as a possible divisor, it would be clumsy to describe what to do each time we find a divisor.

Running through an algorithm step by step is also called **executing** the algorithm. Let us execute this algorithm for a small number, say 18. We use square brackets to denote a list of values — for instance, [1, 4, 9, 16].

Let us see how this algorithm works for a small number, say 18.

Initially list-of-divisors is empty [ ].

• 1 divides 18, so we update list-of-divisors to [1].

• 2 divides 18, so we update list-of-divisors to [1, 2].

• 3 divides 18, so we update list-of-divisors to [1, 2, 3].

4 does not divide 18, so we leave list-of-divisors unchanged as [1, 2, 3].

5 does not divide 18, so we leave list-of-divisors unchanged as [1, 2, 3].