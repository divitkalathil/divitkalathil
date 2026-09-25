"""Minimal JSON HTTP API (standard library only).

Endpoints:
  GET  /movies
  POST /users/<user_id>/watched   {"movieId": 1}
  POST /users/<user_id>/ratings   {"movieId": 1, "rating": 8}
  GET  /users/<user_id>/recommendations
"""

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from recommender import Movie, UserHistory, recommend

SAMPLE_MOVIES = [
    Movie.create(1, "The Dark Knight", ["Action", "Crime", "Drama"], 9.0),
    Movie.create(2, "Inception", ["Action", "Sci-Fi"], 8.8),
    Movie.create(3, "Interstellar", ["Sci-Fi", "Drama"], 8.6),
    Movie.create(4, "The Notebook", ["Romance", "Drama"], 7.8),
    Movie.create(5, "Superbad", ["Comedy"], 7.6),
    Movie.create(6, "The Hangover", ["Comedy"], 7.7),
    Movie.create(7, "Mad Max: Fury Road", ["Action", "Adventure"], 8.1),
    Movie.create(8, "Toy Story", ["Animation", "Comedy", "Family"], 8.3),
    Movie.create(9, "The Conjuring", ["Horror"], 7.5),
    Movie.create(10, "Paddington 2", ["Family", "Comedy"], 7.8),
    Movie.create(11, "Grown Ups", ["Comedy"], 6.0),
    Movie.create(12, "Blade Runner 2049", ["Sci-Fi", "Drama"], 8.0),
]


class RecommendationService:
    def __init__(self, movies):
        self.movies = list(movies)
        self.movie_ids = {m.id for m in self.movies}
        self.users = {}

    def history(self, user_id):
        return self.users.setdefault(user_id, UserHistory())

    def require_movie(self, movie_id):
        if movie_id not in self.movie_ids:
            raise KeyError(f"movie {movie_id} not found")


def movie_to_json(movie, score=None):
    data = {
        "id": movie.id,
        "title": movie.title,
        "genres": sorted(movie.genres),
        "averageRating": movie.average_rating,
    }
    if score is not None:
        data["score"] = score
    return data


def make_handler(service):
    user_route = re.compile(r"^/users/([^/]+)/(watched|ratings|recommendations)$")

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self):
            if self.path == "/movies":
                return self._send(200, [movie_to_json(m) for m in service.movies])
            match = user_route.match(self.path)
            if match and match.group(2) == "recommendations":
                recs = recommend(service.movies, service.history(match.group(1)))
                return self._send(200, [movie_to_json(m, s) for m, s in recs])
            self._send(404, {"error": "not found"})

        def do_POST(self):
            match = user_route.match(self.path)
            if not match or match.group(2) == "recommendations":
                return self._send(404, {"error": "not found"})
            try:
                body = self._body()
                movie_id = int(body["movieId"])
                service.require_movie(movie_id)
                history = service.history(match.group(1))
                if match.group(2) == "watched":
                    history.watch(movie_id)
                else:
                    history.rate(movie_id, float(body["rating"]))
            except KeyError as exc:
                return self._send(404 if "not found" in str(exc) else 400, {"error": str(exc)})
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                return self._send(400, {"error": str(exc)})
            self._send(201, {"status": "ok"})

        def log_message(self, *args):
            pass

    return Handler


def create_server(host="127.0.0.1", port=8000, movies=SAMPLE_MOVIES):
    return ThreadingHTTPServer((host, port), make_handler(RecommendationService(movies)))


if __name__ == "__main__":
    server = create_server()
    print(f"Serving on http://{server.server_address[0]}:{server.server_address[1]}")
    server.serve_forever()
