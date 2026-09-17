"""IoT Weather Station backend package.

Provides the Flask application factory, storage layer, alert rule engine,
and the simulated sensor client. All sensor readings handled by this
backend are SIMULATED in software -- there is no real hardware involved.
"""

from .factory import create_app

__all__ = ["create_app"]
