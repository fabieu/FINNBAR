"""FINNBAR package."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("finnbar")
except PackageNotFoundError:
    __version__ = "unknown"
