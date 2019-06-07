# coding: utf-8
"""Sort `ext/readme.md` and `lib/readme.md` by package name."""
import re
from pathlib import Path
from typing import (
    List,
    Match,
)

from .parse import (
    LineParseError,
    PACKAGE_PATTERN,
    STRIP_PATTERN,
)


def _sort_key(line: str) -> str:
    line_copy = line[:]
    line = line.strip()
    line = STRIP_PATTERN.sub('', line)
    columns: List[str] = line.split(' | ')

    match: Match = PACKAGE_PATTERN.match(columns[1])
    if not match:
        raise LineParseError(line_copy, '?', columns[1], 'package')
    return match.group(1).lower()


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
