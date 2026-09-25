// Drop-in replacement for `getRecommendations` in backend/controllers/ratingController.js.
// Assumes the existing models: Movie { title, year, rating, genre, description,
// popularity, type } and Rating { movieId, userId, rating?, watched }.

import Movie from '../models/Movie.js';
import Rating from '../models/Rating.js';

const HIGH_RATING_THRESHOLD = 5;
const MIN_MOVIE_RATING = 7.0;
const BOOST = 1.2;
const LIMIT = 10;

const toGenres = (genre) =>
  (Array.isArray(genre) ? genre : String(genre ?? '').split(','))
    .map((g) => g.trim().toLowerCase())
    .filter(Boolean);

const sharesGenre = (a, b) => a.some((g) => b.includes(g));

const hasRating = (entry) => entry.rating !== undefined && entry.rating !== null;

/**
 * Pure ranking step.
 * @param {Array} activity  user's Rating docs, each with `movieId` populated or joined as `movie`
 * @param {Array} candidates movies with rating >= 7.0
 */
export const rankRecommendations = (activity, candidates) => {
  const seen = new Set(activity.map((a) => String(a.movie._id)));
  const best = new Map();

  for (const entry of activity) {
    const sourceGenres = toGenres(entry.movie.genre);
    const rated = hasRating(entry);
    if (!rated && !entry.watched) continue;

    const ratedHigh = rated && entry.rating > HIGH_RATING_THRESHOLD;
    const wantSimilar = !rated || ratedHigh;
    const multiplier = ratedHigh ? BOOST : 1;
    const source = rated ? 'rated' : 'watched';

    for (const movie of candidates) {
      const id = String(movie._id);
      if (seen.has(id) || movie.rating < MIN_MOVIE_RATING) continue;

      const similar = sharesGenre(toGenres(movie.genre), sourceGenres);
      if (similar !== wantSimilar) continue;

      const score = Math.round(movie.rating * multiplier * 100) / 100;
      const current = best.get(id);
      const better =
        !current ||
        score > current.score ||
        (score === current.score && current.source !== 'rated' && source === 'rated');
      if (better) {
        best.set(id, {
          movie,
          score,
          source,
          sourceMovie: entry.movie.title,
          userRating: rated ? entry.rating : null,
        });
      }
    }
  }

  // A movie similar to a low-rated movie must never be recommended, even if
  // another entry would otherwise suggest it.
  const dislikedGenres = activity
    .filter((a) => hasRating(a) && a.rating <= HIGH_RATING_THRESHOLD)
    .flatMap((a) => toGenres(a.movie.genre));
  const likedGenres = activity
    .filter((a) => !hasRating(a) ? a.watched : a.rating > HIGH_RATING_THRESHOLD)
    .flatMap((a) => toGenres(a.movie.genre));

  return [...best.values()]
    .filter((rec) => {
      const genres = toGenres(rec.movie.genre);
      return !sharesGenre(genres, dislikedGenres) || sharesGenre(genres, likedGenres);
    })
    .sort((a, b) => b.score - a.score || b.movie.rating - a.movie.rating || a.movie.title.localeCompare(b.movie.title))
    .slice(0, LIMIT);
};

export const getRecommendations = async (req, res) => {
  try {
    const userId = req.userId;

    const userRatings = await Rating.find({ userId }).populate('movieId').lean();
    const activity = userRatings
      .filter((r) => r.movieId && (r.watched || hasRating(r)))
      .map((r) => ({ ...r, movie: r.movieId }));

    if (activity.length === 0) {
      return res.json({
        message: 'Start exploring movies by rating them or marking them as watched.',
        recommendations: [],
      });
    }

    const candidates = await Movie.find({ rating: { $gte: MIN_MOVIE_RATING } }).lean();
    const recommendations = rankRecommendations(activity, candidates);

    const formattedRecommendations = recommendations.map((rec) => ({
      _id: rec.movie._id,
      title: rec.movie.title,
      year: rec.movie.year,
      rating: rec.movie.rating,
      genre: rec.movie.genre,
      description: rec.movie.description,
      popularity: rec.movie.popularity,
      type: rec.movie.type,
      score: rec.score,
      source: rec.source,
      sourceMovie: rec.sourceMovie,
      userRating: rec.userRating,
    }));

    if (formattedRecommendations.length !== 0) {
      return res.json({
        message: `Found ${formattedRecommendations.length} personalized recommendations`,
        recommendations: formattedRecommendations,
      });
    }

    res.json({
      message: 'No recommendations found',
      recommendations: [],
    });
  } catch (error) {
    console.error('Get recommendations error:', error);
    res.status(500).json({ message: 'Server error' });
  }
};
