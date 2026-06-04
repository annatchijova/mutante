# MUTANTE — Demo Script (3 min)
## Google Cloud Rapid Agent Hackathon 2026

---

## ✅ CHECKLIST ANTES DE GRABAR

**Ventanas abiertas y listas:**
- [ ] Terminal con `python3 main.py` pausado (o con resultados ya corriendo)
- [ ] Dashboard en **Attack Families** — con datos pre-cargados (mapa PCA visible)
- [ ] **Agent Console** abierta, con el prompt de roleplay listo en el campo de entrada
- [ ] **Analytics** con las barras de ES|QL visibles
- [ ] Logo en pantalla (favicon del browser o en app)

**Datos cargados antes de grabar:**
```bash
DATASET_PATH=jailbreaks_demo_2k.csv MUTANTE_BATCH_SIZE=200 python3 main.py
```
Corré esto ANTES de grabar — la página de Attack Families necesita datos en Elastic.

**Pantalla:** 1920×1080, zoom al 110%, fuente de terminal grande.
**Grabación:** OBS o Loom. Sin notificaciones. Modo no molestar ON.
**Narración:** ~120 palabras/min — hablá cómodo, no apurado.

---

## 🎬 GUION

---

### 0:00 – 0:20 | HOOK — El problema
**Pantalla:** Pantalla negra → fade in al logo de MUTANTE

> *"Every AI system deployed in production is a potential target.
> Jailbreak attacks — carefully crafted prompts designed to bypass safety layers —
> are growing faster than our ability to detect them.
> Most teams find out their model was vulnerable only after it's too late."*

---

### 0:20 – 0:45 | SOLUCIÓN — Qué es MUTANTE
**Pantalla:** Pasar rápido a la terminal, mostrar `adk web` corriendo, luego al dashboard

> *"MUTANTE is a Bayesian red-teaming agent built on Google Cloud's Agent Development Kit.
> It automatically mutates adversarial prompts using five attack vectors —
> and uses Thompson Sampling to learn, in real time,
> which mutations are most likely to defeat your model."*

---

### 0:45 – 1:15 | PIPELINE — El ciclo en vivo
**Pantalla:** Agent Console — escribir un roleplay prompt, hacer clic en INJECT PAYLOAD
*(El sistema aplica una mutación, llama al target, muestra el veredicto)*

> *"Each probe goes through a full adversarial cycle:
> mutate — attack the target Gemini model — evaluate with our hybrid judge.
> The Jailbreak Confidence Score combines a deterministic semiotic evaluator
> with an LLM judge running at temperature zero.*

**Pantalla:** Primer plano del panel de veredicto — HYBRID JCS en amarillo, BYPASSED visible

> *"The result: a precise, interpretable score — not a black box.
> BYPASSED means the model collaborated with a dangerous request.
> BLOCKED means it held the line."*

---

### 1:15 – 2:00 | WOW — Attack Families (el momento principal)
**Pantalla:** Navegar a Attack Families — dejar que se vea el mapa PCA completo

> *"This is where Elasticsearch becomes the intelligence layer.
> Every probe is embedded using Vertex AI's Gemini Embedding model
> and indexed as a dense vector in Elasticsearch.*

**Pantalla:** Hacer zoom lento al scatter plot — clusters de colores distintos visibles

> *"What you're seeing is a semantic map of attacks.
> Each point is a probe — colored by verdict.
> Clusters reveal attack families:
> groups of prompts the model treats similarly,
> no matter how differently they're worded.*

**Pantalla:** Escribir un prompt en el Similarity Probe, hacer clic en FIND FAMILY

> *"Ask MUTANTE: 'what family does this attack belong to?'
> Elasticsearch's kNN search finds its semantic neighborhood in milliseconds —
> and tells you the bypass rate of that entire family.*

**Pantalla:** Mostrar el % de bypass apareciendo en el card

> *"You've never seen this exact prompt before.
> But MUTANTE already knows it's dangerous."*

---

### 2:00 – 2:25 | ANALYTICS — ES|QL
**Pantalla:** Analytics page — barras de bypass rate por mutación

> *"Real-time analytics powered by Elasticsearch Query Language.
> Which attack vectors are most effective against your model?
> Where are its blind spots?
> These insights feed directly back into the Bayesian optimizer —
> making every next probe smarter than the last."*

---

### 2:25 – 2:50 | IMPACTO
**Pantalla:** Volver al dashboard completo, overview general

> *"MUTANTE was built for the teams who deploy AI —
> not just the teams who research it.
> Before any model goes to production: run MUTANTE.
> Know exactly where it breaks under adversarial pressure.
> Build safer systems, not just faster ones."*

---

### 2:50 – 3:00 | CIERRE
**Pantalla:** Logo MUTANTE + logos de Google Cloud, Elastic, GitHub

> *"MUTANTE — adversarial intelligence, at scale.
> Built on Google Cloud ADK, Gemini, and Elasticsearch.
> Apache 2.0. Open source."*

---

## ✂️ POST-PRODUCCIÓN (5 minutos en CapCut / DaVinci / iMovie)

- **0:00** Fade in desde negro al logo (0.5s)
- **0:20** Corte directo a pantalla — sin transición
- **1:15** Zoom suave hacia el scatter plot (puede ser en el editor, no en vivo)
- **Subtítulos:** Agregalos — los jueces internacionales los agradecen
- **Música de fondo:** Algo sutil e instrumental, -25dB bajo la voz
- **Texto en pantalla:** En 0:20 podés flashear "Google ADK · Gemini · Elasticsearch"

---

## 📋 METADATA PARA YOUTUBE

**Título sugerido:**
```
MUTANTE — AI Red Teaming Agent | Google Cloud + Elastic Hackathon 2026
```

**Descripción:**
```
MUTANTE is a Bayesian adversarial agent that automatically probes LLMs for
safety vulnerabilities using mutated jailbreak prompts, a hybrid semiotic-AI
judge, and semantic attack family clustering powered by Vertex AI embeddings
and Elasticsearch kNN search.

Built with: Google Cloud ADK · Gemini · Elasticsearch 9 · Vertex AI

Google Cloud Rapid Agent Hackathon 2026 submission.
GitHub: https://github.com/annatchijova/mutante
```

**Tags:** `AI safety`, `LLM red teaming`, `Google Cloud`, `Elastic`, `ADK`, `Gemini`, `jailbreak detection`, `hackathon`

---

## 🗣️ PALABRA POR PALABRA — Conteo

| Sección | Palabras | Segundos |
|---|---|---|
| Hook | 42 | 0:00–0:20 |
| Solución | 48 | 0:20–0:45 |
| Pipeline | 65 | 0:45–1:15 |
| Attack Families | 98 | 1:15–2:00 |
| Analytics | 38 | 2:00–2:25 |
| Impacto | 44 | 2:25–2:50 |
| Cierre | 18 | 2:50–3:00 |
| **Total** | **353** | **3:00** |
