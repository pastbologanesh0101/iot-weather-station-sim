"""Flask application factory."""

import os
import tempfile

from flask import Flask

from . import db as db_module
from .routes import bp as weather_bp


def create_app(testing=False, database_path=None):
    app = Flask(__name__)

    if testing:
        app.config["TESTING"] = True
        if database_path is None:
            # Use a unique temp-file SQLite DB per test app instance so
            # concurrent tests never share state, and it disappears with
            # the OS temp dir cleanup.
            fd, database_path = tempfile.mkstemp(suffix=".sqlite3")
            os.close(fd)
        app.config["DATABASE"] = database_path
    else:
        instance_dir = os.path.join(app.instance_path)
        os.makedirs(instance_dir, exist_ok=True)
        app.config["DATABASE"] = database_path or os.path.join(
            instance_dir, "weather.sqlite3"
        )

    db_module.init_app(app)
    db_module.init_db(app)

    app.register_blueprint(weather_bp)

    return app
