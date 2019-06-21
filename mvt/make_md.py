# coding: utf-8
"""Helper functions to generate vendor readme.md files from JSON spec."""
import json
import re
from pathlib import Path
from typing import (
    AnyStr,
    List,
    Mapping,
    Pattern,
)

from .models import VendoredLibrary


def make_packages_pattern(requirements: List[VendoredLibrary]) -> Pattern[AnyStr]:
    packages = map(lambda r: re.escape(r.package), requirements)
    return re.compile('(?<!`)(\b)?(' + '|'.join(packages) + ')(\b)?(?!`)')


def make_list_item(req: VendoredLibrary, packages_pattern: Pattern[AnyStr]):
    # Folder
    ext = ('ext2' in req.folder) or ('ext3' in req.folder)
    lib = ('lib2' in req.folder) or ('lib3' in req.folder)
    folder = ' '.join(req.folder)
    if ext or lib:
        folder = f'**{folder}**'

    # Package
    package = f'`{req.package}`'
    mod_file_in_pkg = req.modules[0].endswith('.py') and req.modules[0][:-3] == req.package
    if mod_file_in_pkg:
        package = f'<code><b>{req.modules[0][:-3]}</b>.py</code>'
    if req.modules[1:]:
        if not mod_file_in_pkg:
            package = f'**{package}**'
        package += '<br>' + '<br>'.join(f'`{m}`' for m in req.modules[1:])

    # Version
    if not req.git:
        version = f'[{req.version}]({req.url})'
    else:
        version = f'[{req.version[:7]}]({req.url})'
        if '/pymedusa/' in req.url:
            version = f'pymedusa/{version}'

    # Usage
    usage = []
    usage_last = []
    for i, u in enumerate(sorted(req.usage, key=str.lower)):
        if '?????' in u:
            usage_last.append(u)
            continue
        if ' ' in u:
            parts = u.split(' ', 1)
            wrapped = packages_pattern.sub(r'\1`\2`\3', parts[1])
            t = '**`{name}`** {extra}' if parts[0] == 'medusa' else '`{name}` {extra}'
            r = t.format(name=parts[0], extra=wrapped)
        else:
            t = '**`{name}`**' if u == 'medusa' else '`{name}`'
            r = t.format(name=u)

        # if i == 0 and 'medusa' in u:
        if 'medusa' in u:
            usage.insert(0, r)
        else:
            usage.append(r)

    usage = ', '.join(usage + usage_last)

    # Notes
    notes = []
    if not mod_file_in_pkg:
        if req.modules[0].endswith('.py') and req.modules[0][:-3] != req.package:
            notes.append(f'File: `{req.modules[0]}`')
        elif req.modules[0] != req.package:
            notes.append(f'Module: `{req.modules[0]}`')

    if req.notes:
        notes.extend(packages_pattern.sub(r'\1`\2`\3', note) for note in req.notes)

    notes = '<br>'.join(notes) if notes else '-'

    return ' | '.join((folder, package, version, usage, notes))


def make_md(requirements: List[VendoredLibrary]):
    requirements.sort(key=lambda req: req.package.lower())

    folder = requirements[0].folder[0].rstrip('23')
    packages_pattern = make_packages_pattern(requirements)

    data = []

    # Header
    data.append(f'## {folder}\n')
    data.append(' Folder  |  Package  |  Version / Commit  | Usage | Notes\n')
    data.append(':------: | :-------: | :----------------: | :---- | :----\n')

    # Items
    data += [
        make_list_item(req, packages_pattern) + '\n'
        for req in requirements
    ]

    # Footer
    data.append('\n')
    data.append('Notes:\n')
    data.append(f' - `{folder}` compatible with python2 and python3\n')
    data.append(f' - `{folder}2` only compatible with python2\n')
    data.append(f' - `{folder}3` only compatible with python3\n')

    return data


def main(infile: str, outfile: str):
    inpath = Path(infile)
    with inpath.open('r', encoding='utf-8') as fh:
        original = json.load(fh)

    requirements: List[VendoredLibrary] = [VendoredLibrary(**req) for req in original]
    data = make_md(requirements)

    outpath = Path(outfile)
    with outpath.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(''.join(data))