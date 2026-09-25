import random
import unittest

from solution import maximizeShipmentOrder


def brute_force(order, k):
    best = None
    for i in range(len(order) - k + 1):
        candidate = order[:i] + sorted(order[i:i + k]) + order[i + k:]
        if best is None or candidate > best:
            best = candidate
    return best


class MaximizeShipmentOrderTest(unittest.TestCase):
    def test_example(self):
        self.assertEqual(maximizeShipmentOrder([5, 1, 4, 3, 2], 3), [5, 1, 3, 4, 2])

    def test_window_of_one_is_unchanged(self):
        self.assertEqual(maximizeShipmentOrder([5, 4, 3, 2, 1], 1), [5, 4, 3, 2, 1])

    def test_descending_with_window_three(self):
        self.assertEqual(maximizeShipmentOrder([5, 4, 3, 2, 1], 3), [5, 4, 1, 2, 3])

    def test_full_window(self):
        self.assertEqual(maximizeShipmentOrder([3, 1, 2], 3), [1, 2, 3])

    def test_random_against_brute_force(self):
        rng = random.Random(0)
        for _ in range(5000):
            n = rng.randint(1, 9)
            k = rng.randint(1, n)
            order = list(range(1, n + 1))
            rng.shuffle(order)
            self.assertEqual(maximizeShipmentOrder(order, k), brute_force(order, k), (order, k))

    def test_large_input_runs(self):
        n = 200_000
        order = list(range(n, 0, -1))
        result = maximizeShipmentOrder(order, 1000)
        self.assertEqual(result[: n - 1000], order[: n - 1000])


if __name__ == "__main__":
    unittest.main()
