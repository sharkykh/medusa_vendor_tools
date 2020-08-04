# coding: utf-8
"""Helper functions to parse vendor readme.md files."""

import re
from pathlib import Path
from typing import (
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

from .models import (
    UsedBy,
    VendoredLibrary,
)

PACKAGE_PATTERN = re.compile(
    r'(?:\*\*)?`'
    r'(?P<name>[\w.-]+)'
    r'(?:\[(?P<extras>[\w.,-]+)\])?'
    r'`(?:\*\*)?',
    re.IGNORECASE
)

VERSION_PATTERN = re.compile(
    r'(?:\w+/)?'
    r'\[(?:'
    r'(?:(?P<branch>.+?)@)?(?P<git>commit|[a-f0-9]+)'
    r'|(?P<version>.+?)'
    r')\]'
    r'\((?P<url>[\w.:/-]+)\)',
    re.IGNORECASE
)
URL_COMMIT_PATTERN = re.compile(r'/([a-f0-9]{40})/?', re.IGNORECASE)


class ParseFailed(Exception):
    """Parsing of a section failed."""


def _split_columns(line: str) -> List[str]:
    """Split a line into a list of columns."""
    columns: List[str] = line.split(' | ')
    if len(columns) != 5:
        raise ParseFailed

    return columns


def _parse_folder(raw_folder: str) -> List[str]:
    """Parse raw folder into folders list."""
    if not raw_folder.strip():
        raise ParseFailed

    return raw_folder.strip(' *').split(' ')


def _parse_package(raw_package: str) -> Tuple[str, List[str]]:
    """Parse raw package into package name and package extras."""
    # Split package
    match = PACKAGE_PATTERN.match(raw_package)
    if not match:
        raise ParseFailed
    name, raw_extras = match.groups()

    # Extras
    extras = raw_extras.split(',') if raw_extras else []

    return name, extras


def _parse_version(raw_version: str) -> Tuple[Optional[str], Optional[str], bool, Optional[str]]:
    """Parse raw version into version, url, [is_]git and branch name."""
    if raw_version == '-':
        # version, url, git, branch
        return None, None, False, None

    # Split version
    match = VERSION_PATTERN.match(raw_version)
    if not match:
        raise ParseFailed
    branch, git, version, url = match.groups()

    return version, url, bool(git), branch


def _parse_url_for_commit_hash(url: str) -> str:
    """Parse url for a git commit hash."""
    match = URL_COMMIT_PATTERN.search(url)
    if not match:
        raise ParseFailed

    return match.group(1)


def _parse_notes(raw_notes: str) -> Tuple[List[str], List[str]]:
    """Parse raw notes into notes list and modules list."""
    modules: List[str] = []
    notes: List[str] = []
    for note in raw_notes.split('<br>'):
        if note.startswith(('File: ', 'Module: ', 'Modules: ')):
            start = note.index(': ') + 2
            modules = [
                m.strip('`') for m
                in note[start:].split(', ')
            ]
            continue
        if note == '-':
            continue
        notes.append(note)

    return notes, modules


class EndOfList(Exception):
    """Reached end of list."""


class LineParseError(Exception):
    """Raised when unable to parse a vendored library line."""
    def __init__(self, line: str, line_no: int, section: str, part: str = None):
        self.line = line
        self.line_no = line_no
        self.section = section
        self.part = part

    def __str__(self) -> str:
        if self.line_no:
            failed_header = f'Failed to parse {self.section} on line {self.line_no}:'
            line_header = f'Full line ({self.line_no}):'
        else:
            failed_header = f'Failed to parse {self.section}:'
            line_header = 'Full line:'

        width = 36
        spacer = '=' * (width + 4)

        result = '\n'
        result += f'{spacer}\n'
        result += f'| {failed_header.center(width)} |\n'
        result += f'{spacer}\n'

        if self.part:
            result += f'{self.part}\n'
            result += f'{spacer}\n'
            result += f'| {line_header.center(width)} |\n'
            result += f'{spacer}\n'

        result += f'{self.line}\n'
        result += spacer

        return result


LineResultType = Union[Tuple[VendoredLibrary, None], Tuple[None, LineParseError]]


def _parse_line(line: str, line_no: int) -> LineResultType:
    """Parse raw line into a Vendored Library object."""
    line = line.strip('\r\n')
    if not line:
        raise EndOfList

    # Split by columns
    try:
        raw_folder, raw_package, raw_version, raw_usage, raw_notes = _split_columns(line)
    except ParseFailed:
        return None, LineParseError(line, line_no, 'columns')

    # Folder
    try:
        folder = _parse_folder(raw_folder)
    except ParseFailed:
        return None, LineParseError(line, line_no, 'folder', raw_folder)

    # Usage
    usage = UsedBy(raw_usage)

    # Split package to: Name, Extras
    try:
        name, extras = _parse_package(raw_package)
    except ParseFailed:
        return None, LineParseError(line, line_no, 'package', raw_package)

    # Split version to: Version, URL, Git, Branch
    try:
        version, url, git, branch = _parse_version(raw_version)
    except ParseFailed:
        return None, LineParseError(line, line_no, 'version', raw_version)

    if git and not version:
        try:
            version = _parse_url_for_commit_hash(url)
        except ParseFailed:
            return None, LineParseError(line, line_no, 'url', url)

    # Split notes to: Notes, Modules
    notes, modules = _parse_notes(raw_notes)

    # If modules were not specified,
    # the main module has the same name as `VendoredLibrary.package`
    modules = modules or [name]

    result = VendoredLibrary(
        folder=folder,
        name=name,
        extras=extras,
        version=version,
        modules=modules,
        git=git,
        branch=branch,
        url=url,
        usage=usage,
        notes=notes,
    )

    return result, None


def parse_requirements(md_path: Path) -> Iterable[LineResultType]:
    """Yields `(VendoredLibrary, None)` or `(None, LineParseError)`."""
    if not md_path.is_file():
        return  # pragma: no cover

    with md_path.open('r', encoding='utf-8') as file:
        lines = file.readlines()

    line_no: int
    line: str
    for line_no, line in enumerate(lines[3:], 3):
        try:
            yield _parse_line(line=line, line_no=line_no)
        except EndOfList:
            break
    return  # pragma: no cover


def test(file):
    file_path = Path(file)
    for req, error in parse_requirements(file_path):
        if error:
            print(error)
            continue

        print(f'Parsed package: {req.name}')
