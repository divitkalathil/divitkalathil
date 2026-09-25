import json
import threading
import unittest
import urllib.request

from api import create_server
from recommender import Movie, UserHistory, recommend

MOVIES = [
    Movie.create(1, "Action A", ["Action"], 8.0),
    Movie.create(2, "Action B", ["Action"], 7.5),
    Movie.create(3, "Comedy A", ["Comedy"], 9.0),
    Movie.create(4, "Comedy B", ["Comedy"], 7.2),
    Movie.create(5, "Drama A", ["Drama"], 8.5),
    Movie.create(6, "Low Action", ["Action"], 6.9),
    Movie.create(7, "Action Comedy", ["Action", "Comedy"], 7.0),
]


def ids(recs):
    return [m.id for m, _ in recs]


def scores(recs):
    return {m.id: s for m, s in recs}


class RecommenderTest(unittest.TestCase):
    def test_no_history_returns_top_rated_eligible(self):
        self.assertEqual(ids(recommend(MOVIES, UserHistory())), [3, 5, 1, 2, 4, 7])

    def test_excludes_movies_below_seven(self):
        self.assertNotIn(6, ids(recommend(MOVIES, UserHistory())))

    def test_seven_is_inclusive(self):
        self.assertIn(7, ids(recommend(MOVIES, UserHistory())))

    def test_high_rating_boosts_similar_genres(self):
        h = UserHistory()
        h.rate(1, 9)
        recs = recommend(MOVIES, h)
        self.assertEqual(ids(recs)[:2], [2, 7])
        self.assertAlmostEqual(scores(recs)[2], 7.5 * 1.2)
        self.assertAlmostEqual(scores(recs)[7], 7.0 * 1.2)

    def test_rating_of_five_is_low(self):
        h = UserHistory()
        h.rate(1, 5)
        recs = recommend(MOVIES, h)
        self.assertNotIn(2, ids(recs))
        self.assertNotIn(7, ids(recs))
        self.assertEqual(ids(recs), [3, 5, 4])

    def test_low_rating_promotes_other_genres(self):
        h = UserHistory()
        h.rate(3, 2)
        self.assertEqual(ids(recommend(MOVIES, h)), [5, 1, 2])

    def test_watched_only_recommends_similar_without_boost(self):
        h = UserHistory()
        h.watch(1)
        recs = recommend(MOVIES, h)
        self.assertEqual(ids(recs)[:2], [2, 7])
        self.assertAlmostEqual(scores(recs)[2], 7.5)

    def test_watched_and_rated_high_boosts(self):
        h = UserHistory()
        h.watch(1)
        h.rate(1, 8)
        self.assertAlmostEqual(scores(recommend(MOVIES, h))[2], 7.5 * 1.2)

    def test_watched_and_rated_low_uses_other_genres(self):
        h = UserHistory()
        h.watch(1)
        h.rate(1, 4)
        recs = recommend(MOVIES, h)
        self.assertNotIn(2, ids(recs))
        self.assertEqual(ids(recs), [3, 5, 4])

    def test_seen_movies_are_not_recommended(self):
        h = UserHistory()
        h.watch(3)
        h.rate(5, 9)
        recs = ids(recommend(MOVIES, h))
        self.assertNotIn(3, recs)
        self.assertNotIn(5, recs)

    def test_boosted_ranks_above_higher_rated_unboosted(self):
        movies = [
            Movie.create(1, "Liked", ["Action"], 8.0),
            Movie.create(2, "Similar", ["Action"], 7.5),
            Movie.create(3, "Other", ["Drama"], 8.9),
        ]
        h = UserHistory()
        h.rate(1, 10)
        self.assertEqual(ids(recommend(movies, h)), [2, 3])

    def test_limit_is_ten(self):
        movies = [Movie.create(i, f"M{i}", ["Drama"], 7 + i / 100) for i in range(1, 21)]
        recs = recommend(movies, UserHistory())
        self.assertEqual(len(recs), 10)
        self.assertEqual(ids(recs), list(range(20, 10, -1)))

    def test_invalid_rating_rejected(self):
        with self.assertRaises(ValueError):
            UserHistory().rate(1, 11)


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0, movies=MOVIES)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    def test_flow(self):
        self.assertEqual(self.request("POST", "/users/u1/ratings", {"movieId": 1, "rating": 9})[0], 201)
        status, recs = self.request("GET", "/users/u1/recommendations")
        self.assertEqual(status, 200)
        self.assertEqual([r["id"] for r in recs][:2], [2, 7])
        self.assertAlmostEqual(recs[0]["score"], 9.0)

    def test_unknown_movie(self):
        self.assertEqual(self.request("POST", "/users/u2/watched", {"movieId": 999})[0], 404)

    def test_bad_rating(self):
        self.assertEqual(self.request("POST", "/users/u2/ratings", {"movieId": 1, "rating": 42})[0], 400)


if __name__ == "__main__":
    unittest.main()
