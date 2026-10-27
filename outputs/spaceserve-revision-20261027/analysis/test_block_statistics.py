import math
import unittest

from block_statistics import T975_DF2, paired


class ThreeBlockTests(unittest.TestCase):
    def test_independent_reference(self):
        # Logs [-0.1,0,0.1] have mean 0, sample SD .1.
        result = paired({2: math.exp(.1), 0: math.exp(-.1), 1: 1}, dict.fromkeys(range(3), 1))
        self.assertAlmostEqual(T975_DF2, 4.302652729911275)
        half = 4.302652729911275 * .1 / math.sqrt(3)
        self.assertAlmostEqual(result['lower'], math.exp(-half))
        self.assertAlmostEqual(result['upper'], math.exp(half))
        self.assertAlmostEqual(result['geometric_mean_ratio'], 1)

    def test_pair_ids_not_insertion_order(self):
        result = paired({2: 6, 0: 2, 1: 4}, {1: 2, 2: 3, 0: 1})
        self.assertAlmostEqual(result['lower'], 2)
        self.assertAlmostEqual(result['upper'], 2)

    def test_reverse_inverts_bounds(self):
        a, b = {0: .9, 1: 1, 2: 1.1}, dict.fromkeys(range(3), 1)
        forward, reverse = paired(a, b), paired(b, a)
        self.assertAlmostEqual(forward['lower'], 1 / reverse['upper'])
        self.assertAlmostEqual(forward['upper'], 1 / reverse['lower'])

    def test_partial_and_requests_are_not_blocks(self):
        for series in ({0: 1, 1: 1}, dict.fromkeys(range(100), 1),
                       {'0': 1, '1': 1, '2': 1}, {False: 1, 1: 1, 2: 1}):
            with self.assertRaises(ValueError):
                paired(series, dict.fromkeys(range(3), 1))

    def test_invalid_metric(self):
        for value in (0, -1, math.inf, math.nan, True):
            with self.assertRaises(ValueError):
                paired({0: value, 1: 1, 2: 1}, dict.fromkeys(range(3), 1))


if __name__ == '__main__':
    unittest.main()
