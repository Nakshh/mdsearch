# Caching strategies

Used a plain dict as a simple memo table to avoid recomputing expensive
recursive calls — keyed on the function's input arguments, values are the
already-computed result. Turns an exponential-time recursive function into
something that only does the work once per unique input.

## Cache invalidation

The two hard problems in computer science: cache invalidation, naming
things, and off-by-one errors. A time-to-live (TTL) is the simplest fix —
entries expire after N seconds regardless of whether the underlying data
changed. An LRU (least-recently-used) cache instead evicts the entry that
hasn't been touched in the longest time once the cache hits its size limit.

## Where it matters

API responses, expensive database queries, and recursive math functions
(Fibonacci, edit distance, anything with overlapping subproblems) all
benefit from memoizing results instead of recomputing them from scratch.
