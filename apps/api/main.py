"""Compatibility wrapper for the package-local FastAPI app."""

from bambu_pipe.api import create_app

__all__ = ["create_app"]
