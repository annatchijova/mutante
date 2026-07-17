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

import base64
import random

class MutationEngine:
    @staticmethod
    def rot13(text: str) -> str:
        result = []
        for char in text:
            if "A" <= char <= "Z":
                result.append(chr((ord(char) - ord("A") + 13) % 26 + ord("A")))
            elif "a" <= char <= "z":
                result.append(chr((ord(char) - ord("a") + 13) % 26 + ord("a")))
            else:
                result.append(char)
        return "".join(result)

    @staticmethod
    def base64_encode(text: str) -> str:
        return base64.b64encode(text.encode("utf-8")).decode("utf-8")

    @staticmethod
    def mirror(text: str) -> str:
        return " ".join(word[::-1] for word in text.split())

    @staticmethod
    def scramble(text: str) -> str:
        def _scramble_word(word):
            if len(word) > 3:
                middle = list(word[1:-1])
                # Seed a local RNG from the word so the scramble is reproducible:
                # the engine guarantees deterministic, replayable forensic traces,
                # which a global unseeded shuffle would silently break.
                random.Random(word).shuffle(middle)
                return word[0] + "".join(middle) + word[-1]
            return word
        return " ".join(_scramble_word(w) for w in text.split())

    @staticmethod
    def zigzag(text: str) -> str:
        result = ""
        upper = True
        for char in text:
            if char.isalpha():
                result += char.upper() if upper else char.lower()
                upper = not upper
            else:
                result += char
        return result

    def apply(self, text: str, mutation_type: str) -> str:
        method = getattr(self, mutation_type, None)
        if method:
            return method(text)
        return text
