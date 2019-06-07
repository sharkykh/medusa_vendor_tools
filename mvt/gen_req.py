# coding: utf-8
"""Generate `requirements.txt` from `ext/readme.md`."""

import sys
from pathlib import Path

from .models import VendoredLibrary
from .parse import (
    LineParseError,
    parse_requirements,
)


def generate_requirements(infile: str, outfile: str, all_packages: bool = False, json_output: bool = False) -> None:
    inpath = Path(infile)
    outpath = Path(outfile)

    requirements = []
    req: VendoredLibrary
    for req, error in parse_requirements(inpath):
        if error:
            print(str(error), file=sys.stderr)
            continue

        if not all_packages and not (req.used_by_medusa or req.git):
            continue

        requirements.append(req)

    requirements.sort(key=lambda r: r.package.lower())

    if json_output:
        import json
        data = '[\n  ' + ',\n  '.join(json.dumps(req.json()) for req in requirements) + '\n]\n'
    else:
        data = ''.join(req.as_requirement() + '\n' for req in requirements)

    with outpath.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(data)
