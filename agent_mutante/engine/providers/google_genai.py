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
providers/google_genai.py — Backend Gemini (Vertex AI o Google AI Studio).

Preserva el comportamiento del cliente original de MUTANTE:
  - safety_settings BLOCK_ONLY_HIGH sobre HARM_CATEGORY_DANGEROUS_CONTENT
  - extracción de texto robusta con detección de finish_reason de seguridad

Dos modos, seleccionados por construcción:
  - vertex=True  → Vertex AI (requiere GOOGLE_CLOUD_PROJECT + credenciales ADC)
  - vertex=False → Google AI Studio / Gemini Developer API (requiere GEMINI_API_KEY)
"""

from .base import GenerationConfig, LLMProvider, blocked

_SAFETY_FINISH = {"SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"}


class GoogleGenAIProvider(LLMProvider):
    name = "gemini"

    def __init__(self, model: str, vertex: bool = True, project: str = "",
                 location: str = "us-central1", api_key: str = "", **kwargs):
        super().__init__(model, **kwargs)
        self.vertex = vertex
        self.project = project
        self.location = location
        self.api_key = api_key
        self._client = None
        self._init_done = False

    def available(self) -> tuple[bool, str]:
        try:
            import google.genai  # noqa: F401
        except Exception:
            return False, "paquete google-genai no instalado"
        if self.vertex and not self.project:
            return False, "GOOGLE_CLOUD_PROJECT no configurado (modo Vertex)"
        if not self.vertex and not self.api_key:
            return False, "GEMINI_API_KEY no configurado (modo AI Studio)"
        return True, ""

    def _get_client(self):
        if self._init_done:
            return self._client
        self._init_done = True
        try:
            from google import genai
            if self.vertex:
                self._client = genai.Client(
                    vertexai=True, project=self.project, location=self.location,
                )
            else:
                self._client = genai.Client(api_key=self.api_key)
        except Exception as e:  # pragma: no cover - depende de credenciales
            import sys
            print(f"[!] Error inicializando GenAI client: {e}", file=sys.stderr)
            self._client = None
        return self._client

    def _config(self, cfg: GenerationConfig):
        from google.genai import types
        params = dict(
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            top_k=cfg.top_k,
            max_output_tokens=cfg.max_output_tokens,
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
            ],
        )
        if cfg.response_json:
            params["response_mime_type"] = "application/json"
        return types.GenerateContentConfig(**params)

    @staticmethod
    def _extract(resp) -> str:
        try:
            candidates = getattr(resp, "candidates", None)
            if not candidates:
                return blocked("empty candidates (possible safety block)")
            finish = getattr(candidates[0], "finish_reason", None)
            finish_name = str(getattr(finish, "name", finish) or "").upper()
            if finish_name in _SAFETY_FINISH:
                return blocked(f"finish_reason={finish_name}")
            text = resp.text
            return text if text else blocked("empty text")
        except Exception as e:
            return blocked(f"extraction failed: {e}")

    def complete(self, prompt: str, config: GenerationConfig | None = None) -> str:
        client = self._get_client()
        if client is None:
            return blocked("client not initialized")
        cfg = config or GenerationConfig()
        try:
            resp = client.models.generate_content(
                model=self.model, contents=prompt, config=self._config(cfg),
            )
            return self._extract(resp)
        except Exception as e:
            return blocked(str(e))

    async def acomplete(self, prompt: str, config: GenerationConfig | None = None) -> str:
        client = self._get_client()
        if client is None:
            return blocked("client not initialized")
        cfg = config or GenerationConfig()
        try:
            resp = await client.aio.models.generate_content(
                model=self.model, contents=prompt, config=self._config(cfg),
            )
            return self._extract(resp)
        except Exception as e:
            return blocked(str(e))
