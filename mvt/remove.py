# coding: utf-8
"""Remove vendored library by name."""
import shutil
from pathlib import Path

from ._utils import (
    load_requirements,
    package_module_paths,
    remove_all,
)
from .gen_req import generate_requirements
from .make_md import make_md
from .models import VendoredLibrary


def remove(listfile: str, package: str) -> None:
    listpath = Path(listfile).resolve()
    root = listpath.parent.parent

    if not listpath.exists():
        print(f'Aborting: `{listfile}` does not exist')
        return

    # Get requirements from list, try to find the package we're vendoring right now
    requirements, req_idx = load_requirements(listpath, package)
    if req_idx is None:
        print(f'Package `{package}` not found')
        return

    req: VendoredLibrary = requirements[req_idx]
    target = listpath.parent.name  # `ext` or `lib`
    name_lower = req.name.lower()

    print(f'Starting removal of `{req.name}`')

    requirements.pop(req_idx)

    print()
    print('++++++++++++++++++++++')
    print('+ Dependency updates +')
    print('+--------------------+')

    # Update dependencies of `req`
    unused = []  # Possibly unused
    still_used = []  # Possibly still being used

    r: VendoredLibrary
    for r in requirements:
        if r == req:
            continue

        # Warn about packages using `req`:
        if r in req.usage:
            still_used.append(r)

        # if `r` used by `req`
        # remove `req.name` from `r.usage`
        if req not in r.usage:
            continue

        print(f'Removing `{req.name}` usage from dependency `{r.name}`')
        r.usage.remove(req)

        if not r.usage:
            unused.append(r)

    # Display warnings
    for r in still_used:
        print(f'Warning: `{req.name}` possibly still being used by `{r.name}`')
    for r in unused:
        print(f'Possibly unused: `{r.name}`, consider removing')

    print('\n======================\n')

    # Remove vendored folder(s)/file(s) using info from `[target]/readme.md`
    package_modules = package_module_paths(req, root)
    modules_csv = ', '.join(map(str, package_modules))
    print(f'Removing: [{modules_csv}]')
    try:
        remove_all(package_modules)
    except OSError:
        pass

    readme_name = '/'.join(listpath.parts[-2:])
    print(f'Updating {readme_name}')

    md_data = make_md(requirements)

    with listpath.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(''.join(md_data))

    if target == 'ext':
        print('Updating requirements.txt')
        reqs_file = root / 'requirements.txt'
        generate_requirements(
            infile=str(listpath),
            outfile=str(reqs_file),
            all_packages=False,
            json_output=False,
        )

    print('Done!')

