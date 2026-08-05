# Common interview gotchas

Forgetting to cache results in a recursive solution is the single most
common way a candidate's "correct" answer times out on a large input —
the interviewer is often specifically listening for whether you notice the
overlapping subproblems and reach for memoization.

## Complexity analysis

Always state the time and space complexity out loud, even if not asked.
Big-O describes the growth rate as input size increases, not the exact
runtime — O(n log n) sorting dominates O(n^2) approaches only once n gets
large enough, so mention when a "worse" approach might still be fine in
practice.

## Talking through edge cases

Empty input, a single element, duplicate values, and already-sorted input
are the four cases most likely to break an otherwise-correct solution.
Walk through each explicitly before declaring the solution done.
