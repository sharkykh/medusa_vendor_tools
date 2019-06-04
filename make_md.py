# coding: utf-8
"""
Helper functions to generate vendor readme.md files from JSON spec
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import io
import json
import re


def wrap(s, left, right=None):
    if right is None:
        right = left
    return '%s%s%s' % (left, s, right)


def wrapTag(s, t):
    return wrap(s, '<%s>' % t, '</%s>' % t)


def make_packages_pattern(requirements):
    packages = map(lambda r: re.escape(r['package']), requirements)
    return re.compile('(?<!`)(\b)?(' + '|'.join(packages) + ')(\b)?(?!`)')


def make_list_item(req, packages_pattern):
    # Folder
    ext = ('ext2' in req['folder']) or ('ext3' in req['folder'])
    lib = ('lib2' in req['folder']) or ('lib3' in req['folder'])
    folder = ' '.join(req['folder'])
    if ext or lib:
        folder = '**' + folder + '**'

    # Package
    package = wrap(req['package'], '`')
    mod_in_pkg = req['modules'][0].endswith('.py') and req['modules'][0][:-3] == req['package']
    if mod_in_pkg:
        package = wrapTag(wrapTag(req['modules'][0][:-3], 'b') + '.py', 'code')
    if req['modules'][1:]:
        if not mod_in_pkg:
            package = wrap(package, '**')
        package += '<br>' + '<br>'.join('`%s`' % m for m in req['modules'][1:])

    # Version
    if not req['git']:
        version = '[{0}]({1})'.format(req['version'], req['url'])
    else:
        version = '[{0}]({1})'.format(req['version'][:7], req['url'])
        if '/pymedusa/' in req['url']:
            version = 'pymedusa/' + version

    # Usage
    usage = []
    for i, u in enumerate(req['usage']):
        if '?????' in u:
            usage.append(u)
            continue
        if ' ' in u:
            ex = u.split(' ', 1)
            t = '**`%s`** %s' if ex[0] == 'medusa' else '`%s` %s'
            wrapped = packages_pattern.sub(r'\1' + wrap(r'\2', '`') + r'\3', ex[1])
            r = t % (ex[0], wrapped)
        else:
            t = '**`%s`**' if u == 'medusa' else '`%s`'
            r = t % u

        if i == 0 and 'medusa' in u:
            usage.insert(0, r)
        else:
            usage.append(r)
    usage = ', '.join(usage)

    # Notes
    notes = []
    if req['modules'][0].endswith('.py'):
        if req['modules'][0][:-3] != req['package']:
            notes.append('File: `%s`' % req['modules'][0])
    else:
        if req['modules'][0] != req['package']:
            notes.append('Module: `%s`' % req['modules'][0])

    if req['notes']:
        notes.extend(packages_pattern.sub(wrap(r'\2', r'\1`', r'`\3'), note) for note in req['notes'])

    notes = '<br>'.join(notes) if notes else '-'

    return ' | '.join((folder, package, version, usage, notes))


def make_md(requirements):
    requirements.sort(key=lambda r: r['package'].lower())

    folder = requirements[0]['folder'][0].rstrip('23')

    data = []

    # Header
    data.append('## %s\n' % folder)
    data.append(' Folder  |  Package  |  Version / Commit  | Usage | Notes\n')
    data.append(':------: | :-------: | :----------------: | :---- | :----\n')

    # Items
    data += [make_list_item(req, make_packages_pattern(requirements)) + '\n' for req in requirements]

    # Footer
    data.append('\n')
    data.append('Notes:\n')
    data.append(' - `%s` compatible with python2 and python3\n' % folder)
    data.append(' - `%s2` only compatible with python2\n' % folder)
    data.append(' - `%s3` only compatible with python3\n' % folder)

    return data


def main(infile, outfile):
    with io.open(infile, 'r', encoding='utf-8') as fh:
        requirements = json.load(fh)

    data = make_md(requirements)

    with io.open(outfile, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(''.join(data))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate `ext/readme.md` from JSON')
    parser.add_argument('-i', '--infile', default='requirements.json', required=False,
                        help='JSON input file. Defaults to `requirements.json`')
    parser.add_argument('-o', '--outfile', default='ext/readme.md', required=False,
                        help='Markdown output file. Defaults to `ext/readme.md`')

    args = parser.parse_args()

    main(**args.__dict__)
