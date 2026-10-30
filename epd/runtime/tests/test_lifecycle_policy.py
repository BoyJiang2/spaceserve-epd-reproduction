"""Policy tests for the CPU Ray smoke leg: pure arithmetic, no Ray."""
import unittest

import lifecycle_policy


class LifecyclePolicyTests(unittest.TestCase):
    def test_full_run_keeps_four_scenarios_and_original_budget(self):
        self.assertEqual(len(lifecycle_policy.scenarios(False)), 4)
        self.assertEqual(lifecycle_policy.scenarios(False)[0], (False, False))
        work, end = lifecycle_policy.budgets(False, 100.0)
        self.assertEqual((work, end), (280.0, 400.0))

    def test_smoke_runs_one_scenario_with_shorter_budget(self):
        self.assertEqual(lifecycle_policy.scenarios(True), ((False, False),))
        work, end = lifecycle_policy.budgets(True, 100.0)
        self.assertEqual((work, end), (220.0, 280.0))
        self.assertLess(end - work, lifecycle_policy.budgets(False, 0)[1])
        self.assertLess(work, lifecycle_policy.budgets(False, 100.0)[0])

    def test_scenario_deadline_never_exceeds_work_end(self):
        self.assertEqual(lifecycle_policy.scenario_deadline(100.0, 50.0), 80.0)
        self.assertEqual(lifecycle_policy.scenario_deadline(60.0, 50.0), 60.0)
        self.assertEqual(lifecycle_policy.scenario_deadline(10.0, 50.0), 10.0)

    def test_scope_strings_are_distinct_and_deny_gpu(self):
        full = lifecycle_policy.scope(False)
        smoke = lifecycle_policy.scope(True)
        self.assertNotEqual(full, smoke)
        for text in (full, smoke):
            self.assertIn('no GPU', text)
        self.assertIn('smoke', smoke)


if __name__ == '__main__':
    unittest.main()
