# coding: utf-8
"""Remove vendored library by name."""
from pathlib import Path

from . import EXT_FOLDER
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
    requirements = load_requirements(listpath)
    if package not in requirements:
        print(f'Package `{package}` not found')
        return

    req: VendoredLibrary = requirements[package]
    target = requirements.folder or listpath.parent.name  # `ext` or `lib`

    print(f'Starting removal of `{req.name}`')

    print()
    print('++++++++++++++++++++++')
    print('+ Dependency updates +')
    print('+--------------------+')

    # Update dependencies of `req`
    unused = []  # Possibly unused
    still_used = []  # Possibly still being used

    dep: VendoredLibrary
    for dep in requirements:
        if dep == req:
            continue

        # Warn about packages using `req`:
        if dep in req.usage:
            still_used.append(dep)

        # if `dep` used by `req`
        # remove `req.name` from `dep.usage`
        if req not in dep.usage:
            continue

        print(f'Removing `{req.name}` usage from dependency `{dep.name}`')
        dep.usage.remove(req)

        if not dep.usage:
            unused.append(dep)

    # Display warnings
    for dep in still_used:
        print(f'Warning: `{req.name}` possibly still being used by `{dep.name}`')
    for dep in unused:
        print(f'Possibly unused: `{dep.name}`, consider removing')

    print('\n======================\n')

    # Remove vendored folder(s)/file(s) using info from `[target]/readme.md`
    package_modules = package_module_paths(req, root)
    modules_csv = ', '.join(map(str, package_modules))
    print(f'Removing: [{modules_csv}]')
    try:
        remove_all(package_modules)
    except OSError:
        pass

    # Remove from list
    requirements.remove(req)

    readme_name = '/'.join(listpath.parts[-2:])
    print(f'Updating {readme_name}')

    md_data = make_md(requirements)

    with listpath.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(md_data)

    if target == EXT_FOLDER:
        print('Updating requirements.txt')
        reqs_file = root / 'requirements.txt'
        generate_requirements(
            infile=str(listpath),
            outfile=str(reqs_file),
            all_packages=False,
            json_output=False,
        )

    print('Done!')
