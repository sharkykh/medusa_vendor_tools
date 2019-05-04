#!/usr/bin/env python3
#!/usr/bin/env python
# coding: utf-8
"""
Sort `ext/readme.md` and `lib/readme.md` by package name.

Usage - in the same folder with `start.py`, run:
  python sort_md.py
    or
  ./sort_md.py
"""

import io
import re

# Taken from `requirements_gen_from_md.py`
# Strip code tags to make line pattern simpler, and remove line breaks
STRIP_PATTERN = re.compile(r'</?code>|`|\n$', re.IGNORECASE)
PACKAGE_PATTERN = re.compile(r'(?:<b>|\*\*)?([\w.-]+)(?:</b>|\*\*)?.*', re.IGNORECASE)

extfile = 'ext/readme.md'
libfile = 'lib/readme.md'


def sort_md(file):
    with io.open(file, 'r', encoding='utf-8', newline='\n') as fh:
        orig = fh.readlines()

    line_no = -1
    line = orig[line_no]
    while line.strip():
        line_no -= 1
        line = orig[line_no]
        continue

    def sort_key(line):
        line = line.strip()
        line = STRIP_PATTERN.sub('', line)
        columns = line.split(' | ')

        match = PACKAGE_PATTERN.match(columns[1])
        if not match:
            raise Exception('fail @', line)
        return match.group(1).lower()

    header = orig[slice(None, 3)]
    new = sorted(orig[slice(3, line_no)], key=sort_key)
    footer = orig[slice(line_no, None)]

    with io.open(file, 'w', encoding='utf-8', newline='\n') as fh:
        fh.writelines(header + new + footer)


if __name__ == '__main__':
    sort_md(extfile)
    sort_md(libfile)
