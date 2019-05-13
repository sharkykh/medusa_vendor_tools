#!/usr/bin/env python3
#!/usr/bin/env python
# coding: utf-8
"""
Generate `requirements.txt` from `ext/readme.md`.

Usage - in the same folder with `requirements.txt`, run:
  python gen_requirements.py
    or
  ./gen_requirements.py
"""

from __future__ import print_function
from __future__ import unicode_literals

import io
import sys

from parse_md import (
    GIT_REPLACE_PATTERN,
    LineParseError,
    parse_requirements,
)

DEFAULT_INFILE = 'ext/readme.md'
DEFAULT_OUTFILE = 'requirements.txt'


def make_requirement(req):
    markers = ''
    # Exclusive-OR: Either '<dir>2' or '<dir>3', but not both
    ext = ('ext2' in req['folder']) != ('ext3' in req['folder'])
    lib = ('lib2' in req['folder']) != ('lib3' in req['folder'])
    if len(req['folder']) == 1 and (ext or lib):
        major_v = req['folder'][0][-1]
        markers = " ; python_version == '%s.*'" % major_v

    if req['git']:
        if 'github.com' in req['url']:
            # https://codeload.github.com/:org/:repo/tar.gz/:commit-ish
            git_url = GIT_REPLACE_PATTERN.sub('/tar.gz/', req['url'])
            git_url = git_url.replace('https://github.com/', 'https://codeload.github.com/')
        else:
            git_url = 'git+' + GIT_REPLACE_PATTERN.sub('.git@', req['url'])
        return git_url + '#egg=' + (req['module'] or req['package']) + markers
    else:
        return req['package'] + '==' + req['version'] + markers


def main(infile, outfile, all_packages=False, json_output=False):
    requirements = []
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

        if not all_packages and not (any('medusa' in u for u in req['usage']) or req['git']):
            continue

        requirements.append(req)

    requirements.sort(key=lambda r: r['package'].lower())

    if json_output:
        import json
        data = '[\n  ' + ',\n  '.join(json.dumps(req, sort_keys=True) for req in requirements) + '\n]\n'
    else:
        data = ''.join(make_requirement(req) + '\n' for req in requirements)

    with io.open(outfile, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(data)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate `requirements.txt` from `ext/readme.md`')
    parser.add_argument('-i', '--infile', default=DEFAULT_INFILE, required=False,
                        help='Input file. Defaults to `ext/readme.md`')
    parser.add_argument('-o', '--outfile', default=DEFAULT_OUTFILE, required=False,
                        help='Output file. Defaults to `requirements.txt` (with `--json`: `requirements.json`)')
    parser.add_argument('-a', '--all-packages', action='store_true', default=False,
                        help='List all packages, not just those used by Medusa')
    parser.add_argument('-j', '--json', action='store_true', default=False,
                        help='export as JSON to `requirements.json` (or OUTFILE)')

    args = parser.parse_args()

    if args.json and args.outfile == DEFAULT_OUTFILE and args.outfile.endswith('.txt'):
        args.outfile = args.outfile[:-3] + 'json'

    main(
        infile=args.infile,
        outfile=args.outfile,
        all_packages=args.all_packages,
        json_output=args.json,
    )
