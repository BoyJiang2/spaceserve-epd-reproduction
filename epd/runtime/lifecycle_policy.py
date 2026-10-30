"""Scenario and budget policy for the CPU Ray lifecycle diagnostic.

Pure arithmetic: no Ray, no GPU, no /proc. Kept separate so the smoke gate can be
tested without importing the diagnostic.
"""

FULL_SCENARIOS = ((False, False), (True, False), (False, True), (True, True))
SMOKE_SCENARIOS = ((False, False),)


def scenarios(smoke=False):
    return SMOKE_SCENARIOS if smoke else FULL_SCENARIOS


def budgets(smoke, started):
    """Return (work_end, hard_end) as monotonic deadlines.

    The smoke leg exists to prove the Ray connect + one actor round-trip works;
    it must finish well inside a maintenance window, so it gets 120/180 s
    instead of the full 180/300 s.
    """
    if smoke:
        return started + 120, started + 180
    return started + 180, started + 300


def scenario_deadline(work_end, now, window=30):
    """Per-scenario observation window, never past the run's work deadline."""
    return min(work_end, now + window)


def scope(smoke):
    return ('single-scenario CPU Ray smoke only; no GPU/backend approval' if smoke
            else 'four-scenario CPU diagnostic only; no GPU/backend approval')
