"""
Application configuration module.
Provides environment-specific settings for the Flask application.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    """Base configuration shared across all environments."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "netkalkan-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Default admin credentials (should be changed on first login)
    DEFAULT_ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = "netkalkan2026"

    # Extension sync defaults
    DEFAULT_SYNC_INTERVAL_MINUTES = 5
    DEFAULT_KILL_SWITCH = False
    DEFAULT_LOG_RETENTION_DAYS = 30

    # Batch log limits
    MAX_BATCH_SIZE = 500


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'netkalkan_dev.db')}"


class ProductionConfig(BaseConfig):
    """Production environment configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'netkalkan.db')}"


# Configuration map for easy selection
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config(env_name=None):
    """
    Retrieve the configuration class for the given environment.

    Args:
        env_name: Environment name ('development' or 'production').
                  Defaults to FLASK_ENV environment variable or 'development'.

    Returns:
        Configuration class.
    """
    if env_name is None:
        env_name = os.environ.get("FLASK_ENV", "development")
    return config_map.get(env_name, DevelopmentConfig)
