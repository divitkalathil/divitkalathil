"""Maximize Shipment Order.

Exactly one operation is applied: pick a window of length `windowSize` and sort
it ascending. Return the lexicographically largest resulting array.

Key facts (0-indexed, window [i, e] with e = i + k - 1):
  * Sorting the window leaves position t unchanged for every t in the prefix
    where a[t] is the minimum of a[t..e]. The first changed position is
        d_i = min { t in [i, e] : nse[t] <= e }
    where nse[t] is the index of the next smaller element to the right of t.
    At d_i the value strictly decreases. If no such t exists the window is
    already sorted and the array is unchanged, which is the best possible.
  * A larger d_i always wins (the array matches the original for longer).
  * Among windows with the same d_i, the leftmost window wins, because its
    sorted suffix is drawn from a subset of the other window's elements.

Complexity: O(n log n) time, O(n) memory.
"""

import heapq
import sys


def maximizeShipmentOrder(shipmentOrder, windowSize):
    a = list(shipmentOrder)
    n, k = len(a), windowSize

    nse = [n] * n
    stack = []
    for idx, value in enumerate(a):
        while stack and a[stack[-1]] > value:
            nse[stack.pop()] = idx
        stack.append(idx)

    by_nse = [[] for _ in range(n + 1)]
    for t in range(n):
        by_nse[nse[t]].append(t)

    heap = []
    for e in range(k - 1):
        for t in by_nse[e]:
            heapq.heappush(heap, t)

    best_i, best_d = -1, -1
    for i in range(n - k + 1):
        e = i + k - 1
        for t in by_nse[e]:
            heapq.heappush(heap, t)
        while heap and heap[0] < i:
            heapq.heappop(heap)
        if not heap:
            return a
        d = heap[0]
        if d > best_d:
            best_d, best_i = d, i

    a[best_i:best_i + k] = sorted(a[best_i:best_i + k])
    return a


def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    shipment_order = list(map(int, data[1:1 + n]))
    window_size = int(data[1 + n])
    print("\n".join(map(str, maximizeShipmentOrder(shipment_order, window_size))))


if __name__ == "__main__":
    main()
