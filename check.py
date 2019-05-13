#!/usr/bin/env python3
#!/usr/bin/env python
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

import os
import sys

from parse_md import (
    LineParseError,
    parse_requirements,
)

DEFAULT_INFILE = 'ext/readme.md'


def main(infile):
    root = os.path.abspath(
        os.path.join(
            os.path.dirname(infile),
            '..',
        )
    )

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
            split_count = (module.count('.') - 1) if module.endswith('.py') else -1
            parts = module.split('.', split_count)
            module_paths = [os.path.join(root, f, *parts) for f in req['folder']]
            if not all(os.path.exists(p) for p in module_paths):
                print('❌ ', module, '⚠  NOT FOUND IN:', module_paths)
            # else:
            #     print('✅ ', module, module_paths)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Check vendor folders using `ext/readme.md`')
    parser.add_argument('-i', '--infile', default=DEFAULT_INFILE, required=False,
                        help='Input file. Defaults to `ext/readme.md`')

    args = parser.parse_args()

    main(
        infile=args.infile,
    )
