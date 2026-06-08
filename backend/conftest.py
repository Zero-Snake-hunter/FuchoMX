"""
Root conftest.py — sets required env vars before any module imports happen.
This allows unit tests to import backend modules without a live MongoDB connection.
"""
import os

# Provide dummy env vars so database.py can be imported without a real connection.
# Tests that use db must patch 'services.push_service.db' (or equivalent).
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "quiniela_db_test")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("API_FOOTBALL_KEY", "test-key")
