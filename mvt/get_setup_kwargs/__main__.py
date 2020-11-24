import argparse
import json
from pathlib import Path

from .. import (
    SUPPORT_PYTHON_2,
    MIN_PYTHON_2,
    MIN_PYTHON_3,
)
from .main import get_setup_kwargs


def main(path):
    results = {
        version: {}
        for version in (
            [MIN_PYTHON_2, MIN_PYTHON_3]
            if SUPPORT_PYTHON_2 else
            [MIN_PYTHON_3]
        )
    }

    if not path.startswith('all:'):
        resolved_path = Path(path).resolve()
        for python_version in results.keys():
            results[python_version] = get_setup_kwargs(
                setup_path=resolved_path,
                discard_unwanted=True,
                python_version=python_version,
            )
        print(json.dumps(results, indent=2))
        return

    for resolved_path in Path(path[4:]).resolve().glob('*'):
        for python_version in results.keys():
            try:
                get_setup_kwargs(
                    setup_path=resolved_path,
                    discard_unwanted=True,
                    python_version=python_version,
                )
            except Exception as error:
                print(f'failed :: {python_version} :: {resolved_path} :: {error!r}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test `get_setup_kwargs`')
    parser.add_argument('package', help='Path to a package source code folder or its `setup.py` file.')
    args = parser.parse_args()

    main(args.package)
