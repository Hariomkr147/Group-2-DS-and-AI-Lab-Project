3. Move to the next column of digits on the left. Add the two digits and the current value of carry.

– If the sum is less than 10, write the sum directly below the two digits. Set the value of carry to 0.

– If the sum is more than 10, write the units digit of the sum directly below the two digits. Set the value of carry to 1.

4. Repeat Step 3 until there are no more digits on the left.

5. If the value of carry is 1, write 1 to the left of the bottom row.

## Exercise Set 11.1

Add two 4-digit numbers using the steps we have written down. Make sure you follow the steps precisely; do not perform any action that is not explicitly mentioned. Are you able to obtain the correct result?

2. What happens if you add a 5-digit number to a 3-digit number. Do our steps handle this situation correctly?

3. Why is it important to align the columns from right to left?

4. In Step 3, why cannot the value of carry be more than 1?

5. What happens if we do not include the fifth step in the algorithm above? Give examples where the algorithm will work correctly and where it will fail to work.

There is also an important assumption in this algorithm, namely, that we know how to add single digit numbers without counting them out. Typically, any algorithm is built using such basic steps that we assume we can perform directly.

The main advantage of this algorithm is that it is much faster than counting explicitly. For instance, if we move from adding 3-digit numbers to adding 4-digit numbers, we have 10 times as many dots to draw and count. On the other hand, if we add the digits right to left, as in the algorithm above, we only have to add 1 more column. Likewise, 5-digit numbers would generate 100 times as many dots as 3-digit numbers, but only 2 more columns to be added.