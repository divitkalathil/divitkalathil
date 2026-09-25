"""Lexicographically largest permutation after sorting exactly one window.

Problem
-------
`shipmentOrder` is a permutation of 1..n. Exactly one contiguous window of
length `windowSize` must be sorted ascending. Return the lexicographically
largest array achievable.

Key facts
---------
1. Sorting a window never makes the array larger. At the first position the
   window changes, the sorted copy places the minimum of the remaining window,
   which is strictly smaller than what was there. So every candidate result is
   <= the original array, with equality iff the chosen window is already sorted.

2. Therefore, let d(i) be the first index at which sorting the window at i
   changes the array. Results with a longer untouched prefix win, so the
   objective is to maximize d(i).

3. Ties on d(i) are broken by the *smaller* i: if d(i) == d(j) for i < j, both
   results are rearrangements of the same multiset over positions
   [d, j+windowSize-1] and identical afterwards, and candidate j lays that
   multiset out fully ascending -- the lexicographically smallest arrangement.

Computing d(i)
--------------
Position k stays put iff a[k] is the minimum of a[k..e] where e = i+W-1, i.e.
iff a[k] is smaller than every later element inside the window. For a fixed e
those positions are exactly the entries of the classic increasing monotonic
stack built while scanning left to right. So d(i) is the first index >= i that
is *missing* from that stack.

Scanning e once and keeping the stack as a deque of maximal runs of consecutive
indices makes each query O(1): indices below i are dropped from the front (they
can never be needed again, since i only grows), so the answer is read off the
front run. Every index is pushed and popped at most once at each end.

Complexity: O(n) time, O(n) space.
"""

from collections import deque
from typing import List


def maximizeShipmentOrder(shipmentOrder: List[int], windowSize: int) -> List[int]:
    a = shipmentOrder
    n = len(a)
    w = windowSize
    if w <= 1 or w > n:
        return a[:]

    # Maximal runs of consecutive indices currently on the monotonic stack,
    # stored as [start, end] index pairs in increasing order.
    runs = deque()
    best_d = -1
    best_i = 0

    for e in range(n):
        v = a[e]
        while runs and a[runs[-1][1]] > v:
            back = runs[-1]
            back[1] -= 1
            if back[1] < back[0]:
                runs.pop()
        if runs and runs[-1][1] == e - 1:
            runs[-1][1] = e
        else:
            runs.append([e, e])

        if e < w - 1:
            continue
        i = e - w + 1

        while runs[0][1] < i:
            runs.popleft()
        front = runs[0]
        if front[0] < i:
            front[0] = i

        if front[0] > i:
            d = i  # a[i] is not the window minimum, so position i moves
        elif front[1] == e:
            return a[:]  # window already ascending: nothing changes at all
        else:
            d = front[1] + 1

        if d > best_d:
            best_d = d
            best_i = i

    return a[:best_i] + sorted(a[best_i:best_i + w]) + a[best_i + w:]


def maximizeShipmentOrderBrute(shipmentOrder: List[int], windowSize: int) -> List[int]:
    """O(n * w log w) reference implementation used to validate the fast one."""
    a = shipmentOrder
    n, w = len(a), windowSize
    return max(
        a[:i] + sorted(a[i:i + w]) + a[i + w:]
        for i in range(n - w + 1)
    )


if __name__ == "__main__":
    import random
    import time

    assert maximizeShipmentOrder([5, 1, 4, 3, 2], 3) == [5, 1, 3, 4, 2]

    for _ in range(3000):
        n = random.randint(1, 9)
        arr = list(range(1, n + 1))
        random.shuffle(arr)
        w = random.randint(1, n)
        fast = maximizeShipmentOrder(arr, w)
        slow = maximizeShipmentOrderBrute(arr, w)
        assert fast == slow, (arr, w, fast, slow)
    print("randomized tests passed")

    n = 200_000
    arr = list(range(1, n + 1))
    random.shuffle(arr)
    for w in (2, n // 2, n):
        start = time.perf_counter()
        maximizeShipmentOrder(arr, w)
        print(f"n={n} w={w}: {time.perf_counter() - start:.3f}s")

    for name, arr in (
        ("descending", list(range(n, 0, -1))),
        ("ascending", list(range(1, n + 1))),
    ):
        start = time.perf_counter()
        maximizeShipmentOrder(arr, n // 3)
        print(f"{name} n={n}: {time.perf_counter() - start:.3f}s")
