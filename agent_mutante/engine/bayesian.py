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
from typing import List, Dict

class ThompsonSamplingOrchestrator:
    """
    Manages the selection of mutation vectors using Multi-Armed Bandit (Thompson Sampling).
    Learns continuously which mutations are most effective at triggering JCS bypasses.
    """
    def __init__(self, mutation_types: List[str]):
        self.mutation_types = mutation_types
        n = len(mutation_types)
        self.alpha = np.ones(n)
        self.beta = np.ones(n)

    def select_mutation(self) -> str:
        """
        Samples from the Beta distribution for each vector and selects the highest probability.
        """
        samples = [np.random.beta(self.alpha[i], self.beta[i]) for i in range(len(self.mutation_types))]
        best = int(np.argmax(samples))
        return self.mutation_types[best]

    def update(self, mutation_type: str, success: bool) -> None:
        """
        Updates the Alpha/Beta parameters based on the deterministic evaluation outcome.
        """
        if mutation_type in self.mutation_types:
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
