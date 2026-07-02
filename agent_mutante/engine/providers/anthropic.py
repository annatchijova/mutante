# Copyright 2026 Anna Tchijova
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
providers/anthropic.py — Backend para la Messages API de Anthropic (Claude).

Sin dependencias nuevas: async vía aiohttp, sync vía urllib (stdlib).
Respeta HTTPS_PROXY del entorno.
"""

import json
import urllib.request
import urllib.error

from .base import GenerationConfig, LLMProvider, blocked

DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str, api_key: str = "", base_url: str = DEFAULT_BASE_URL,
                 version: str = ANTHROPIC_VERSION, timeout: float = 60.0, **kwargs):
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.version = version
        self.timeout = timeout

    def available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "ANTHROPIC_API_KEY no configurado"
        return True, ""

    def _endpoint(self) -> str:
        return f"{self.base_url}/messages"

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.version,
        }

    def _payload(self, prompt: str, cfg: GenerationConfig) -> dict:
        # La Messages API exige max_tokens y no acepta top_k=0.
        payload = {
            "model": self.model,
            "max_tokens": cfg.max_output_tokens,
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "messages": [{"role": "user", "content": prompt}],
        }
        if cfg.top_k and cfg.top_k > 0:
            payload["top_k"] = cfg.top_k
        return payload

    @staticmethod
    def _extract(data: dict) -> str:
        try:
            if data.get("type") == "error" or data.get("error"):
                return blocked(str(data.get("error", data)))
            stop = str(data.get("stop_reason") or "").lower()
            blocks = data.get("content") or []
            parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
            text = "".join(parts).strip()
            if not text:
                return blocked(f"empty content (stop_reason={stop or 'none'})")
            return text
        except Exception as e:
            return blocked(f"extraction failed: {e}")

    def complete(self, prompt: str, config: GenerationConfig | None = None) -> str:
        cfg = config or GenerationConfig()
        body = json.dumps(self._payload(prompt, cfg)).encode("utf-8")
        req = urllib.request.Request(
            self._endpoint(), data=body, headers=self._headers(), method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return self._extract(data)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            return blocked(f"HTTP {e.code}: {detail}")
        except Exception as e:
            return blocked(str(e))

    async def acomplete(self, prompt: str, config: GenerationConfig | None = None) -> str:
        cfg = config or GenerationConfig()
        try:
            import aiohttp
        except Exception:
            import asyncio
            return await asyncio.to_thread(self.complete, prompt, cfg)

        payload = self._payload(prompt, cfg)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        try:
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                async with session.post(
                    self._endpoint(), headers=self._headers(), json=payload,
                ) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        return blocked(f"HTTP {resp.status}: {text[:300]}")
                    return self._extract(json.loads(text))
        except Exception as e:
            return blocked(str(e))
