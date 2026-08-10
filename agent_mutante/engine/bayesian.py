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
bayesian.py — Thompson Sampling Orchestrator for adversarial mutation selection.
"""

import numpy as np
from typing import List, Dict, Optional

class ThompsonSamplingOrchestrator:
    """
    Manages the selection of mutation vectors using Multi-Armed Bandit (Thompson Sampling).
    Learns continuously which mutations are most effective at triggering JCS bypasses.
    """
    def __init__(self, mutation_types: List[str], discount: float = 0.98, seed: Optional[int] = None):
        self.mutation_types = mutation_types
        n = len(mutation_types)
        self.alpha = np.ones(n)
        self.beta = np.ones(n)
        # discount in (0, 1]: fades accumulated evidence toward the Beta(1, 1) prior so
        # the posterior never becomes infinitely confident. Classic (stationary) Thompson
        # Sampling accumulates alpha/beta without bound; under mutante's sparse,
        # non-stationary rewards (a family's easy bypasses get exhausted) that collapses
        # the posterior variance and the bandit locks onto one early-lucky family, never
        # revisiting the others. Discounting keeps exploration alive and lets the bandit
        # adapt. 1.0 recovers classic behaviour; effective memory ~ 1 / (1 - discount)
        # observations per arm.
        if not 0.0 < discount <= 1.0:
            raise ValueError("discount must be in (0, 1]")
        self.discount = float(discount)
        # Injectable RNG so a seeded campaign can be replayed bit-for-bit.
        self._rng = np.random.default_rng(seed)

    def select_mutation(self) -> str:
        """
        Samples from the Beta distribution for each vector and selects the highest probability.
        """
        samples = self._rng.beta(self.alpha, self.beta)
        best = int(np.argmax(samples))
        return self.mutation_types[best]

    def update(self, mutation_type: str, success: bool) -> None:
        """
        Updates the Alpha/Beta parameters based on the deterministic evaluation outcome.
        """
        if mutation_type not in self.mutation_types:
            return
        # Fade every arm toward the Beta(1, 1) prior before crediting the new outcome.
        # This bounds the effective sample size (posterior variance never collapses, so
        # exploration persists) and makes the bandit non-stationary: an exhausted winner
        # decays back and a previously starved family recovers to the prior and is tried
        # again. discount == 1.0 disables the fade (classic Thompson Sampling).
        if self.discount < 1.0:
            self.alpha = 1.0 + self.discount * (self.alpha - 1.0)
            self.beta = 1.0 + self.discount * (self.beta - 1.0)
        idx = self.mutation_types.index(mutation_type)
        if success:
            self.alpha[idx] += 1.0
        else:
            self.beta[idx] += 1.0

    def get_probs(self) -> Dict[str, float]:
        """
        Calculates the expected success probability for each mutation vector.
        """
        means = self.alpha / (self.alpha + self.beta)
        return {self.mutation_types[i]: float(means[i]) for i in range(len(self.mutation_types))}
