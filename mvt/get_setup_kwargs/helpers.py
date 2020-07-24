# coding: utf-8
"""
Helpers for the `get_setup_kwargs` functions (`main.py` and `py2.py`).
[Python 2/3 Compatible]
"""
import os
import sys
from contextlib import contextmanager

try:
    from pathlib import Path
    from typing import Iterator, Union
except ImportError:
    pass


@contextmanager
def with_working_dir(path):
    # type: (Union[Path, str]) -> Iterator[None]
    """Change working directory to `path` and restore when done."""
    try:
        path = path.__fspath__()
    except AttributeError:
        pass

    old_cwd = os.getcwd()
    os.chdir(path)

    try:
        yield
    finally:
        os.chdir(old_cwd)


@contextmanager
def add_to_path(path):
    # type: (Union[Path, str]) -> Iterator[None]
    """Add `path` to `sys.path` and restore when done."""
    try:
        path = path.__fspath__()
    except AttributeError:
        pass

    old_path = sys.path
    sys.path = sys.path[:]
    sys.path.insert(0, path)

    try:
        yield
    finally:
        sys.path = old_path
