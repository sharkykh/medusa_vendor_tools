# coding: utf-8
"""Helper functions to generate vendor readme.md files from JSON spec."""
import json
from pathlib import Path

from .__main__ import DEFAULT_EXT_README
from ._utils import load_requirements
from .models import VendoredList


def make_md(requirements: VendoredList) -> str:
    folder = requirements.folder

    # Header
    data = [
        f'## {folder}',
        'Folder | Package | Version / Commit | Used By | Notes / Modules',
        ':----: | :-----: | :--------------: | :------ | :--------------',
    ]

    # Items
    data += [
        req.as_list_item()
        for req in requirements
    ]

    # Footer
    data += [
        '',
        '#### Notes:',
        f'- `{folder}` compatible with Python 2 and Python 3',
        f'- `{folder}2` only compatible with Python 2',
        f'- `{folder}3` only compatible with Python 3',
    ]

    return '\n'.join(data) + '\n'


def main(infile: str, outfile: str):
    inpath = Path(infile)
    outpath = Path(outfile)

    if inpath.suffix == '.md':
        requirements = load_requirements(inpath, ignore_errors=True)

        if outpath == Path(DEFAULT_EXT_README):
            outfile = infile
            outpath = inpath
    else:
        with inpath.open('r', encoding='utf-8') as fh:
            requirements = VendoredList.from_json(json.load(fh))

    data = make_md(requirements)

    with outpath.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(data)
