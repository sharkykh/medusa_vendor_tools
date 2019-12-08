# coding: utf-8
"""Update already-vendored library by name."""
import sys
from pathlib import Path
from typing import (
    Optional,
    Union,
)

from . import parse
from .vendor import vendor
from .models import VendoredLibrary


def update(listfile: Union[Path, str], package: str) -> None:
    if not isinstance(listfile, Path):
        listfile = Path(listfile)

    package_lower = package.lower()
    generator = parse.parse_requirements(listfile)

    # Types for the loop variables
    req: Optional[VendoredLibrary]
    error: Optional[parse.LineParseError]
    for req, error in generator:
        if error:
            print(str(error), file=sys.stderr)
            continue

        if req.package.lower() == package_lower:
            break
    else:
        print(f'Package `{package}` not found.')
        return

    print(f'Running vendor command for: `{req.package}`')
    requirement = req.as_update_requirement()
    print(f'mvt vendor {requirement}')
    print('\n===========================================\n')
    sys.stdout.flush()

    vendor(
        listfile=str(listfile),
        package=requirement,
        py2=False,
        py3=False,
    )
