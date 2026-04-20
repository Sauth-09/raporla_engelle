"""
SQLAlchemy database instance.
Shared across all models via dependency injection.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
