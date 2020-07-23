# coding: utf-8
"""Helper functions to generate vendor readme.md files from JSON spec."""
import json
from pathlib import Path
from typing import List

from .__main__ import DEFAULT_EXT_README
from ._utils import load_requirements
from .models import (
    UsedBy,
    VendoredLibrary,
    VendoredList,
)


def make_list_item(req: VendoredLibrary):
    # Folder
    ext = ('ext2' in req.folder) or ('ext3' in req.folder)
    lib = ('lib2' in req.folder) or ('lib3' in req.folder)
    folder = ' '.join(req.folder)
    if ext or lib:
        folder = f'**{folder}**'

    # Package
    package = f'`{req.package}`'
    if req.main_module_matches_package_name:
        package = f'**{package}**'

    # Version
    if req.version is None:
        version = '-'
    elif not req.git:
        version = f'[{req.version}]({req.url})'
    else:
        branch = f'{req.branch}@' if req.branch else ''
        version = f'[{branch}{req.version[:7]}]({req.url})'
        if '/pymedusa/' in req.url:
            version = f'pymedusa/{version}'

    # Usage
    usage = str(req.usage)

    # Modules
    modules = ', '.join(
        [f'`{req.main_module}`']
        + [f'`{m}`' for m in req.modules[1:]]
    )

    # Notes
    notes = []
    if len(req.modules) > 1:
        notes.append(f'Modules: {modules}')
    elif not req.main_module_matches_package_name:
        if req.is_main_module_file:
            notes.append(f'File: `{req.main_module}`')
        else:
            notes.append(f'Module: `{req.main_module}`')

    notes.extend(req.notes)
    notes = '<br>'.join(notes) if notes else '-'

    return ' | '.join((folder, package, version, usage, notes))


def make_md(requirements: VendoredList) -> List[str]:
    folder = requirements.folder

    # Header
    data = [
        f'## {folder}\n',
        'Folder | Package | Version / Commit | Used By | Notes / Modules\n',
        ':----: | :-----: | :--------------: | :------ | :--------------\n',
    ]

    # Items
    data += [
        make_list_item(req) + '\n'
        for req in requirements
    ]

    # Footer
    data += [
        '\n',
        '#### Notes:\n',
        f'- `{folder}` compatible with Python 2 and Python 3\n',
        f'- `{folder}2` only compatible with Python 2\n',
        f'- `{folder}3` only compatible with Python 3\n',
    ]

    return data


def main(infile: str, outfile: str):
    inpath = Path(infile)
    outpath = Path(outfile)

    if inpath.suffix == '.md':
        requirements = load_requirements(inpath, ignore_errors=True)

        if outpath.samefile(DEFAULT_EXT_README):
            outfile = infile
            outpath = inpath
    else:
        with inpath.open('r', encoding='utf-8') as fh:
            requirements = VendoredList.from_json(json.load(fh))

    data = make_md(requirements)

    with outpath.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(''.join(data))
