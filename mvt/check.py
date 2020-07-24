# coding: utf-8
"""Check vendor folders using `ext/readme.md` or `lib/readme.md`."""
import sys
from pathlib import Path
from typing import (
    List,
    Optional,
    Union,
)

from .parse import parse_requirements


def check_modules(inpath: Union[Path, str]) -> None:
    if not isinstance(inpath, Path):
        inpath = Path(inpath)

    root = inpath.parent.parent.resolve()

    all_found = True

    for req, error in parse_requirements(inpath):
        if error:
            print(str(error), file=sys.stderr)
            continue

        results: List[str] = []
        for module in req.modules:
            module_paths: List[Path] = [root.joinpath(f, module) for f in req.folder]
            rel_module_paths: List[str] = [p.relative_to(root).as_posix() for p in module_paths]

            if not all(p.exists() for p in module_paths):
                results.append(f'  XX {module} !!  NOT FOUND IN: {rel_module_paths}')
                all_found = False
            # else:
            #     results.append(f'  VV {module} => {rel_module_paths}')

        if results:
            print(f'{req.name}')
            print('\n'.join(results))

    if all_found:
        print('Done.')
