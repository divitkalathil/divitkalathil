# Cheat Sheet — Night-Before Refresher

One page to skim right before the 60-minute ML System Design interview. Full detail in [`ml-system-design-interview.md`](./ml-system-design-interview.md).

## The 8-step script (say it out loud)
1. **Requirements & clarifying Qs** — goal/metric, scale (users/items/QPS), constraints (latency, freshness, compute), data available.
2. **Frame the ML task + metrics** — ranking / classification / regression; offline (NDCG, Recall@K, AUC, ECE) *and* online (CTR, watch time, revenue) + guardrails.
3. **Data & labels** — implicit vs explicit; position bias, delayed feedback, imbalance; time-based split.
4. **Features & feature store** — user/item/context/cross; offline + online store; point-in-time joins; batch vs streaming freshness.
5. **Architecture (funnel)** — retrieval → (light pre-rank) → heavy rank → re-rank.
6. **Training & feedback loops** — retrain cadence, embedding refresh, exploration, model registry.
7. **Serving (latency & compute)** — online vs batch; cascade, caching, batching, quantization/distillation; graceful degradation.
8. **Evaluation & monitoring** — offline gate → A/B/interleaving → monitor latency, drift, calibration, KPIs; rollback.

> Breadth first: sketch the whole pipeline in ~15 min, then go deep. Attach a **number + tradeoff** to every choice.

## The reference funnel (draw this)
```
10^6–10^9 items ─▶ Retrieval (recall) ─▶ Pre-rank ─▶ Heavy rank (precision) ─▶ Re-rank (biz rules)
                    ~1,000, ~20 ms       ~200        top-K, ~60 ms            diversity/policy/auction
```
- **Retrieval:** two-tower + ANN (FAISS/ScaNN/HNSW); search = BM25 + dense, merged via **RRF**.
- **Ranking:** LambdaMART (search), DLRM/Wide&Deep (ads), DIN/transformer (recs), often **multi-task**.
- **Why:** no single model can score millions in ms; retrieval=recall cheap, ranking=precision expensive on a shortlist, re-rank=control.

## Numbers to memorize (order-of-magnitude)
- Page P99 ~100–300 ms; per-ad scoring ~10 ms.
- Funnel: millions/billions → ~1,000 → ~200 → top-10/50.
- Online feature reads: single-digit ms. Feature latency often > model latency.
- INT8 quantization: ~4× smaller, ~2–3× faster.
- Well-calibrated CTR: **ECE < 0.02**.

## Latency/compute levers
Cascade ▸ caching (`model_version_id + hash(input)`, TTL) ▸ dynamic batching ▸ quantization ▸ distillation ▸ ONNX/TensorRT ▸ precompute embeddings/candidates offline ▸ CPU for light stages, GPU for heavy.
**Graceful degradation:** GPU model → distilled CPU model → rules (popularity) → cached/default.

## Metrics quick map
| Stage/task | Offline | Online |
|---|---|---|
| Retrieval | Recall@K, MAP | — |
| Ranking | NDCG@K, MRR | CTR, dwell, watch time |
| Classification/CTR | AUC, PR-AUC, log loss, **ECE** | revenue, actual vs predicted CTR |
| Regression | RMSE/MAE | task KPI |

## Bias & correctness checklist
- Position bias → IPS / position feature ablated / interleaving.
- Delayed feedback → attribution window.
- Feedback loop / cold start → exploration (ε-greedy / Thompson).
- Training-serving skew → one feature definition, point-in-time joins.
- Ship decision = **A/B test**, not offline metric.

## MVP → v1 → v2
- **MVP:** simplest model per stage (popularity/MF + LogReg/GBDT), batch features, daily retrain, one A/B cell + guardrail. *Establishes the loop.*
- **v1:** two-tower+ANN, DLRM/LambdaMART, streaming freshness, re-rank, calibration.
- **v2:** multi-task, sequence models, real-time personalization, bandits, distillation for cost.

## Tradeoffs to be ready to compare
Two-tower vs MF · BM25 vs dense (use both) · GBDT vs deep · pointwise vs listwise LTR · batch vs streaming features · online vs batch inference · GPU big vs distilled CPU · Platt vs isotonic calibration · greedy vs exploration.

## Red flags to avoid
Jump straight to a model · ignore latency budget · name components without tradeoffs · forget training-serving skew · use raw CTR ignoring position bias · no monitoring/rollback · optimize AUC and ignore calibration (ads) · over-build v0 · go silent.

## Logistics & LLM disclosure
Camera on; near a computer with internet for the HackerRank link. If you use an LLM, **self-disclose** and be able to defend every component and tradeoff yourself.
