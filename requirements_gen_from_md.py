# Usage - in the same folder with requirements.txt, run:
#   python requirements-gen-from-md.py

from __future__ import print_function
from __future__ import unicode_literals

import io
import re
import sys

# Strip code tags to make line pattern simpler, and remove line breaks
STRIP_PATTERN = re.compile(r'</?code>|`|\n$', re.IGNORECASE)
PACKAGE_PATTERN = re.compile(r'(?:<b>|\*\*)?([\w.-]+)(?:</b>|\*\*)?.*', re.IGNORECASE)
VERSION_PATTERN = re.compile(r'(?:\w+/)?\[(?:(?P<git>[a-f0-9]+)|(?P<version>[\d.]+))\]\((?P<url>[\w.:/-]+)\)', re.IGNORECASE)
NOTES_PATTERN = re.compile(r'(?:(?:Module|File): (?P<module>[\w.]+))?(?:<br>)?(?:Markers: (?P<markers>.+))?(?P<notes>.*)', re.IGNORECASE)

GIT_REPLACE_PATTERN = re.compile(r'/(tree|commits?)/', re.IGNORECASE)


def print_failed(line, line_no, part=None, section=None):
    failed_header = 'Failed to parse {0}:'.format(section or 'line')
    line_header = 'Full line ({0}):'.format(line_no)

    write = sys.stderr.write
    write('================================\n')
    write('| {0:^28} |\n'.format(failed_header))
    write('================================\n')

    if part:
        write(part + '\n')
        write('================================\n')
        write('| {0:^28} |\n'.format(line_header))
        write('================================\n')

    write(line + '\n')
    write('================================\n')

    sys.stderr.flush()

    print('# Failed to a parse a package on line {0},'
          ' please check stderr.'.format(line_no))


def parse_requirements(md_file):
    results = []

    with io.open(md_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line_no, line in enumerate(lines[3:], 3):
        line = line.strip()
        if not line:
            break

        line = STRIP_PATTERN.sub('', line)

        # Split by columns
        columns = line.split(' | ')
        if len(columns) > 6:
            print_failed(line, line_no, section='columns')
            continue
        status, package, version, usage, folder, notes = columns
        if usage:
            usage = [pkg.replace('**', '') for pkg in usage.split(', ')]

        match = PACKAGE_PATTERN.match(package)
        if not match:
            print_failed(line, line_no, package, 'package')
            continue
        package = match.groups()[0]

        match = VERSION_PATTERN.match(version)
        if not match:
            print_failed(line, line_no, version, 'version')
            continue
        git, version, url = match.groups()

        if not folder.strip():
            print_failed(line, line_no, folder, 'folder')
            continue
        folder = folder.strip(' *').split(' ')

        match = NOTES_PATTERN.match(notes)
        if not match:
            print_failed(line, line_no, notes, 'notes')
            continue
        module, markers, notes = match.groups()
        if notes == '-':
            notes = None

        results.append({
            'status': status,
            'package': package,
            'git': bool(git),
            'version': version,
            'url': url,
            'usage': usage,
            'folder': folder,
            'module': module,
            'markers': markers,
            'notes': notes,
        })

    return results


def make_requirement(req):
    markers = ''
    if req['markers']:
        markers = ' ; ' + req['markers']

    if req['git']:
        git_url = GIT_REPLACE_PATTERN.sub('.git@', req['url'])
        return 'git+' + git_url + '#egg=' + (req['module'] or req['package']) + markers
    else:
        return req['package'] + '==' + req['version'] + markers


def main(file='ext/readme.md', output='requirements.txt'):
    requirements = parse_requirements(file)
    # requirements = [r for r in requirements if 'medusa' in r['usage'] or r['git']]
    requirements.sort(key=lambda r: r['package'].lower())

    data = ''.join(make_requirement(req) + '\n' for req in requirements)
    with io.open(output, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(data)


if __name__ == '__main__':
    main()
