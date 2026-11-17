In concrete terms, suppose we can count one dot per second. To count the dots in 33 + 27 would take a minute, to count 334 + 272 would take about ten minutes, while 3347 + 2729 would take over one hour and forty minutes.

On the other hand, suppose we work slowly and carefully and take 15 seconds to add two single digit numbers with a carry. Adding 33 + 27 would take about half a minute, while 334 + 272 would take about 45 seconds, while 3347 + 2729 would take about one minute.

Whenever we provide an algorithm, we also have to justify why it works. Combining the dots and counting the sum is how addition is defined. Why does adding individual digits from right to left result in the sum of the two numbers? The key idea is that we are grouping each number into units, tens, hundreds, … and adding each group separately. Whenever a smaller group, say units, generates a large group of ten, we carry over the newly formed ten to the tens group.

## Think and Reflect

1. See if you can complete the argument about grouping by units, tens, hundreds, … to justify why the addition algorithm works.

2. How would you modify the algorithm to add two decimal fractions?

In the rest of this chapter, we will explore the idea of an algorithm in more detail and in some other contexts.

## 11.2 Greatest Common Divisor

Let us look at a familiar problem: computing the **greatest common divisor (gcd) or highest common factor (hcf)** of two numbers. We have already learned different ways to solve this problem, using prime factorisation and other methods.

How can we solve the problem from the definition of gcd? How do we write down an algorithm for this?

The first step is to understand what is required and break down the problem into smaller pieces that we know how to solve.

• We want the greatest common divisor of two numbers.

• For this, we need to first compute the divisors of both numbers and note them down.

Once we have done this, we need to compare the two collections of divisors and find the largest number that is present in both collections.