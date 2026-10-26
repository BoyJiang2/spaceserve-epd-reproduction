import math
import unittest
from block_statistics import contrast, equivalent, paired


class BlockStatisticsTests(unittest.TestCase):
    def test_independent_nonzero_variance_reference(self):
        # These six logs have mean 0 and sample variance 0.02, so SEM=sqrt(1/300).
        values = [math.exp(x) for x in [-.2, -.1, 0, .1, .2, 0]]
        result = paired(values, [1] * 6)
        half = 2.570581835636305 / math.sqrt(300)
        self.assertAlmostEqual(result['lower'], math.exp(-half))
        self.assertAlmostEqual(result['upper'], math.exp(half))
        result = equivalent(values, [1] * 6, .98, 1.02)
        half90 = 2.0150483733330233 / math.sqrt(300)
        self.assertAlmostEqual(result['lower'], math.exp(-half90))
        self.assertFalse(result['equivalence_demonstrated'])

    def test_six_blocks_not_requests_and_constant_ratio(self):
        result = paired([2, 4, 6, 8, 10, 12], [1, 2, 3, 4, 5, 6])
        self.assertAlmostEqual(result['geometric_mean_ratio'], 2)
        self.assertAlmostEqual(result['lower'], 2)
        self.assertEqual(result['blocks'], 6)
        with self.assertRaises(ValueError):
            paired([1] * 100, [1] * 100)

    def test_reverse_pair_inverts_interval(self):
        a = [0.9, 1.0, 1.1, 0.95, 1.05, 1.02]
        forward, reverse = paired(a, [1] * 6), paired([1] * 6, a)
        self.assertAlmostEqual(forward['lower'], 1 / reverse['upper'])
        self.assertAlmostEqual(forward['upper'], 1 / reverse['lower'])

    def test_equivalence_can_be_inconclusive_due_to_width(self):
        self.assertTrue(equivalent([1] * 6, [1] * 6, .98, 1.02)['equivalence_demonstrated'])
        self.assertFalse(equivalent([.8, 1.2, .8, 1.2, .8, 1.2], [1] * 6, .98, 1.02)['equivalence_demonstrated'])

    def test_global_block_contrast_and_invalid_data(self):
        result = contrast([2] * 6, [1] * 6, [1] * 6, [1] * 6)
        self.assertAlmostEqual(result['geometric_mean_ratio'], 2)
        for bad in (0, math.nan, math.inf):
            with self.assertRaises(ValueError):
                paired([bad] * 6, [1] * 6)


if __name__ == '__main__':
    unittest.main()
