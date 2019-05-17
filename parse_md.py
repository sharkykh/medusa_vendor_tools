# coding: utf-8
"""
Helper functions to parse vendor readme.md files
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import io
import re

from collections import OrderedDict

# Strip code tags to make line pattern simpler, and remove line breaks
STRIP_PATTERN = re.compile(r'</?code>|`|\n$', re.IGNORECASE)
PACKAGE_PATTERN = re.compile(r'(?:<b>|\*\*)?([\w.-]+)(?:</b>|\*\*)?(.*)', re.IGNORECASE)
VERSION_PATTERN = re.compile(r'(?:\w+/)?\[(?:(?P<git>commit|[a-f0-9]+)|(?P<version>[\d.]+))\]\((?P<url>[\w.:/-]+)\)', re.IGNORECASE)
URL_COMMIT_PATTERN = re.compile(r'/([a-f0-9]{40})/?', re.IGNORECASE)


class LineParseError(Exception):
    """Raised when unable to parse requirement line."""
    def __init__(self, line, line_no, part=None, section=None):
        self.line = line
        self.line_no = line_no
        self.part = part
        self.section = section

    def __str__(self):
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


def parse_requirements(md_file):
    with io.open(md_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line_no, line in enumerate(lines[3:], 3):
        line = line.strip()
        if not line:
            break

        line = STRIP_PATTERN.sub('', line)

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
            usage = [pkg.replace('**', '') for pkg in usage.split(', ')]

        # Package / Extra Modules
        match = PACKAGE_PATTERN.match(package)
        if not match:
            yield None, LineParseError(line, line_no, package, 'package')
            continue
        package, extra_modules = match.groups()

        # Version
        match = VERSION_PATTERN.match(version)
        if not match:
            yield None, LineParseError(line, line_no, version, 'version')
            continue
        git, version, url = match.groups()

        if git and not version:
            match = URL_COMMIT_PATTERN.search(url)
            if not match:
                yield None, LineParseError(line, line_no, url, 'url')
                continue
            version = match.group(1)

        # Notes
        split_notes = notes.split('<br>')
        module = ''
        notes = []
        for note in split_notes:
            if note.startswith(('Module: ', 'File: ')):
                module = note.split(': ', 1)[1]
                continue
            if note == '-':
                continue
            notes.append(note)

        extra_modules = extra_modules.split('<br>')
        first_item = extra_modules.pop(0)  # Could be an empty string
        if not module and first_item:  # `.py`
            module = package + first_item
        modules = [module or package] + extra_modules

        result = OrderedDict()
        result['folder'] = folder
        result['package'] = package
        result['version'] = version
        result['modules'] = modules
        result['git'] = bool(git)
        result['url'] = url
        result['usage'] = usage
        result['notes'] = notes

        yield result, None
