# coding: utf-8
"""Get the keyword arguments passed to the `setup()` function."""

try:
    from .main import get_setup_kwargs  # noqa: F401
except SyntaxError:
    # If imported using Python 2 ignore the exception
    import sys
    if sys.version_info[0] != 2:
        raise
