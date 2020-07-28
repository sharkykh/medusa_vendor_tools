# coding: utf-8
"""Sort `ext/readme.md` and `lib/readme.md` by package name."""
from pathlib import Path
from typing import List

from .parse import (
    _parse_package,
    _split_columns,
    LineParseError,
    ParseFailed,
)


def _sort_key(line: str) -> str:
    try:
        _, raw_package, _, _, _ = _split_columns(line.strip())
    except ParseFailed:
        raise LineParseError(line, -1, section='columns')

    try:
        name, _ = _parse_package(raw_package)
    except ParseFailed:
        raise LineParseError(line, -1, raw_package, 'package')

    return name.lower()


def sort_md(file: str) -> None:
    filepath = Path(file)
    with filepath.open('r', encoding='utf-8', newline='\n') as fh:
        orig: List[str] = fh.readlines()

    # Find the end of the list
    line_no = -1
    line = orig[line_no]
    while line.strip():
        line_no -= 1
        line = orig[line_no]
        continue

    header: List[str] = orig[slice(None, 3)]
    new: List[str] = sorted(orig[slice(3, line_no)], key=_sort_key)
    footer: List[str] = orig[slice(line_no, None)]

    with filepath.open('w', encoding='utf-8', newline='\n') as fh:
        fh.writelines(header + new + footer)
