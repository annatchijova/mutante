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
providers/openai_compatible.py — Backend para la API Chat Completions de OpenAI
y cualquier endpoint compatible con ella.

Un solo proveedor cubre: OpenAI, Azure OpenAI (base_url custom), OpenRouter,
Groq, Together, Fireworks, DeepSeek, vLLM, LM Studio y Ollama (`/v1`). Basta
apuntar `base_url` y `api_key`.

Sin dependencias nuevas: async vía aiohttp (ya requerido por MUTANTE),
sync vía urllib (stdlib). Respeta HTTPS_PROXY del entorno.
"""

import json
import urllib.request
import urllib.error

from .base import GenerationConfig, LLMProvider, blocked

DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAICompatibleProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str, api_key: str = "", base_url: str = DEFAULT_BASE_URL,
                 organization: str = "", timeout: float = 60.0, **kwargs):
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.organization = organization
        self.timeout = timeout

    def available(self) -> tuple[bool, str]:
        # Los endpoints locales (Ollama/vLLM) aceptan cualquier key; solo exigimos
        # api_key cuando el host es la API pública de OpenAI.
        if "api.openai.com" in self.base_url and not self.api_key:
            return False, "OPENAI_API_KEY no configurado"
        return True, ""

    def _endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        return headers

    def _payload(self, prompt: str, cfg: GenerationConfig) -> dict:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "max_tokens": cfg.max_output_tokens,
        }
        if cfg.response_json:
            payload["response_format"] = {"type": "json_object"}
        return payload

    @staticmethod
    def _extract(data: dict) -> str:
        try:
            choices = data.get("choices") or []
            if not choices:
                if data.get("error"):
                    return blocked(str(data["error"]))
                return blocked("empty choices")
            choice = choices[0]
            finish = str(choice.get("finish_reason") or "").lower()
            if finish in {"content_filter"}:
                return blocked("finish_reason=content_filter")
            message = choice.get("message") or {}
            text = message.get("content")
            return text if text else blocked("empty content")
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
            # Sin aiohttp caemos al camino síncrono en un thread.
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
