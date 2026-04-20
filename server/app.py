"""
Flask application factory.
Creates and configures the Flask application with dependency injection.
"""

import os
from flask import Flask
from flask_cors import CORS

from server.config import get_config
from server.models.base import db
from server.services.log_service import LogService
from server.services.blocklist_service import BlocklistService
from server.services.config_service import ConfigService
from server.services.maintenance_service import MaintenanceService
from server.routes.api import api_bp, init_api_services
from server.routes.admin import admin_bp, init_admin_services


def create_app(config_name=None):
    """
    Application factory pattern.
    Creates a fully configured Flask application with all dependencies wired.

    Args:
        config_name: Environment name ('development' or 'production').

    Returns:
        Configured Flask application instance.
    """
    import sys
    # Handle paths for PyInstaller
    if getattr(sys, 'frozen', False):
        # Running as a bundled EXE
        resource_dir = sys._MEIPASS
        # For writable data like the database, we use the folder where the EXE is located
        data_dir = os.path.dirname(sys.executable)
    else:
        # Running normally
        resource_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = resource_dir

    app = Flask(
        __name__,
        template_folder=os.path.join(resource_dir, "server", "templates") if getattr(sys, 'frozen', False) else os.path.join(resource_dir, "templates"),
        static_folder=os.path.join(resource_dir, "server", "static") if getattr(sys, 'frozen', False) else os.path.join(resource_dir, "static"),
    )

    # Load configuration
    app_config = get_config(config_name)
    app.config.from_object(app_config)
    
    # Override database path to be in the writable data_dir
    db_path = os.path.join(data_dir, "netkalkan.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Create services (dependency injection)
    log_service = LogService()
    blocklist_service = BlocklistService()
    config_service = ConfigService()
    maintenance_service = MaintenanceService(config_service)

    # Inject services into blueprints
    init_api_services(log_service, blocklist_service, config_service)
    init_admin_services(log_service, blocklist_service, config_service, maintenance_service, app_config)

    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # Root redirect
    @app.route("/")
    def index():
        from flask import redirect, url_for
        return redirect(url_for("admin.login"))

    # Create database tables and initialize defaults
    with app.app_context():
        db.create_all()
        config_service.initialize_defaults(app_config)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
