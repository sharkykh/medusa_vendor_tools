# coding: utf-8
"""Update already-vendored library by name."""
import sys
from pathlib import Path
from typing import (
    Optional,
    Union,
)

from . import parse
from .__main__ import DEFAULT_EXT_README
from .models import VendoredLibrary
from .vendor import vendor


def update(listfile: Union[Path, str], package: str, cmd: bool) -> None:
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

        if req.name.lower() == package_lower:
            break
    else:
        print(f'Package `{package}` not found.')
        return

    if not req.updatable:
        print(f'Package `{package}` found, but can not be updated.')
        return

    requirement = req.as_update_requirement()
    req_str = f'"{requirement}"' if ' ' in requirement else requirement

    listfile_str = str(listfile)

    if cmd:
        print(f'Vendor command for: `{req.package}`')
        if listfile.samefile(DEFAULT_EXT_README):
            print(f'> mvt vendor {req_str}')
        else:
            listfile_escaped =f'"{listfile_str}"' if ' ' in listfile_str else listfile_str
            print(f'> mvt vendor -f {listfile_escaped} {req_str}')
        return

    print(f'Running vendor command for: `{req.package}`')
    print(f'mvt vendor {req_str}')
    print('\n===========================================\n')
    sys.stdout.flush()

    vendor(
        listfile=str(listfile),
        package=requirement,
        dependents=[],
        py2=False,
        py3=False,
        py6=False,
    )
