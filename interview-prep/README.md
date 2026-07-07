# ML System Design Interview — Prep Kit

A structured, end-to-end preparation kit for a **60-minute ML System Design interview** focused on designing production ML pipelines under **latency and compute constraints** (recommendation, search, and ads-ranking systems).

## What this interview is
Design an end-to-end ML system for a real-world case study: draw the architecture, describe every component, state the **minimum viable product**, show how you'd **extend** it, and explain the **pros/cons** versus alternatives. Unlike an Applied ML interview, the focus is on **systems and tradeoffs**, not modeling internals. It is collaborative (ask questions, think out loud), uses a shared editor (HackerRank), and expects your camera on.

## How to use this kit
1. **Learn the framework** → [`ml-system-design-interview.md`](./ml-system-design-interview.md)
   The master guide: an 8-step framework with a 60-minute time budget, a reference architecture diagram, and deep dives on data, features, the multi-stage funnel, serving/latency, evaluation, monitoring, MVP-vs-extensions, domain playbooks (recs/search/ads), tradeoff tables, and pitfalls.
2. **Practice with full walkthroughs** → [`worked-examples.md`](./worked-examples.md)
   Three complete 60-minute scripts: video recommendations, ad CTR prediction, and e-commerce search ranking.
3. **Refresh the night before** → [`cheatsheet.md`](./cheatsheet.md)
   One-page summary: the 8-step script, the reference funnel, numbers to memorize, latency levers, metric map, bias checklist, and red flags.

## The one thing to remember
Cover the whole pipeline end-to-end within the first ~15 minutes, then go deep — and attach a **number and a tradeoff** to every design choice. That is the difference between a "names components" answer and a "reasons about production" answer.

## Suggested practice plan
Pick one prompt per session (recommendation, CTR, search ranking, fraud detection, feed ranking, ETA). Without looking at answers, whiteboard it end-to-end using the 8-step framework and time yourself to 60 minutes. Where you stall is what to study next.
