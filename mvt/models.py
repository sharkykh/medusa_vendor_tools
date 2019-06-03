# coding: utf-8

import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import List


@dataclass
class VendoredLibrary:
    """Represents a vendored library."""
    folder: List[str]
    package: str
    version: str
    modules: List[str]
    git: bool
    url: str
    usage: List[str]
    notes: List[str]

    GIT_REPLACE_PATTERN = re.compile(r'/(?:tree|commits?)/', re.IGNORECASE)

    def json(self) -> OrderedDict:
        return OrderedDict([
            ('folder', self.folder),
            ('package', self.package),
            ('version', self.version),
            ('modules', self.modules),
            ('git', self.git),
            ('url', self.url),
            ('usage', self.usage),
            ('notes', self.notes),
        ])

    def as_requirement(self):
        if self.git:
            if 'github.com' in self.url:
                # https://codeload.github.com/:org/:repo/tar.gz/:commit-ish
                git_url = self.GIT_REPLACE_PATTERN.sub('/tar.gz/', self.url)
                git_url = git_url.replace('https://github.com/', 'https://codeload.github.com/')
            else:
                git_url = 'git+' + GIT_REPLACE_PATTERN.sub('.git@', self.url)
            return git_url + '#egg=' + self.package + self.markers
        else:
            return self.package + '==' + self.version + self.markers

    @property
    def markers(self):
        markers = ''
        # Exclusive-OR: Either '<dir>2' or '<dir>3', but not both
        ext = ('ext2' in self.folder) != ('ext3' in self.folder)
        lib = ('lib2' in self.folder) != ('lib3' in self.folder)
        if len(self.folder) == 1 and (ext or lib):
            major_v = self.folder[0][-1]
            markers = " ; python_version == '%s.*'" % major_v

        return markers
