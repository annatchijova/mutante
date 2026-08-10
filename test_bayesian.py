# Copyright 2026 Anna Tchijova, Gemini
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Unit tests for the non-stationary (discounted) Thompson Sampling orchestrator.

The orchestrator must keep exploring under sparse, non-stationary rewards
instead of locking onto a single mutation family. These tests assert the
mechanism directly (bounded posteriors, prior recovery) so they do not depend
on RNG luck, plus one seeded end-to-end adaptation check.

Run: `python test_bayesian.py`  or  `pytest test_bayesian.py`
"""

import random

from agent_mutante.engine.bayesian import ThompsonSamplingOrchestrator

FAM = ["A", "B", "C", "D", "E"]


def test_backward_compat():
    # Legacy call site (no discount/seed) must still work unchanged.
    b = ThompsonSamplingOrchestrator(FAM)
    assert b.select_mutation() in FAM
    assert set(b.get_probs()) == set(FAM)


def test_discount_guard():
    for bad in (0.0, -0.1, 1.01, 2.0):
        raised = False
        try:
            ThompsonSamplingOrchestrator(FAM, discount=bad)
        except ValueError:
            raised = True
        assert raised, f"discount={bad} should raise ValueError"


def test_seeded_replay_is_deterministic():
    a = ThompsonSamplingOrchestrator(FAM, seed=42)
    b = ThompsonSamplingOrchestrator(FAM, seed=42)
    assert [a.select_mutation() for _ in range(64)] == [b.select_mutation() for _ in range(64)]


def test_discount_bounds_confidence():
    # Classic Thompson Sampling accumulates without bound; the discounted
    # variant converges to ~ 1 / (1 - discount), keeping posterior variance
    # alive so exploration never dies.
    classic = ThompsonSamplingOrchestrator(FAM, discount=1.0)
    disc = ThompsonSamplingOrchestrator(FAM, discount=0.98)
    for _ in range(1000):
        classic.update("A", True)
        disc.update("A", True)
    ai = FAM.index("A")
    assert classic.alpha[ai] == 1001.0   # unbounded growth (the bug)
    assert disc.alpha[ai] < 60.0         # bounded near the 1 + 1/(1-0.98) = 51 fixed point


def test_stale_arm_recovers_toward_prior():
    # An arm buried by failures must decay back toward the Beta(1,1) prior once
    # other arms are exercised, so it becomes explorable again (anti-laziness).
    b = ThompsonSamplingOrchestrator(FAM, discount=0.95)
    ai = FAM.index("A")
    for _ in range(50):
        b.update("A", False)             # bury A under failures
    buried_beta = b.beta[ai]
    for _ in range(300):
        b.update("B", True)              # exercise a different arm; A only decays
    assert b.beta[ai] < buried_beta      # A's stale failure evidence faded
    assert b.beta[ai] < 2.0 and b.alpha[ai] < 2.0   # A is back near the (1,1) prior


def test_adapts_when_reward_shifts():
    # A pays off first; then it goes dry and B becomes the productive family.
    # A healthy bandit migrates to B; a lazy one stays on the stale winner.
    env = random.Random(1234)
    b = ThompsonSamplingOrchestrator(FAM, discount=0.98, seed=7)
    tail = []
    for step in range(1000):
        m = b.select_mutation()
        p = (0.30 if m == "A" else 0.0) if step < 500 else (0.30 if m == "B" else 0.0)
        b.update(m, env.random() < p)
        if step >= 800:
            tail.append(m)
    assert tail.count("B") > tail.count("A")   # migrated to the now-productive family


if __name__ == "__main__":
    import sys

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001 - test harness
            failed += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
