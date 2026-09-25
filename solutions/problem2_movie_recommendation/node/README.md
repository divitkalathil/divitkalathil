# MovieDB – `getRecommendations` Bug Report

File: `backend/controllers/ratingController.js` → `getRecommendations`
Endpoint: `GET /api/ratings/recommendations/user`

Symptom: the "Recommended For You" section shows "No recommendations found" even after a user watches/rates movies.

## Errors found

| # | Location | Buggy code | Fix | Why |
|---|----------|-----------|-----|-----|
| 1 | Empty-state check | `if (watchedMovies.length !== 0 && ratedMovies.length === 0)` | `if (watchedMovies.length === 0 && ratedMovies.length === 0)` | Users who only watched movies got the "Start exploring…" message; brand-new users fell through. |
| 2 | Watched-only query | `genre: { $ne: movie.genre }` | `genre: { $in: movie.genre }` | Watched-only must recommend **similar** genres. |
| 3 | Watched-only query | `rating: { $lte: 7.0 }` | `rating: { $gte: 7.0 }` | Only movies rated 7.0+ may be recommended. |
| 4 | Watched-only result | `source: 'rated'` | `source: 'watched'` | Wrong source label for watched recommendations. |
| 5 | Low-rated query | `genre: { $ne: movie.genre }` | `genre: { $nin: movie.genre }` | `$ne` against an array only excludes exact-array matches; `$nin` excludes any shared genre. |
| 6 | Low-rated query | `rating: { $lte: 7.0 }` | `rating: { $gte: 7.0 }` | 7.0+ rule applies to every recommendation. |
| 7 | Watched filter | watched movies rated high were processed again by the watched loop | only watched movies **without** a rating go through the watched loop | "When a movie is both rated and watched, the rated signal takes precedence." |
| 8 | Watched result | `userRating: watchedRating.rating \|\| null` | omit `userRating` | `userRating` is only present when `source` is `"rated"`. |
| 9 | Final list | no dedupe, no sort, no limit (returned 22–44 items) | dedupe by movie `_id` keeping the higher score (rated wins ties), sort by `score` desc, `.slice(0, 10)` | "Remove duplicates, sort by score descending, return top 10." |
| 10 | No-results message | `'No recommendations found'` | `'No recommendations found. Try rating more movies or marking some as watched to help us understand your preferences better!'` | Must match the README response text (verify the tail of the sentence against the README). |

## Rules implemented

| User action | Strategy | Multiplier |
|-------------|----------|-----------|
| Rated high (> 5) | Similar genres (`$in`) | 1.2 |
| Rated low (≤ 5) | Different genres (`$nin`), `score = ratingScore` | none |
| Watched only | Similar genres (`$in`) | 1.0 |
| Watched + rated high | Similar genres (rated signal) | 1.2 |
| Watched + rated low | Different genres (rated signal) | none |

```
totalScore = (genreScore * 0.7 + ratingScore * 0.3) * multiplier
genreScore  = matching genres / total genres of source movie
ratingScore = candidate rating / 10
```

Check: rating Shawshank (Crime, Drama) 9/10 → Joker (8.4) = (1.0·0.7 + 0.84·0.3)·1.2 = **1.1424** ✔

## Fixed code

See [`getRecommendations.js`](./getRecommendations.js) — drop-in replacement for the function in `ratingController.js`.
