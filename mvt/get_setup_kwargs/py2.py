# coding: utf-8
"""
Get the keyword arguments passed to the `setup()` function.

[Python 2 ONLY]
This file is called from `get_setup_kwargs.py`.
YOU SHOULD NOT IMPORT THIS FILE OR CALL IT DIRECTLY!
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import imp
import json
import os
import platform
import sys

if sys.version_info[:2] != (2, 7):
    raise Exception('Python version must be 2.7.x')

# Instead of the built-in: `from unittest.mock import patch`
# Requires `mock` to be installed
try:
    from mock import patch
except ImportError:
    raise Exception(
        'Please install `mock` using the following command:\n'
        'py -2 -m pip install mock'
    )

if __package__ is not None:
    from .helpers import add_to_path, with_working_dir
else:
    # This file was NOT run as a module, relative imports are not possible.
    from helpers import add_to_path, with_working_dir


def import_setup_from_path_once(setup_path, as_main=True):
    setup_folder = os.path.abspath(
        os.path.dirname(setup_path) if os.path.isfile(setup_path) else setup_path
    )
    setup_py = os.path.join(setup_folder, 'setup.py')

    # Always load it as with `__name__` set to `'__main__'`
    name = '__main__' if as_main else 'setup'

    with with_working_dir(setup_folder), add_to_path(setup_folder):
        mod = imp.load_source(name, setup_py)

    return mod


def get_setup_kwargs(setup_path, **mocks):
    # type: (Path, Any) -> Mapping[Any, Any]
    sys_platform = mocks.pop('sys_platform', sys.platform)  # type: str
    platform_system = mocks.pop('platform_system', platform.system())  # type: str

    @patch('setuptools.setup')
    @patch('distutils.core.setup')
    @patch.object(sys, 'platform', sys_platform)
    @patch.object(platform, 'system', lambda: platform_system)
    def import_and_get_kwargs(mocked_setup, mocked_du_setup):
        import_setup_from_path_once(setup_path)

        if mocked_setup.called:
            call_args = mocked_setup.call_args
        elif mocked_du_setup.called:
            call_args = mocked_du_setup.call_args
        else:
            raise AssertionError('setup() function was not called!')

        args, kwargs = call_args
        return kwargs

    return import_and_get_kwargs()


input_data = json.load(sys.stdin)
result = get_setup_kwargs(**input_data)
print(
    json.dumps(result, skipkeys=True, default=lambda value: '<<unhashable type>>')
)
