# MUTANTE — Ideas de comercialización y roadmap técnico

Documento vivo. Reúne ideas para convertir MUTANTE en producto, ordenadas por
esfuerzo/impacto, y apoyadas en dos cosas ya hechas:

1. **Capa multi-proveedor** (`agent_mutante/engine/providers/`) — MUTANTE ya no
   depende solo de Gemini: ataca Gemini, OpenAI y compatibles (OpenRouter, Groq,
   Together, DeepSeek, Ollama, vLLM, LM Studio) y Anthropic.
2. **Suite ampliada de mutaciones** (17 vectores stdlib) conectada al bandit.

---

## 1. Tesis de producto (por qué se vende)

MUTANTE deja de ser "un red-teamer contra Gemini" y pasa a ser una **plataforma
de auditoría adversarial multi-modelo, determinista y auditable**. Tres cosas lo
diferencian de la competencia (garak, PyRIT, promptfoo-redteam, Spikee):

- **Determinismo forense.** Núcleo semiótico con aritmética racional
  (`fractions.Fraction`), cadena SHA-256 y logs BigQuery → resultados
  reproducibles y defendibles (ángulo Daubert / evidencia).
- **Aprendizaje de vectores.** El bandit Thompson Sampling aprende qué familia de
  mutación funciona por modelo → mapas de vulnerabilidad que hoy no existen
  públicamente.
- **Multi-modelo real.** Misma campaña contra GPT, Claude, Gemini y modelos
  locales → matriz de resistencia comparable entre vendors.

**Frase de venta:** *"La matriz de resistencia adversarial reproducible que tu
comité de riesgo puede firmar."*

---

## 2. Segmentos y ofertas

| Segmento | Dolor | Oferta MUTANTE | Modelo de precio |
|---|---|---|---|
| Empresas que compran LLMs (banca, salud, legal) | ¿Qué vendor es más seguro? | Reporte comparativo de resistencia (matriz vendor×vector) | Por auditoría / retainer trimestral |
| Equipos que despliegan apps LLM | ¿Mi system prompt aguanta? | Modo "hardening": ataques específicos a *su* prompt/RAG | SaaS por seat / por app |
| Labs y model providers | Benchmark antes de release | ASR vs estado del arte, regression suite en CI | Licencia enterprise + soporte |
| Consultoras de seguridad / pentesters | Herramienta llave en mano | Self-hosted + white-label de reportes | Licencia OEM |
| Compliance / seguros | Evidencia auditable | Trazas firmadas, scoring tipo CVSS | Add-on por reporte certificado |

**Tres SKUs sugeridos:**
- **Community (OSS):** motor de mutaciones + evaluador determinista, un proveedor.
- **Pro:** multi-proveedor, dashboard, scoring unificado (JCS+JEF+Fidelity), export PDF.
- **Enterprise:** self-hosted, guardrail testing, CI/regression, SSO, trazas firmadas, soporte.

---

## 3. Roadmap técnico priorizado

Notación: **[✔] hecho · [1] alto impacto/bajo esfuerzo · [2] medio · [3] apuesta grande**

### 3.1 Cobertura de modelos y stack
- **[✔] Multi-proveedor** (Gemini/Vertex+AI Studio, OpenAI+compatibles, Anthropic).
- **[1] Matriz de benchmarking cross-model.** Runner que corre el mismo dataset
  contra N modelos y emite la matriz vendor×vector×ASR (ya casi gratis con la
  capa nueva; falta el agregador + export).
- **[2] Guardrail testing.** Integrar `any-guardrail` (Llama Guard, ShieldGemma,
  deepset) como *target*: atacar guardrail solo, modelo solo, y stack completo.
  Amplía el mercado de "evaluar modelos" a "evaluar stacks de seguridad".
- **[2] Costo/latencia por probe.** Registrar tokens y ms por llamada (la capa
  HTTP ya los tiene a mano) → ASR-por-dólar, argumento de compra fuerte.
- **[3] NeMo Guardrails como case study.** Desplegar app protegida y publicar
  "MUTANTE vs NeMo" — resultado vendible.

### 3.2 Vectores de ataque nuevos
- **[✔] Ciphers/encodings/evasión** (atbash, caesar, hex, binary, octal, morse,
  flip, leetspeak, splat, ascii_smuggle) + framing.
- **[1] Best-of-N (BoN) sobre mutaciones.** El bandit elige la *familia*; BoN
  optimiza la *instancia* para ese prompt. Cascada natural, poco código.
- **[2] Crescendo (multi-turno gradual).** Escalada neutro→harmful en N turnos.
  Requiere estado de conversación; es el salto de single-turn a multi-turn.
- **[2] Actor-attack / back-to-the-past.** Framings de roleplay específicos
  (FuzzyAI) — mutaciones genuinamente nuevas.
- **[2] LLM-assisted rewriting.** Reescritura por poesía/multilingüe usando la
  propia capa multi-proveedor (un modelo barato como "mutador").
- **[3] ArtPrompt / multimodal (text2image, tts).** Vectores visuales/audio;
  requiere infra multimodal.

### 3.3 Scoring (hablar el idioma de la industria)
Objetivo: reporte final `[JCS=2.90 | JEF=7.3 | Fidelity=0.81]`.
- **[1] JEF (0din, `pip install 0din-jef`).** Score CVSS-like (impacto/alcance).
  Complementa el JCS interno, es publicable y comparable.
- **[2] Fidelity / RelativeTruthfulness.** Un bypass que alucina debería puntuar
  más bajo. Se puede implementar como juez extra reusando la capa multi-proveedor
  (sin arrastrar PyTorch/FastChat).
- **[2] Baseline de seguridad por modelo (snitching).** Calibrar el JCS basal
  según cuán conservador es el modelo antes de la campaña.

### 3.4 Validación y credibilidad
- **[1] Ground truth con CTFs.** Correr MUTANTE contra los 10 ML-CTF
  (Heist, Rogue_AI_Agent, Matrix_AI_Agent...) con solución conocida → evidencia
  objetiva de que los vectores funcionan.
- **[2] Datasets verbalizados por humanos** (bon-jailbreaking: PAIR/TAP/direct)
  para calibrar el juez.
- **[2] Regression suite en CI.** "Este modelo era resistente al vector X, dejó
  de serlo" → alerta. Vendible como monitoreo continuo.

### 3.5 Producto / plataforma
- **[1] Export de reportes** (PDF/HTML firmado) desde el dashboard actual.
- **[2] Modo hardening (ps-fuzz).** Dado el system prompt de una app, generar
  mutaciones específicas a ese dominio, no solo el corpus genérico.
- **[2] API/SaaS.** Exponer campañas como servicio (ya hay MCP server: base para
  integraciones tipo agente/CI).
- **[3] Prompt injection sobre apps** (Open-Prompt-Injection). Atacar apps LLM
  (RAG, agentes con tools), no solo modelos base — nuevo dominio, nuevo mercado.

---

## 4. Quick wins para las próximas 2 semanas

1. **Matriz cross-model** con la capa nueva: correr dataset contra 3-4 modelos y
   generar la tabla vendor×vector. *(Es la demo comercial más potente y ya está
   casi gratis.)*
2. **JEF integrado** al reporte (una dependencia pip, alto valor de marketing).
3. **BoN sobre mutaciones** (poco código, sube ASR de forma medible).
4. **CTF ground-truth**: resolver 2-3 CTFs automáticamente y documentarlo.
5. **Costo/latencia por probe** en la telemetría → gráfico "ASR por dólar".

---

## 5. Riesgos y mitigaciones

- **Dual-use / legal.** Posicionar explícitamente como herramienta defensiva de
  auditoría autorizada; gating de uso, ToS, y foco en Blue Team. El determinismo
  y las trazas firmadas ayudan a la defensibilidad.
- **Fragilidad de vectores.** Las técnicas caducan cuando los modelos parchean;
  el bandit + regression suite convierten eso en *feature* (detectas el parcheo).
- **Dependencia de APIs de terceros.** Ya mitigado: soporte de modelos locales
  (Ollama/vLLM) permite auditar sin enviar prompts sensibles a un tercero.
- **Costo de campañas 30k+.** Batching async + selección por bandit + modelos
  locales para las fases de exploración baratas.

---

## 6. Nombre / posicionamiento del fork comercial

Si el fork privado se llama `mutante_mutante`, conviene separar:
- **`mutante` (OSS):** motor + evaluador determinista, tracción y comunidad.
- **`mutante_mutante` (privado, comercial):** multi-proveedor avanzado, guardrail
  testing, scoring unificado, reportes firmados, SaaS/enterprise.

Estrategia open-core clásica: el OSS crea confianza y adopción; el valor
enterprise (multi-modelo a escala, compliance, soporte) vive en el privado.
