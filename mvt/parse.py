# coding: utf-8
"""Helper functions to parse vendor readme.md files."""

import re
from pathlib import Path
from typing import (
    Iterator,
    Tuple,
    Union,
)

from .models import VendoredLibrary

# Strip code tags to make line pattern simpler, and remove line breaks
STRIP_PATTERN = re.compile(r'</?code>|`|\n$', re.IGNORECASE)
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


class LineParseError(Exception):
    """Raised when unable to parse requirement line."""
    def __init__(self, line: str, line_no: int, part: str = None, section: str = None):
        self.line = line
        self.line_no = line_no
        self.part = part
        self.section = section

    def __str__(self) -> str:
        failed_header = 'Failed to parse {0} on line {1}:'.format(self.section or 'line', self.line_no)
        line_header = 'Full line ({0}):'.format(self.line_no)

        width = 36
        spacer = '=' * (width + 4)

        result = '\n'
        result += spacer + '\n'
        result += '| {0:^{width}} |\n'.format(failed_header, width=width)
        result += spacer + '\n'

        if self.part:
            result += self.part + '\n'
            result += spacer + '\n'
            result += '| {0:^{width}} |\n'.format(line_header, width=width)
            result += spacer + '\n'

        result += self.line + '\n'
        result += spacer

        return result


def parse_requirements(md_path: Path) -> Iterator[ Union[ Tuple[VendoredLibrary, None], Tuple[None, LineParseError] ] ]:
    """Yields `(VendoredLibrary, None)` or `(None, LineParseError)`."""
    if not md_path.exists():
        return

    with md_path.open('r', encoding='utf-8') as file:
        lines = file.readlines()

    for line_no, line in enumerate(lines[3:], 3):
        line = line.strip()
        if not line:
            break

        # Split by columns
        columns = line.split(' | ')
        if len(columns) != 5:
            yield None, LineParseError(line, line_no, section='columns')
            continue
        folder, package, version, usage, notes = columns

        # Folder
        if not folder.strip():
            yield None, LineParseError(line, line_no, folder, 'folder')
            continue
        folder = folder.strip(' *').split(' ')

        # Usage
        if usage:
            usage = STRIP_PATTERN.sub('', usage)
            usage = [pkg.replace('**', '') for pkg in usage.split(', ')]
        else:
            usage = []

        # Split package to: Name, Extras
        match = PACKAGE_PATTERN.match(package)
        if not match:
            yield None, LineParseError(line, line_no, package, 'package')
            continue
        name, extras = match.groups()

        # Extras
        extras = extras.split(',') if extras else []

        # Version
        match = VERSION_PATTERN.match(version)
        if version == '-':
            branch, git, version, url = None, None, None, None
        elif match:
            branch, git, version, url = match.groups()
        else:
            yield None, LineParseError(line, line_no, version, 'version')
            continue

        if git and not version:
            match = URL_COMMIT_PATTERN.search(url)
            if not match:
                yield None, LineParseError(line, line_no, url, 'url')
                continue
            version = match.group(1)

        # Notes, Modules
        split_notes = notes.split('<br>')
        modules: List[str] = []
        notes = []
        for note in split_notes:
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

        # If modules were not specified,
        # the main module has the same name as `VendoredLibrary.package`
        modules = modules or [name]

        result = VendoredLibrary(
            folder=folder,
            name=name,
            extras=extras,
            version=version,
            modules=modules,
            git=bool(git),
            branch=branch,
            url=url,
            usage=usage,
            notes=notes,
        )

        yield result, None


def test(file):
    file_path = Path(file)
    for req, error in parse_requirements(file_path):
        if error:
            print(error)
            continue

        print(f'Parsed package: {req.name}')
