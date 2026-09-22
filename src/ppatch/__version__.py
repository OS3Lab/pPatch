import sys

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata


try:
    __version__ = importlib_metadata.version("ppatch")
except importlib_metadata.PackageNotFoundError:
    __version__ = "0.0.0"
