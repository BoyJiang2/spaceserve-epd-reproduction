import unittest
from collections import Counter
from freeze_schedule import LOADS, ROLES, schedule


class ScheduleTests(unittest.TestCase):
    def test_exact_budget_and_positions(self):
        state = schedule()
        rows = state['cells']
        self.assertEqual(len(rows), 54)
        self.assertEqual(sum(r['requests'] for r in rows), 5400)
        self.assertEqual(sum(r['warmup'] for r in rows), 1080)
        self.assertEqual([r['index'] for r in rows], list(range(54)))
        self.assertEqual(len({(r['block'],r['images'],r['concurrency'],r['role']) for r in rows}), 54)
        for images, concurrency in LOADS:
            subset = [r for r in rows if (r['images'], r['concurrency']) == (images, concurrency)]
            for role in ROLES:
                self.assertEqual(Counter(r['role_position'] for r in subset if r['role'] == role), Counter({0:1, 1:1, 2:1}))
        groups = {}
        for row in rows:
            groups.setdefault((row['block'],row['images'],row['concurrency']), []).append(row['role'])
        for a, b in ((ROLES[0],ROLES[1]),(ROLES[0],ROLES[2]),(ROLES[1],ROLES[2])):
            self.assertEqual(sum(group.index(a) < group.index(b) for group in groups.values()), 9)
        self.assertEqual(state, schedule())


if __name__ == '__main__':
    unittest.main()
