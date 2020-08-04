import contextlib

import pytest


@contextlib.contextmanager
def raises_if_provided(exception=None, match=None):
    try:
        if exception is None:
            yield
            return

        with pytest.raises(exception, match=match):
            yield
    finally:
        pass
