# ML System Design Interview — Complete Preparation Guide

> **Format:** 60 minutes · collaborative · shared editor (HackerRank) · camera on
> **Goal of the interview:** Design an *end-to-end* ML pipeline for a real-world case study under **latency and compute constraints**. Draw the architecture, describe every component, state the **MVP**, then show how you would **extend** it. Explain the **pros/cons** of your design versus the alternatives you considered.

This is the master document. See also:

- [`worked-examples.md`](./worked-examples.md) — three fully worked 60-minute walkthroughs (video recommendations, ads CTR, e-commerce search).
- [`cheatsheet.md`](./cheatsheet.md) — one-page reference: framework, numbers to memorize, tradeoff tables, drill questions.

---

## Table of contents

1. [What this interview actually tests](#1-what-this-interview-actually-tests)
2. [The repeatable 8-step framework (with a 60-min time budget)](#2-the-repeatable-8-step-framework)
3. [Step 1 — Requirements & clarifying questions](#step-1--requirements--clarifying-questions)
4. [Step 2 — Frame the ML problem & define metrics](#step-2--frame-the-ml-problem--define-metrics)
5. [Step 3 — Data & labels](#step-3--data--labels)
6. [Step 4 — Features & the feature store](#step-4--features--the-feature-store)
7. [Step 5 — Model architecture: the multi-stage funnel](#step-5--model-architecture-the-multi-stage-funnel)
8. [Step 6 — Training pipeline & feedback loops](#step-6--training-pipeline--feedback-loops)
9. [Step 7 — Serving under latency & compute constraints](#step-7--serving-under-latency--compute-constraints)
10. [Step 8 — Evaluation, monitoring & iteration](#step-8--evaluation-monitoring--iteration)
11. [MVP first, then extend — how to frame it](#mvp-first-then-extend)
12. [Latency & compute playbook](#latency--compute-playbook)
13. [Domain playbooks: recommendation, search, ads](#domain-playbooks)
14. [Tradeoffs & alternatives you should be able to compare](#tradeoffs--alternatives)
15. [Common pitfalls & interview red flags](#common-pitfalls--red-flags)
16. [Collaboration, communication & LLM disclosure](#collaboration-communication--llm-disclosure)
17. [Curated resources](#curated-resources)

---

## 1. What this interview actually tests

This is **not** the Applied ML interview. You are **not** graded on the mathematical detail of a loss function or the internals of an attention block. You are graded on whether you can **architect a production system** and reason about it.

| Dimension | What the interviewer is listening for |
|---|---|
| **Problem framing** | Can you turn a fuzzy product goal into a crisp ML task with a measurable objective? |
| **End-to-end thinking** | Data → labels → features → training → serving → evaluation → monitoring → feedback. Nothing left dangling. |
| **Systems reasoning** | Do you respect the latency budget and compute cost? Do you know *what runs online vs. offline/batch*? |
| **Scoping / prioritization** | Can you name a **minimum viable product** and defend it, then layer on extensions? |
| **Tradeoff fluency** | For every choice, can you state why, and what you gave up? "We used X because…, at the cost of…" |
| **Communication** | Do you think out loud, ask clarifying questions, and drive the conversation? |

**The single biggest differentiator:** *quantified* tradeoffs. A B-grade answer names components ("two-tower for retrieval, GBDT for ranking"). An A-grade answer attaches numbers and consequences ("two-tower ANN gives ~20 ms P99 over 100M items and 95% Recall@1000, but it can't use user×item cross-features, so we recover precision in the downstream ranker").

**Golden rule of pacing:** breadth first, then depth. Sketch the whole pipeline end-to-end within the first ~15 minutes so the interviewer sees you can cover the system, *then* go deep where they push.

---

## 2. The repeatable 8-step framework

Use this skeleton for **any** prompt ("design recommendations / search / ads / fraud / feed ranking / ETA / content moderation"). Say the steps out loud so the interviewer can follow your structure.

```
1. Requirements & clarifying questions      (~5 min)
2. Frame the ML problem + metrics           (~5 min)
3. Data & labels                            (~5 min)
4. Features & feature store                 (~5 min)
5. Model architecture (multi-stage funnel)  (~10 min)
6. Training pipeline & feedback loops        (~5 min)
7. Serving: latency & compute               (~10 min)
8. Evaluation, monitoring & iteration        (~5 min)
   + buffer for deep dives / Q&A            (~10 min)
```

Draw this as a left-to-right diagram early. A clean reference architecture you can reproduce from memory:

```
                        ┌─────────────── OFFLINE / BATCH ───────────────┐
  Logs / events ──▶ Data lake ──▶ Label join ──▶ Feature pipeline (Spark)
        │                                              │
        │                                     ┌────────┴────────┐
        │                                     ▼                 ▼
        │                            Offline feature store   Training (retrain daily/…)
        │                                     │                 │
        │                                     │           Model registry ──┐
        ▼                                     ▼                            │
  Streaming (Flink/Kafka) ──▶ Online feature store (Redis) ◀───────┐       │
                                                                   │       ▼
  ┌────────────────────────── ONLINE / REQUEST PATH ───────────────┴───────────────┐
  │ Request ▶ Candidate generation (retrieval) ▶ Light pre-rank ▶ Heavy rank ▶ Re-rank ▶ Response │
  │            millions → ~1,000              ~1,000 → ~200     ~200 → top-K   biz rules            │
  └───────────────────────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                        Serving/impression logs ──▶ (back to Data lake)  [closes the feedback loop]
                                   │
                                   ▼
                        Monitoring: latency P99, drift, calibration, business KPIs
```

Everything below is one step of this framework, expanded.

---

## Step 1 — Requirements & clarifying questions

**Never start designing before you scope.** Spend the first few minutes converting the open-ended prompt into concrete constraints. This is also where you demonstrate collaboration.

Ask about four buckets:

**A. Business goal & scope**
- What is the product and the north-star metric? (engagement / revenue / retention / safety?)
- Who is the user and what is the surface? (home feed, search box, ad slot, notifications?)
- What does *success* look like in one sentence?

**B. Scale**
- How many users / items / requests per second (QPS)? (drives retrieval strategy & sharding)
- Catalog size: thousands, millions, or billions of items? (decides whether you *need* ANN retrieval)
- How many results per request (K)?

**C. Constraints (this interview lives here)**
- **Latency budget**: end-to-end P99 (e.g., 100–300 ms for a page; ~10 ms per-item for ads scoring).
- **Freshness**: must new items/events be reflected in seconds, minutes, or is daily fine?
- **Compute / cost budget**: GPU available? cost per 1k requests? on-device vs. cloud?
- **Constraints on the objective**: fairness, diversity, safety/policy, regulatory.

**D. Data availability**
- What signals do we log today? Are there explicit labels or only implicit feedback?
- Is there a cold-start problem (new users, new items)?

> **Tip:** State your assumptions explicitly when the interviewer is vague: *"I'll assume ~10M items, ~1M DAU, a 200 ms page budget, and that we log impressions + clicks + dwell. Sound right?"* This keeps momentum while inviting correction.

---

## Step 2 — Frame the ML problem & define metrics

Translate the product goal into an ML task. Name the task type explicitly:

| Product goal | Common ML framing |
|---|---|
| "Show relevant videos/products" | **Ranking** (learning-to-rank), often two-stage retrieval + ranking |
| "Will the user click this ad?" | **Binary classification / probability estimation** (must be **calibrated**) |
| "Best search results for a query" | **Retrieval + learning-to-rank** |
| "Is this transaction fraud?" | **Binary classification** (heavy class imbalance) |
| "How long until arrival?" | **Regression** |
| "Is this content policy-violating?" | **Classification / multi-label** |

**Then define metrics in two layers** — this pairing is what interviewers want:

- **Offline / model metrics** (fast to iterate, computed on held-out logs):
  - Retrieval: **Recall@K**, MAP.
  - Ranking: **NDCG@K**, MRR, MAP.
  - Classification: **AUC-ROC / AUC-PR**, **log loss**, and **calibration (ECE)** for anything feeding an auction or threshold.
  - Regression: RMSE / MAE.
- **Online / business metrics** (the truth, measured via A/B test):
  - Engagement: **CTR**, session length, watch time, dwell time, DAU retention.
  - Revenue: **revenue per session**, RPM, conversion rate.
  - **Guardrails** you must not regress: latency P99, diversity, policy-violation rate, complaint/hide rate.

> **Key insight to voice:** offline metrics are a *proxy*. You ship based on **online** metrics from a controlled experiment, using offline metrics only to decide *which* candidates are worth an A/B test.

---

## Step 3 — Data & labels

Describe where labels come from — this is where feedback loops and bias sneak in.

**Label sources**
- **Implicit feedback** (clicks, watch >50%, dwell, purchases): abundant but **noisy and biased**. Define the positive precisely (e.g., "watched > 50% of the video" is a stronger signal than a click).
- **Explicit feedback** (ratings, thumbs, reports): sparse but high quality.
- **Human annotation / golden sets**: expensive; reserve for evaluation and for a trusted NDCG benchmark.

**Data hazards to call out proactively**
- **Position / presentation bias**: items shown higher get clicked regardless of quality. Correct with **inverse propensity weighting (IPS)**, a position feature ablated at inference, or **randomized interleaving**.
- **Delayed feedback**: conversions (and some clicks) arrive after the impression. Use an **attribution window** (e.g., click within 60 s; conversion within 7/30 days) and handle early-stopping false negatives.
- **Feedback loops**: the model only sees data for items it chose to show. Reserve a small **exploration budget** (ε-random or Thompson sampling) to gather unbiased signal.
- **Class imbalance** (fraud, CTR): most impressions are negatives → use PR-AUC, negative subsampling (with recalibration), focal loss.
- **Train/serve split discipline**: split by **time**, not randomly, to reflect production and avoid leakage.

**Sampling:** for retrieval training, negatives matter a lot — use **in-batch negatives** plus **hard negatives** (items that are close but wrong) to sharpen discrimination.

---

## Step 4 — Features & the feature store

Group features by entity; this shows structure:

- **User features**: demographics, long-term history embeddings, recent session actions.
- **Item features**: category, metadata, age/freshness, content embeddings (text/image), popularity stats.
- **Context features**: device, time of day, location, query, slot/placement.
- **Cross features**: user×item interactions ("has this user engaged with this creator/brand before?"). These are the most powerful for **ranking** and are exactly what a two-tower retrieval model *cannot* express.

**The feature store** (Feast/Tecton-style) is the backbone that prevents the #1 production bug, **training–serving skew**:

- **Offline store** — historical values (data lake / warehouse), used to build training sets with **point-in-time correct joins** (never leak the future).
- **Online store** — low-latency key–value (Redis/DynamoDB) serving fresh features in single-digit ms at request time.
- **One definition, two paths**: compute a feature once, serve it to both training and serving, so the same logic produces the same value.

**Freshness strategy (a classic tradeoff to voice):**
- Stable features (user long-term history, item metadata) → compute **offline/batch** (e.g., nightly Spark).
- Time-sensitive features (last few clicks, "trending in last 10 min") → compute in a **streaming pipeline** (Flink/Kafka) and serve from the online store.
- Fully stale features make the ranker "score yesterday's world"; fully real-time features add latency and operational cost. **Hybrid is the production answer.**

---

## Step 5 — Model architecture: the multi-stage funnel

This is the heart of the interview for recommendation/search/ads. **No single model can cheaply score millions of items within milliseconds**, so production systems use a **cascade** where each stage is more expensive but sees fewer items.

```
   Corpus            Retrieval /            Light            Heavy             Re-rank
 (10^6–10^9) ──▶  candidate generation ──▶ pre-rank  ──▶    rank    ──▶   (business logic)
                    → ~1,000               → ~200          → top-K          → final list
   cheap, recall-first                                    expensive, precision-first
```

### Stage 0 (search only): Query understanding
Spell correction, synonym/expansion, intent classification (navigational vs. informational vs. transactional). Produces a clean query + a query embedding.

### Stage 1 — Retrieval / candidate generation (recall-first, ~10–20 ms)
Goal: reduce millions/billions → ~1,000 candidates with **high recall**.
- **Two-tower (dual-encoder) model**: a user/query tower and an item tower produce embeddings in the *same* space. **Item embeddings are precomputed offline and indexed**; at request time you compute only the user embedding and do **approximate nearest neighbor (ANN)** search (FAISS / ScaNN / HNSW). This asymmetry is what makes sub-100 ms retrieval over 100M+ items possible.
  - *Constraint that defines everything:* the towers never share computation until the final dot product, so the model **cannot use cross-features** — that's fine, because retrieval needs recall, not precision.
- **Search retrieval:** run **BM25 over an inverted index** (great for exact-match/navigational/rare terms) **in parallel with dense ANN** (great for paraphrase/semantic), then **merge with Reciprocal Rank Fusion (RRF)** and dedup. BM25 and dense are complementary, not substitutes.
- Often **many candidate generators run in parallel** (subscriptions, trending, personalized, co-visitation) and their outputs are unioned.

### Stage 2 — Light pre-ranker (~15 ms, CPU)
Optional but common at large scale. A cheap model (e.g., **LightGBM**) trims ~1,000 → ~200 using a few fast cross-features, so the expensive model runs on fewer items.

### Stage 3 — Heavy ranker (precision-first, ~50–60 ms, often GPU)
Now you can afford a rich model on ~200 candidates:
- **GBDT / LambdaMART** — the industry-standard listwise learning-to-rank model for search; directly optimizes NDCG; ~150 trees can score 1,000 candidates in ~15 ms on CPU.
- **DLRM / Wide & Deep** — for ads/CTR and large-scale recsys: embedding tables for high-cardinality sparse IDs + dot-product feature interactions + MLP; handles billions of sparse features.
- **DIN / transformer rankers** — attention over user history for recommendations.
- **Multi-task heads** — predict CTR, conversion, watch time, likes/shares jointly, then combine into a single utility score. This is how you optimize for long-term satisfaction rather than pure clickbait.

### Stage 4 — Re-ranking / post-processing (business logic)
Deterministic rules the model shouldn't learn implicitly: **diversity** (cap items per author/category), **freshness boosts**, **policy/safety filters**, dedup, ads **auction & pricing**, exploration injection.

> **Why this pattern wins (say this):** retrieval optimizes recall cheaply; ranking optimizes precision expensively but only on a shortlist; re-ranking enforces product control. One model can't satisfy all three within the latency budget — the cascade lets you *pay the expensive model's cost only where it matters*.

---

## Step 6 — Training pipeline & feedback loops

- **Training data assembly**: join logged impressions/features with labels using point-in-time joins; apply position-bias correction; build train/val/test **split by time**.
- **Retraining cadence**: driven by drift. Daily or hourly for fast-moving surfaces (ads, trending); weekly for stable ones. **Online / incremental learning** for session-level intent drift.
- **Embedding/index refresh**: recompute item embeddings nightly for stable items, more frequently (hourly) for trending; hot-reload the ANN index with no downtime.
- **The feedback loop**: serving logs (what you showed + what the user did) flow back into the data lake and become tomorrow's training data. Explicitly note the risk: this loop **amplifies popularity** and **starves items you never show** — mitigate with exploration and by logging propensities.
- **Reproducibility**: version data, features, and models in a **model registry**; every prediction should be traceable to a `model_version_id`.

---

## Step 7 — Serving under latency & compute constraints

This is the section this interview weighs most heavily. Make the **latency budget explicit** and show where every millisecond goes.

**Online vs. batch — decide per component:**
- **Precompute (batch)** when the output space is bounded and context is stable — e.g., nightly top-N per user, item embeddings, daily digests.
- **Online inference** when context changes per request — query-based ranking, real-time personalization, fraud, ads auctions.
- **Hybrid** is typical: precompute embeddings/candidate pools offline, do ranking online.

**Latency levers (know these cold):**
- **Multi-stage cascade** — the biggest lever (above): don't run the heavy model on millions of items.
- **Caching** — cache predictions keyed by `model_version_id + hash(input)` in Redis with a TTL. Extremely effective for search (same query → same ranking). Version in the key means a model swap auto-bypasses stale entries.
- **Dynamic batching** — group concurrent requests into one GPU call to amortize overhead (a single request may use ~1% of GPU parallelism).
- **Model compression** — **quantization** (INT8/FP8 → ~4× smaller, 2–3× faster), **pruning**, **distillation** (train a small student to mimic a large teacher).
- **Compilation / kernels** — ONNX Runtime, TensorRT, operator fusion, mixed precision.
- **Feature latency** — often *dominates* model latency; keep hot features in the online store, precompute expensive aggregates.
- **Hardware** — CPU for light models (GBDT), GPU/accelerators for deep rankers; horizontal autoscaling behind a load balancer.

**Reliability under load — graceful degradation (great senior signal):**
```
1. Primary:   full deep ranker on GPU        (best quality)
2. Fallback:  distilled/smaller model on CPU (slightly worse, no GPU dep)
3. Fallback:  rule-based (popularity / recency) ranking
4. Fallback:  cached / default response      (last-known-good or global average)
```
Bound every downstream call with a timeout; a slow feature fetch should degrade, not stall the request.

**Deployment safety:** versioned artifacts, **shadow mode** (score live traffic, don't serve it, compare offline), **canary / champion–challenger** routing with deterministic user bucketing, and **instant rollback**.

---

## Step 8 — Evaluation, monitoring & iteration

**Offline evaluation** → gate for what earns an experiment: NDCG/Recall/AUC/ECE on a time-split holdout and a human-rated golden set. Do **slice analysis** (per segment/placement/country) — a globally good model can be badly wrong on a cohort.

**Online evaluation** → the decision-maker:
- **A/B testing** with proper power analysis and randomization unit (user/session). Watch primary metric *and* guardrails (latency, diversity, revenue, complaints).
- **Interleaving** for ranking — cheaper/more sensitive than A/B for relevance.
- **Off-policy / counterfactual evaluation** (IPS) to estimate a new policy from logged data before live traffic.

**Monitoring in production:**
- **System**: P99/P999 latency, error rate, throughput, resource use.
- **Data/feature**: input distribution drift, missing-feature rates, feature freshness lag.
- **Model**: prediction distribution shift, **calibration (ECE) drift**, concept drift, silent degradation when a feature pipeline lags.
- **Business**: the KPIs from Step 2, with alerts and auto-triggers for retraining/rollback.

---

## MVP first, then extend

The interview explicitly asks you to state the **minimum viable product** and how to extend it. Frame it as a deliberate v0 → v1 → v2 progression, and justify each jump by a constraint or a measured gap.

**MVP (v0) — ship something that works and is measurable:**
- Simplest defensible model per stage: e.g., **popularity + collaborative-filtering / matrix factorization** retrieval, **logistic regression or GBDT** ranker.
- Batch features, daily retrain, basic online store, one A/B cell, core metric + latency guardrail.
- Rationale to voice: "This establishes the data/serving/experiment loop and a baseline. It's fast to build, easy to debug, and tells us whether the problem is even model-limited."

**v1 — add ML capacity where the MVP is weakest:**
- **Two-tower + ANN** retrieval (fixes cold-start & scale), **DLRM/LambdaMART** ranker (fixes precision), streaming features for freshness, re-ranking for diversity/policy, calibration for ads.

**v2 — sophistication & long-term health:**
- Multi-task ranking (optimize long-term satisfaction), sequence/transformer models, real-time personalization, exploration (bandits) to break feedback loops, per-segment calibration, on-device or distilled models for cost.

> Always tie an extension to a **why**: "We add streaming features *because* trending content decays within minutes and the batch pipeline is 24 h stale."

---

## Latency & compute playbook

A compact decision guide you can recite when the interviewer tightens constraints.

| Problem | First move | Then | Last resort |
|---|---|---|---|
| "Score millions of items in <100 ms" | Multi-stage cascade (ANN retrieval) | Light pre-ranker before heavy ranker | Precompute candidate pools offline |
| "Model is 200 ms, SLA is 100 ms" | Dynamic batching + quantization | Distillation to a smaller student | Prediction caching for hot inputs |
| "Feature fetch is the bottleneck" | Cache hot features in online store | Precompute expensive aggregates | Reduce feature set for online path |
| "GPU cost too high" | Distill / quantize; move light stages to CPU | Cache + batch to raise utilization | Serve fewer candidates to the heavy model |
| "Need real-time freshness" | Streaming feature pipeline | Hourly embedding/index refresh | Time-decay boosts in re-ranker |
| "Serve a 70B LLM" | Tensor/pipeline parallelism across GPUs | vLLM + PagedAttention (KV-cache) | INT4/INT8 quantized serving |

**Numbers worth memorizing** (typical, order-of-magnitude — adapt to the prompt):
- Page-level budget: ~100–300 ms P99. Per-ad scoring: ~10 ms P99.
- Funnel: 10^6–10^9 → ~1,000 (retrieval) → ~200 (pre-rank) → top-10/50 (rank).
- Online feature reads: single-digit to low-double-digit ms.
- Quantization INT8: ~4× smaller, ~2–3× faster.
- Well-calibrated CTR: **ECE < 0.02**.

---

## Domain playbooks

### Recommendation (YouTube / Netflix / TikTok / Spotify / Reels)
- **Framing:** two-stage ranking; primary online metric = watch time / session length (not raw clicks).
- **Retrieval:** two-tower + ANN, trained with in-batch + hard negatives; **label = meaningful engagement** (e.g., watched >50%), not click.
- **Ranking:** multi-task deep model (CTR, watch time, likes/shares) → combined utility.
- **Re-rank:** diversity caps per creator/topic, freshness boost, "already seen" filter.
- **Cold start:** content encoders (BERT for text, ViT for thumbnails) produce a warm item embedding before any interaction; explore new items with a small budget.
- **Failure modes:** popularity feedback loop, filter bubbles, serving staleness on trending content.

### Search ranking (Google / Bing / Amazon / LinkedIn)
- **Framing:** query understanding → hybrid retrieval → LTR → optional neural re-rank.
- **Retrieval:** **BM25 (inverted index) + dense ANN**, merged via **RRF**, with hard filters (language, region, permissions).
- **Ranking:** **LambdaMART** (listwise, optimizes NDCG) with 100–200+ query–doc features; optionally a **BERT cross-encoder** re-ranking the top ~50 on GPU.
- **Labels:** clicks with **position-bias correction** (IPS / interleaving); human-rated golden set for NDCG.
- **Metrics:** NDCG@10 offline; CTR@1, time-to-first-click, zero-click rate online.
- **Senior signal:** "BM25 for exact-match/navigational precision, dense for semantic recall, merged before ranking."

### Ads / CTR prediction (Meta / Google Ads)
- **Framing:** predict `P(click | user, ad, context)` — a **calibrated probability**, because the **auction consumes the probability, not just the ranking**. A 1% calibration error has direct dollar impact.
- **Model:** **DLRM / Wide & Deep** — embedding tables for billion-scale sparse IDs (user_id, ad_id, page_id) + learned interactions + MLP → sigmoid. LightGBM baseline is a fine MVP.
- **Calibration:** **Platt scaling** (logistic on logits), **isotonic regression** (non-parametric), or **temperature scaling**; monitor **ECE** and recalibrate hourly; consider **per-segment (COEC)** calibration since a globally calibrated model can be wrong within advertiser cohorts.
- **Data:** delayed-conversion handling with attribution windows; position-bias correction (IPS); log-what-you-serve for point-in-time features; exploration budget for unbiased signal.
- **Serving:** per-ad P99 ~10 ms at millions of QPS; heavy caching + feature store; daily/hourly retrain.
- **Senior signal:** discuss the **calibration-vs-ranking** distinction (AUC can be great while ECE is terrible) and the **feedback loop** where the model's own choices bias future labels.

---

## Tradeoffs & alternatives

Be ready to compare, with pros/cons, for each of these:

| Choice | Option A | Option B | When to pick which |
|---|---|---|---|
| Retrieval | Two-tower + ANN | Matrix factorization / co-visitation | Two-tower for scale + cold-start generalization; MF simpler & accurate for warm items but degrades on cold start |
| Retrieval (search) | BM25 (sparse) | Dense bi-encoder | BM25 for exact/rare terms; dense for semantic/paraphrase; **use both + RRF** |
| Ranking | GBDT / LambdaMART | Deep model (DLRM/DIN) | GBDT cheap, interpretable, strong on tabular; deep wins with huge sparse features & interactions but 10–100× serving cost |
| LTR loss | Pointwise | Pairwise (RankNet) / Listwise (LambdaMART) | Listwise directly optimizes NDCG → gold standard for search |
| Freshness | Batch features | Streaming features | Batch cheap but stale; streaming fresh but complex → hybrid |
| Inference | Online | Batch precompute | Online for per-request context; batch when output space is bounded |
| Cost | Big model on GPU | Distilled/quantized on CPU | Trade a little quality for large cost/latency wins; use fallbacks |
| Calibration | Platt scaling | Isotonic regression | Platt fast/parametric (monotonic errors); isotonic flexible/non-parametric |
| Explore/exploit | Greedy | ε-greedy / Thompson sampling | Exploration breaks feedback loops & fixes cold start at a small engagement cost |

---

## Common pitfalls & red flags

- Jumping to model architecture in the first two minutes without scoping requirements or metrics.
- Ignoring the **latency/compute budget** — proposing a single giant model over the whole catalog.
- Naming components with **no tradeoffs** ("we'll use a neural net") — always say *why* and *what you gave up*.
- Forgetting **training–serving skew** and point-in-time correctness.
- Using raw CTR as a label without addressing **position bias**.
- Treating offline metrics as the ship decision instead of an **A/B test**.
- No **monitoring / feedback loop / rollback** story — the system ends at "deploy".
- For ads: optimizing AUC while ignoring **calibration**.
- Over-engineering v0 instead of stating a lean **MVP** and extending.
- Going silent — this is a **collaborative** interview; narrate and check in.

---

## Collaboration, communication & LLM disclosure

- **Drive the conversation.** Restate the problem, propose the framework, and check alignment: *"Here's my plan — scope, framing, data, features, architecture, serving, evaluation. I'll sketch it end-to-end, then go deep where you'd like. Sound good?"*
- **Think out loud.** Verbalize tradeoffs as you make them; the interviewer is grading your reasoning, not just the final diagram.
- **Ask before assuming;** when they're vague, state an assumption and move on.
- **Manage the whiteboard/editor:** keep the reference diagram visible and annotate it as you add stages.
- **On LLM use:** the interview allows LLMs **if you self-disclose** and can **speak deeply to the core system**. If you use one, say so explicitly (e.g., *"I'm using an assistant to draft boilerplate; the architecture and tradeoffs are mine — let me walk you through them"*), and be ready to defend every component without it. Never let the tool replace your reasoning; the assessment is on *you* explaining the system.
- **Camera on** unless you've arranged accommodations; be near a computer with internet for the shared HackerRank link.

---

## Curated resources

The following were used to compile this guide and are excellent for deeper study of production recommendation, search, and ads-ranking systems:

- Hello Interview — *ML System Design in a Hurry* (problem breakdowns, e.g., video recommendations): https://www.hellointerview.com/learn/ml-system-design
- System Design Handbook — *Recommendation System Design*: https://www.systemdesignhandbook.com/guides/recommendation-system-design/
- CalibreOS — *Two-Stage Retrieval & Ranking*, *Ad Click Prediction*, *Search Ranking*: https://www.calibreos.com/learn/mlsd-two-stage-retrieval
- InterviewLoop — ML system design guides (recommendation, CTR, search): https://interviewloop.app/learn/ml/
- EngineersOfAI — case studies (ad click prediction, search ranking): https://engineersofai.com/docs/ai-systems/case-studies/
- techinterview.org — ML system design framework, model-serving LLD, search-ranking pipeline: https://www.techinterview.org/
- Two-tower models, retrieval & ranking at scale: https://rajeevraibhatia.com/topics/recsys/two-tower-retrieval-ranking/

**Foundational papers/architectures to name-drop correctly:**
- *Deep Neural Networks for YouTube Recommendations* (Covington et al., 2016) — canonical two-stage candidate-gen + ranking.
- *Wide & Deep Learning* (Cheng et al., 2016) — memorization + generalization for CTR.
- *DLRM* (Naumov et al., 2019) — embedding tables + interactions for large-scale recsys/ads.
- *LambdaMART* (Burges, 2010) — listwise LTR, industry standard for search.
- *Deep Interest Network (DIN)* — attention over user behavior for CTR.
- ANN libraries: **FAISS, ScaNN, HNSW**; feature stores: **Feast, Tecton**.

---

*Next: read [`worked-examples.md`](./worked-examples.md) for three full 60-minute walkthroughs, and [`cheatsheet.md`](./cheatsheet.md) for the night-before refresher.*
