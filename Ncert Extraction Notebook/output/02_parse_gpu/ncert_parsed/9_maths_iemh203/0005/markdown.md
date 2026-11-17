6 divides 18, so we update list-of-divisors to [1, 2, 3, 6].

7 and 8 do not divide 18, so we leave list-of-divisors unchanged as [1, 2, 3, 6].

• 9 divides 18, so we update list-of-divisors to [1, 2, 3, 6, 9].

10, 11, 12, … , 17 do not divide 18, so we keep list-of-divisors unchanged as [1, 2, 3, 6, 9].

18 divides 18, so we update list-of-divisors to [1, 2, 3, 6, 9, 18].

Thus, at the end of the algorithm we have divisors(18) = [1, 2, 3, 6, 9, 18]. Notice that the list is also in increasing order, because we checked for divisors systematically, from 1 to 18.

What is the basic step that we assumed in this algorithm? It is that we know how to compute when a smaller number divides a larger number.

If we go through the steps of the algorithm, we get the following answers.

• divisors(375) = [1, 3, 5, 15, 25, 75, 125, 375]

• divisors(825) = [1, 3, 5, 11, 15, 25, 33, 55, 75, 165, 275, 825]

## Think and Reflect

Try to execute the algorithm to compute the divisors of 15, 135, and 775. How does the amount of work increase as the numbers grow?

## 11.2.2 Finding the Greatest Common Divisor

The second step in our procedure to find the gcd is to compare the lists of divisors of the two numbers and find the largest number that appears in both lists.

If we look through the divisiors of 375 and 825 above, we see that the answer is 75. What if the numbers were 54000 and 81000?

divisors(54000) = [1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 18, 20, 24, 25, 27, 30, 36, 40, 45, 48, 50, 54, 60, 72, 75, 80, 90, 100, 108, 120, 125, 135, 144, 150, 180, 200, 216, 225, 240, 250, 270, 300, 360, 375, 400, 432, 450, 500, 540, 600, 675, 720, 750, 900, 1000, 1080, 1125, 1200, 1350, 1500, 1800, 2000, 2160, 2250, 2700, 3000, 3375, 3600, 4500, 5400, 6000, 6750, 9000, 10800, 13500, 18000, 27000, 54000]