"""Movie recommendation scoring.

Rules:
  * Rated high (> 5), watched or not  -> similar genres, 1.2x boost.
  * Rated low (<= 5), watched or not  -> ignore those genres, promote others.
  * Watched without a rating          -> similar genres, no boost.
  * Only movies with average rating >= 7.0 are eligible; return the top 10.
"""

from dataclasses import dataclass, field

HIGH_RATING_THRESHOLD = 5
MIN_AVERAGE_RATING = 7.0
BOOST_MULTIPLIER = 1.2
TOP_N = 10


@dataclass(frozen=True)
class Movie:
    id: int
    title: str
    genres: frozenset
    average_rating: float

    @staticmethod
    def create(id, title, genres, average_rating):
        return Movie(id, title, frozenset(g.lower() for g in genres), float(average_rating))


@dataclass
class UserHistory:
    watched: set = field(default_factory=set)
    ratings: dict = field(default_factory=dict)

    def watch(self, movie_id):
        self.watched.add(movie_id)

    def rate(self, movie_id, rating):
        if not 0 <= rating <= 10:
            raise ValueError("rating must be between 0 and 10")
        self.ratings[movie_id] = rating


def _preference_genres(movies_by_id, history):
    boosted, similar, disliked = set(), set(), set()
    for movie_id, rating in history.ratings.items():
        movie = movies_by_id.get(movie_id)
        if movie is None:
            continue
        if rating > HIGH_RATING_THRESHOLD:
            boosted |= movie.genres
        else:
            disliked |= movie.genres
    for movie_id in history.watched - history.ratings.keys():
        movie = movies_by_id.get(movie_id)
        if movie is not None:
            similar |= movie.genres
    return boosted, similar, disliked


SIMILAR_TIER = 0
OTHER_TIER = 1


def score_movie(movie, boosted, similar, disliked):
    """Return (tier, score) for a candidate, or None if it must not be recommended.

    Lower tier ranks first: genre matches with liked movies come before
    movies from other genres, which fill any remaining slots.
    """
    if movie.average_rating < MIN_AVERAGE_RATING:
        return None
    if movie.genres & boosted:
        return SIMILAR_TIER, movie.average_rating * BOOST_MULTIPLIER
    if movie.genres & similar:
        return SIMILAR_TIER, movie.average_rating
    if movie.genres & disliked:
        return None
    return OTHER_TIER, movie.average_rating


def recommend(movies, history, limit=TOP_N):
    """Return up to `limit` (movie, score) pairs, best first."""
    movies_by_id = {m.id: m for m in movies}
    boosted, similar, disliked = _preference_genres(movies_by_id, history)
    seen = history.watched | history.ratings.keys()

    ranked = []
    for movie in movies:
        if movie.id in seen:
            continue
        result = score_movie(movie, boosted, similar, disliked)
        if result is not None:
            tier, score = result
            ranked.append((tier, round(score, 4), movie))

    ranked.sort(key=lambda r: (r[0], -r[1], -r[2].average_rating, r[2].id))
    return [(movie, score) for _, score, movie in ranked[:limit]]
