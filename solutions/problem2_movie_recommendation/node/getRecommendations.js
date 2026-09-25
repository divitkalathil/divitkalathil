// Fixed `getRecommendations` for backend/controllers/ratingController.js.
// Replace the existing function (from `export const getRecommendations` to its closing `};`).
// Relies on the imports already at the top of ratingController.js:
//   import Rating from '../models/Rating.js';
//   import Movie from '../models/Movie.js';

import Movie from '../models/Movie.js';
import Rating from '../models/Rating.js';

export const getRecommendations = async (req, res) => {
  try {
    const userId = req.userId;
    const userRatings = await Rating.find({ userId }).populate('movieId');
    const watchedMovies = userRatings.filter((r) => r.watched);
    const ratedMovies = userRatings.filter((r) => r.rating >= 1);

    const relevantWatchedMovies = watchedMovies.filter((watched) => {
      const ratingEntry = ratedMovies.find(
        (rated) => rated.movieId._id.toString() === watched.movieId._id.toString()
      );
      return !ratingEntry || ratingEntry.rating >= 6;
    });

    if (watchedMovies.length === 0 && ratedMovies.length === 0) {
      return res.json({
        message:
          'Start exploring movies by rating them or marking them as watched to get personalized recommendations!',
        recommendations: [],
      });
    }

    let recommendations = [];

    for (const ratedMovie of ratedMovies) {
      const movie = ratedMovie.movieId;
      if (!movie) continue;

      let similarMovies;

      if (ratedMovie.rating >= 6) {
        similarMovies = await Movie.find({
          _id: { $ne: movie._id },
          genre: { $in: movie.genre },
          rating: { $gte: 7.0 },
        }).limit(30);
      } else {
        similarMovies = await Movie.find({
          _id: { $ne: movie._id },
          genre: { $nin: movie.genre },
          rating: { $lte: 7.0 },
        }).limit(30);
      }

      const scoredMovies = similarMovies.map((similarMovie) => {
        let score = similarMovie.rating / 10;

        if (ratedMovie.rating >= 6) {
          const genreMatches = movie.genre.filter((g) =>
            similarMovie.genre.includes(g)
          ).length;
          const genreScore = genreMatches / Math.max(movie.genre.length, 1);
          score = genreScore * 0.7 + score * 0.3;
          score *= 1.2;
        }

        return {
          movie: similarMovie,
          score: score,
          source: 'rated',
          sourceMovie: movie.title,
          userRating: ratedMovie.rating,
        };
      });

      recommendations.push(...scoredMovies);
    }

    for (const watchedRating of relevantWatchedMovies) {
      const movie = watchedRating.movieId;
      if (!movie) continue;

      const similarMovies = await Movie.find({
        _id: { $ne: movie._id },
        genre: { $in: movie.genre },
        rating: { $gte: 7.0 },
      }).limit(50);

      const scoredMovies = similarMovies.map((similarMovie) => {
        const genreMatches = movie.genre.filter((g) =>
          similarMovie.genre.includes(g)
        ).length;
        const genreScore = genreMatches / Math.max(movie.genre.length, 1);
        const ratingScore = similarMovie.rating / 10;
        const totalScore = genreScore * 0.7 + ratingScore * 0.3;

        return {
          movie: similarMovie,
          score: totalScore,
          source: 'watched',
          sourceMovie: movie.title,
          userRating: watchedRating.rating || null,
        };
      });

      recommendations.push(...scoredMovies);
    }

    // One entry per movie: higher score wins; on a tie the rated signal beats watched.
    const bestByMovie = new Map();
    for (const rec of recommendations) {
      if (!rec.movie || rec.movie.rating < 7.0) continue;
      const key = rec.movie._id.toString();
      const existing = bestByMovie.get(key);
      if (
        !existing ||
        rec.score > existing.score ||
        (rec.score === existing.score && rec.source === 'rated' && existing.source !== 'rated')
      ) {
        bestByMovie.set(key, rec);
      }
    }

    recommendations = [...bestByMovie.values()]
      .sort((a, b) => b.score - a.score)
      .slice(0, 10);

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
