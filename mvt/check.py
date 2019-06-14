# coding: utf-8
"""Check vendor folders using `ext/readme.md` or `lib/readme.md`."""
import sys
from pathlib import Path
from typing import (
    List,
    Optional,
    Union,
)

from . import parse
from .models import VendoredLibrary


def check(inpath: Union[Path, str]) -> None:
    if not isinstance(inpath, Path):
        inpath = Path(inpath)

    root = inpath.parent.parent.resolve()

    all_found = True
    generator = parse.parse_requirements(inpath)

    # Types for the loop variables
    req: Optional[VendoredLibrary]
    error: Optional[parse.LineParseError]
    for req, error in generator:
        if error:
            print(str(error), file=sys.stderr)
            continue

        for module in req.modules:
            # backports/package.py [OR] backports.module
            split_count = (module.count('.') - 1) if module.endswith('.py') else -1
            parts: List[str] = module.split('.', split_count)

            module_paths: List[Path] = [root.joinpath(f, *parts) for f in req.folder]
            rel_module_paths: List[str] = [str(p.relative_to(root).as_posix()) for p in module_paths]

            if not all(p.exists() for p in module_paths):
                print(f'XX {module} !!  NOT FOUND IN: {rel_module_paths}')
                all_found = False
            else:
                pass  # print(f'VV {module} {rel_module_paths}')

    if all_found:
        print('Done.')
