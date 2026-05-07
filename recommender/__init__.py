"""
Recommender package initialization.
Loads model and routes for the movie recommender system.
"""

from .model import MovieRecommender
from .routes import register_routes

__all__ = ["MovieRecommender", "register_routes"]
