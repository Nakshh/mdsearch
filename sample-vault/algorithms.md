# Dynamic programming

DP is really just recursion plus caching. If a recursive solution
re-solves the same subproblem many times, storing each subproblem's answer
the first time it's computed turns an exponential brute force into
something polynomial.

## Two flavors

Top-down (memoization): write the natural recursive solution, then wrap it
so repeated calls with the same arguments return a cached answer instead of
recomputing. Bottom-up (tabulation): build a table of subproblem answers
iteratively, smallest first, so by the time you need a larger subproblem
its dependencies are already filled in.

## Graph traversal

Breadth-first search explores a graph level by level using a queue, and is
the right tool whenever you need the shortest path in an unweighted graph.
Depth-first search instead follows one branch as far as it can before
backtracking, using a stack (or recursion) rather than a queue.
