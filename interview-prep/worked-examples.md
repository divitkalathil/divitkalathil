# Worked Examples — Three 60-Minute Walkthroughs

Each walkthrough applies the [8-step framework](./ml-system-design-interview.md#2-the-repeatable-8-step-framework). Read them as *scripts you could speak* — notice how each one leads with scoping, sketches the whole pipeline early, states an MVP, then extends, and attaches numbers + tradeoffs to every choice.

- [Example 1 — Design a video recommendation system (YouTube/Reels/TikTok)](#example-1--video-recommendations)
- [Example 2 — Design an ad click-through-rate (CTR) prediction system](#example-2--ad-ctr-prediction)
- [Example 3 — Design an e-commerce search ranking system](#example-3--e-commerce-search-ranking)

---

## Example 1 — Video recommendations

### 1. Requirements & clarifying questions
- **Goal:** maximize long-term user satisfaction on the Home feed; north-star = **daily watch time / retention**, not raw clicks (avoid clickbait).
- **Scale (assume):** ~100M videos, ~500M DAU, ~10k QPS peak, return **~20 videos** per feed request.
- **Constraints:** end-to-end **P99 ≤ 200 ms**; trending content must appear within **minutes**; GPU available for ranking; must enforce diversity + safety.
- **Data:** we log impressions, clicks, watch duration, likes/shares, skips. Implicit feedback only; cold-start for new videos and new users.

### 2. ML framing & metrics
- **Task:** two-stage ranking (retrieval → ranking).
- **Label:** *meaningful engagement* = watched > 50% (stronger than a click).
- **Offline:** Recall@1000 (retrieval), NDCG@20 (ranking).
- **Online:** watch time/session, day-7 retention; **guardrails:** P99 latency, topic diversity, report/hide rate.

### 3. Data & labels
- Positive = watch>50% or like/share; negative = impression with skip + in-batch/hard negatives for retrieval.
- Correct **position bias** (IPS / a position feature dropped at inference).
- **Time-based split**; reserve ~1–2% exploration traffic for unbiased signal on new content.

### 4. Features & store
- **User tower:** user_id embedding, last-50 watch history, search history, demographics, time-of-day.
- **Item tower:** video_id, category, title tokens (BERT), thumbnail (ViT), upload recency, popularity.
- **Cross (ranking only):** "has user watched this creator before?", user-topic affinity — impossible in two towers, added downstream.
- **Feature store:** offline (Spark, nightly) for stable features; **streaming (Flink)** for trending/last-N-clicks; online store = Redis, single-digit-ms reads.

### 5. Architecture (draw the funnel)
```
100M videos
  └▶ Candidate generation (many generators in parallel):
        • two-tower + ANN (FAISS/HNSW), user emb @request, item emb precomputed → ~1,000, ~20 ms, Recall@1000≈95%
        • subscriptions / trending / co-visitation generators (unioned)
  └▶ Light pre-ranker (LightGBM, CPU): 1,000 → 200, ~15 ms, cheap cross-features
  └▶ Heavy ranker (transformer/DIN, GPU): 200 → scored, ~60 ms
        • multi-task heads: P(click), P(watch>50%), P(like), predicted watch time → combined utility
  └▶ Re-rank / post-process: diversity cap per creator, freshness boost, "already seen" filter, safety → top 20
```

### 6. Training & feedback
- Retrieval: contrastive loss, in-batch + hard negatives; item embeddings recomputed nightly (hourly for trending); ANN index hot-reloaded.
- Ranker: retrain daily; online/incremental updates for session drift.
- Serving logs → data lake → tomorrow's training set. **Call out** popularity feedback loop → mitigate with exploration + logged propensities.

### 7. Serving / latency
- Only the **user tower** runs online (<5 ms); item embeddings precomputed. ANN <10 ms. Pre-rank on CPU; heavy ranker on GPU with **dynamic batching**.
- **Cache** popular feed slices with short TTL. **Graceful degradation:** GPU ranker → distilled CPU ranker → popularity/trending fallback → cached feed.

### 8. Evaluation & monitoring
- Offline NDCG/Recall gate → **A/B test** (or interleaving) on watch time with latency + diversity guardrails.
- Monitor P99, feature drift, embedding staleness, and business KPIs; auto-alert + rollback.

### MVP → extensions
- **MVP:** popularity + matrix-factorization retrieval, GBDT ranker on click label, batch features, daily retrain, one A/B cell.
- **v1:** two-tower + ANN, multi-task deep ranker on watch-time label, streaming freshness, diversity re-rank.
- **v2:** sequence/transformer user model, content encoders for cold start, bandit exploration, distilled ranker to cut GPU cost.

**Tradeoffs voiced:** two-tower can't use cross-features (recover in ranker); watch-time label beats clicks for long-term satisfaction; streaming features add cost but trending decays in minutes.

---

## Example 2 — Ad CTR prediction

### 1. Requirements & clarifying questions
- **Goal:** predict **P(click | user, ad, context)** to rank eligible ads and feed the **auction**. Revenue-critical.
- **Scale (assume):** billions of impressions/day, millions of ads, **5M scoring requests/sec** peak.
- **Constraints:** **per-ad P99 ≤ 10 ms**; model refreshed at least daily, critical features real-time; **predictions must be calibrated** (auction consumes the probability, not just the order).
- **Data:** impressions + clicks (and downstream conversions with delay). Extreme class imbalance; billion-scale sparse IDs.

### 2. ML framing & metrics
- **Task:** binary probability estimation (calibrated).
- **Offline:** AUC-ROC / **PR-AUC**, **log loss**, and **ECE (target < 0.02)**; slice ECE by placement/country/device.
- **Online:** revenue per impression, actual CTR vs. predicted, advertiser ROI; **guardrails:** latency, policy violations, advertiser-cohort calibration.

### 3. Data & labels
- Positive = click within 60 s of impression; conversion label via **attribution window** (7/30 d) → handle **delayed feedback** & early-stopping false negatives.
- **Position-bias correction** (IPS / position feature ablated at inference); **log-what-you-serve** for point-in-time features.
- Class imbalance → negative subsampling + recalibration; **exploration budget** (ε random ads) for unbiased signal and to break the feedback loop.
- Time-based split; new campaigns/creatives cause distribution shift → beware leakage from random splits.

### 4. Features & store
- **Sparse (high-cardinality):** user_id, ad_id, campaign_id, page_id, publisher_id → **embedding tables** (one-hot is impossible at 3B dims).
- **Dense:** historical CTR of ad/user, budget pacing, time features.
- **Context:** device, placement (Feed/Stories/Reels), geo, hour.
- Feature store with point-in-time joins; online store for real-time features; heavy caching.

### 5. Architecture
```
Eligible ads (per request)
  └▶ (retrieval/targeting pruning: eligibility, budget, targeting filters)
  └▶ CTR model per ad: DLRM
        bottom MLP (dense) + embedding tables (sparse) + pairwise dot-product interactions + top MLP → sigmoid → pCTR
  └▶ Calibration layer (Platt / isotonic; per-segment COEC)
  └▶ Auction: rank by pCTR × bid (× quality), pricing, pacing, policy filters
```
- **MVP model:** logistic regression / **Wide & Deep** or LightGBM baseline; upgrade to **DLRM** for large sparse interactions (10–100× cost, justified at scale).

### 6. Training & feedback
- Retrain **daily**, hourly recalibration; **online learning** for intent drift.
- Feedback loop: model's own choices bias future labels → exploration + IPS.

### 7. Serving / latency
- Per-ad **P99 ~10 ms** at millions of QPS → embedding lookups + MLP, aggressive **prediction caching** (`model_version_id + hash(features)`), feature-store reads dominate latency so keep hot features online.
- Quantize/distill for cost; horizontal autoscaling; shadow + canary deploys.

### 8. Evaluation & monitoring
- Offline AUC/log-loss/ECE + slice analysis gate → **A/B** on revenue with calibration & latency guardrails; off-policy (IPS) pre-check.
- Monitor **ECE drift** (alert if > 0.02), prediction distribution, feature freshness, revenue.

### MVP → extensions
- **MVP:** logistic regression on hashed features + Platt scaling, daily retrain, ECE + revenue guardrails.
- **v1:** DLRM with embedding tables, isotonic per-segment calibration, streaming features, delayed-conversion modeling.
- **v2:** multi-task (CTR + CVR), online learning, exploration bandits, advertiser-cohort fairness.

**Tradeoffs voiced:** AUC can be excellent while ECE is terrible → calibration is first-class; DLRM vs. LightGBM is a quality-vs-serving-cost call; delayed conversions force an attribution-window design choice.

---

## Example 3 — E-commerce search ranking

### 1. Requirements & clarifying questions
- **Goal:** given a query, return the most relevant/purchasable products; optimize conversion + revenue while keeping relevance.
- **Scale (assume):** ~50M products, ~5k QPS, return top 50; multilingual.
- **Constraints:** **P99 ≤ 200 ms**; new products/prices reflected quickly; enforce policy + in-stock filters.
- **Data:** query logs, clicks, add-to-cart, purchases, human relevance ratings available for a golden set.

### 2. ML framing & metrics
- **Task:** query understanding → retrieval → learning-to-rank (+ optional neural re-rank).
- **Offline:** **NDCG@10** on human-rated golden set; Recall@1000 for retrieval.
- **Online:** CTR@1, add-to-cart rate, conversion, revenue, **zero-result / zero-click rate**; guardrails: latency, diversity.

### 3. Data & labels
- Graded relevance from purchases > add-to-cart > click; **position-bias correction** (IPS / randomized interleaving); golden set for trusted NDCG.
- Time-based split; watch for new-product cold start.

### 4. Features & store
- **Query:** tokens/n-grams, **intent class** (navigational/informational/transactional), query embedding, historical query CTR.
- **Doc:** BM25 fields, title/description embeddings, price, rating, popularity/CTR (7d), freshness, in-stock.
- **Query–doc cross:** exact-match flags, embedding cosine, user's category affinity.
- Feature store: doc features precomputed; real-time price/stock via streaming.

### 5. Architecture
```
Query
  └▶ Query understanding: spell correct + synonym expansion + intent classification → clean query + query embedding
  └▶ Hybrid retrieval (parallel):
        • BM25 over inverted index → ~1,000 (exact/rare/navigational)
        • dense ANN (HNSW over 768-d embeddings) → ~500 (semantic/paraphrase)
        • merge with Reciprocal Rank Fusion (RRF) + dedup + hard filters (language/region/in-stock) → ~1,000
  └▶ LTR ranker: LambdaMART (~150 trees, listwise, optimizes NDCG), 200+ features, ~15 ms CPU → top 200
  └▶ Neural re-ranker (optional, high-value queries): BERT cross-encoder on top 50, ~50 ms GPU
  └▶ Post-process: dedup, domain/brand diversity caps, business boosts, policy → top 50
```

### 6. Training & feedback
- LTR trained on click logs with position-bias correction; retrain weekly (query distribution drifts); re-embed docs nightly, price/stock streaming.
- Log impressions + positions + clicks + dwell for every result → continuous training.

### 7. Serving / latency
- Retrieval ~100 ms (Elasticsearch BM25 + ANN), LTR ~15 ms CPU, optional cross-encoder ~50 ms GPU on 50 items only.
- **Cache** rankings per (query, filters) with TTL — same query → same ranking is a huge cache-hit source. Blue-green model swaps via experiment config (no redeploy). Graceful degradation to BM25-only ranking.

### 8. Evaluation & monitoring
- Offline NDCG@10 on golden set gates → **interleaving / A/B** on conversion + CTR@1 with latency guardrail.
- Monitor zero-result rate, latency, feature freshness (price/stock), model drift.

### MVP → extensions
- **MVP:** BM25 retrieval + GBDT pointwise ranker on click labels; daily index; A/B on CTR.
- **v1:** hybrid BM25+dense with RRF, **LambdaMART** listwise, position-bias correction, streaming price/stock.
- **v2:** BERT cross-encoder re-rank for head queries, personalization features, query intent-specific models, semantic query rewriting.

**Tradeoffs voiced:** BM25 (exact/precision) vs. dense (semantic/recall) → use both + RRF; listwise LambdaMART directly optimizes NDCG vs. pointwise; cross-encoder is highest quality but too slow for >50 candidates, so restrict to the shortlist.
