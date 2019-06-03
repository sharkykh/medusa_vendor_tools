#!/usr/bin/env python3
# coding: utf-8
"""
Check vendor folders using `ext/readme.md`.

Usage - in the same folder with `start.py`, run:
  python check.py
    or
  ./check.py
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import sys
from pathlib import Path

from parse_md import (
    LineParseError,
    parse_requirements,
)

DEFAULT_INFILE = 'ext/readme.md'


def main(infile):
    root = Path(infile).parent.parent.absolute()

    all_found = True
    iterator = parse_requirements(infile)
    while True:
        try:
            req, error = next(iterator)
        except StopIteration:
            break

        if error:
            if isinstance(error, LineParseError):
                print(str(error), file=sys.stderr)
                continue
            else:
                raise error

        for module in req['modules']:
            # backports/package.py [OR] backports.module
            split_count = (module.count('.') - 1) if module.endswith('.py') else -1
            parts = module.split('.', split_count)

            module_paths = [root.joinpath(f, *parts) for f in req['folder']]
            rel_module_paths = [str(p.relative_to(root).as_posix()) for p in module_paths]

            if not all(p.exists() for p in module_paths):
                print('XX', module, '!!  NOT FOUND IN:', rel_module_paths)
                all_found = False
            else:
                pass  # print('VV', module, rel_module_paths)

    if all_found:
        print('Done.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Check vendor folders using `ext/readme.md`')
    parser.add_argument('-i', '--infile', default=DEFAULT_INFILE, required=False,
                        help='Input file. Defaults to `ext/readme.md`')

    args = parser.parse_args()

    main(
        infile=args.infile,
    )
