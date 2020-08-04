# coding: utf-8
"""Update already-vendored library by name."""
import sys
from pathlib import Path
from typing import Union

from .__main__ import DEFAULT_EXT_README
from .parse import parse_requirements
from .vendor import vendor


def update(listfile: Union[Path, str], package: str, cmd: bool, pre_releases: bool) -> None:
    if not isinstance(listfile, Path):
        listfile = Path(listfile)

    package_lower = package.lower()

    for req, error in parse_requirements(listfile):
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

        cmd_args = []
        if pre_releases:
            cmd_args.append('--pre')
        if not listfile.samefile(DEFAULT_EXT_README):
            cmd_args += [
                '-f',
                f'"{listfile_str}"' if ' ' in listfile_str else listfile_str,
            ]
        cmd_args.append(req_str)

        print(f"> mvt vendor {' '.join(cmd_args)}")
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
        pre_releases=pre_releases,
    )
