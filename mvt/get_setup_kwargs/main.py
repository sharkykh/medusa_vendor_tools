# coding: utf-8
"""Get the keyword arguments passed to the `setup()` function."""

import json
import platform
import subprocess
import sys
from importlib.util import (
    module_from_spec,
    spec_from_file_location,
)
from pathlib import Path
from typing import (
    Any,
    Mapping,
    NamedTuple,
    Tuple,
    Union,
)
from unittest.mock import (
    MagicMock,
    patch,
)

from .helpers import (
    add_to_path,
    with_working_dir,
)

this_file_path = Path(__file__).resolve()


class version_info(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str = 'final'
    serial: int = 0


def get_setup_kwargs(setup_path: Path, discard_unwanted=True, **mocks: Any) -> Mapping[Any, Any]:
    """
    Get the keyword arguments passed to the `setup()` function.

    This function attempts to import `setup.py` and return the data that is passed to the `setup()` function.
    It runs using Python 3 interpreter (current executable).
    If that fails and the version is mocked to look like Python 2, it runs a similar code using a Python 2 interpreter.

    Arguments:

        `setup_path`: Can be either the path to the `setup.py` file, or to the folder that contains it.
        `discard_unwanted`: Removes irrelevant keys from the results (see `discard_unwanted_keys`).

    Keyword arguments:

        `python_version`: Mock the value of `sys.version_info`. Example values: '2.7.10' or (2, 7, 10)
        `sys_platform`: Mock the value of `sys.platform`.
        `platform_system`: Mock the value of `platform.system()`.
    """
    python_version: Union[Tuple[int], str] = mocks.get('python_version', sys.version_info[:3])
    sys_platform: str = mocks.get('sys_platform', sys.platform)
    platform_system: str = mocks.get('platform_system', platform.system())

    if isinstance(python_version, str):
        python_version = tuple(map(int, python_version.split('.')))

    assert len(python_version) == 3, 'Please provide a tuple with at least 3 integers for the version'
    python_version = version_info(*python_version[:3])

    @patch('setuptools.setup')
    @patch('distutils.core.setup')
    @patch.object(sys, 'version_info', python_version)
    @patch.object(sys, 'platform', sys_platform)
    @patch.object(platform, 'system', lambda: platform_system)
    def import_and_get_kwargs(mocked_setup: MagicMock, mocked_du_setup: MagicMock) -> Mapping:
        import_setup_from_path_once(setup_path)

        if mocked_setup.called:
            call_args = mocked_setup.call_args
        elif mocked_du_setup.called:
            call_args = mocked_du_setup.call_args
        else:
            raise AssertionError('setup() function was not called!')

        args, kwargs = call_args
        return kwargs

    data = None
    # Try by mocking a Python 2 environment first.
    try:
        data = import_and_get_kwargs()
    except Exception:
        if python_version.major == 3:
            raise

    if data is None:
        # Try by running a similar function with Python 2
        data = run_in_python2({
            'setup_path': str(setup_path),
            'mocks': mocks,
        })

    return discard_unwanted_keys(data) if discard_unwanted else data


def import_setup_from_path_once(setup_path: Path, as_main=True):
    if setup_path.is_file():
        setup_py: Path = setup_path.with_name('setup.py')
    else:
        setup_py: Path = setup_path / 'setup.py'

    setup_folder = setup_py.parent

    # Load it with `__name__` set to `'__main__'`
    name = '__main__' if as_main else setup_py.name

    with with_working_dir(setup_folder), add_to_path(setup_folder):
        spec = spec_from_file_location(name, setup_py)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)

    return mod


def run_in_python2(data: Mapping) -> Mapping:
    encoded_data = json.dumps(data)

    if __package__ is None:
        path_parts = this_file_path.parts
        mvt_index = path_parts.index('mvt')
        dotted_module = '.'.join(path_parts[slice(mvt_index, -1)])
    else:
        dotted_module = __package__

    dotted_name = f'{dotted_module}.py2'

    # set cwd to the folder containing the 'mvt' package
    cwd = this_file_path
    while cwd.name != '':
        cwd = cwd.parent
        if cwd.name == 'mvt':
            cwd = cwd.parent
            break
    else:
        raise Exception('Unable to find the correct working directory.')

    result = subprocess.run(
        ['py', '-2.7', '-m', dotted_name],
        cwd=cwd,
        encoding='utf-8',
        universal_newlines=True,
        stdout=subprocess.PIPE,
        check=True,
        input=encoded_data,
    )

    data = json.loads(result.stdout)

    return data


def discard_unwanted_keys(data: Mapping) -> Mapping:
    unwanted_keys = [
        'author_email',
        'author',
        'classifiers',
        'cmdclass',
        'description',
        'distclass',
        'download_url',
        'entry_points',
        'ext_modules',
        'include_package_data',
        'keywords',
        'license',
        'long_description_content_type',
        'long_description',
        'maintainer_email',
        'maintainer',
        'project_urls',
        'test_suite',
        'tests_require',
        'url',
        'zip_safe',
    ]

    return {
        key: val for (key, val) in data.items()
        if key not in unwanted_keys
    }
