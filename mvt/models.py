# coding: utf-8

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List


@dataclass
class VendoredLibrary:
    """Represents a vendored library."""
    folder: List[str]
    name: str
    extras: List[str]
    version: str
    modules: List[str]
    git: bool
    branch: str
    url: str
    usage: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    GIT_REPLACE_PATTERN = re.compile(r'/(?:tree|commits?)/', re.IGNORECASE)

    def json(self) -> OrderedDict:
        return OrderedDict([
            ('folder', self.folder),
            ('name', self.name),
            ('extras', self.extras),
            ('version', self.version),
            ('modules', self.modules),
            ('git', self.git),
            ('branch', self.branch),
            ('url', self.url),
            ('usage', self.usage),
            ('notes', self.notes),
        ])

    @property
    def package(self):
        extras = ','.join(self.extras)
        return self.name + (f'[{extras}]' if extras else '')

    def as_requirement(self):
        if self.git:
            if 'github.com' in self.url:
                # https://codeload.github.com/:org/:repo/tar.gz/:commit-ish
                git_url = self.GIT_REPLACE_PATTERN.sub('/tar.gz/', self.url)
                git_url = git_url.replace('https://github.com/', 'https://codeload.github.com/')
            else:
                git_url = 'git+' + self.GIT_REPLACE_PATTERN.sub('.git@', self.url)
            return f'{self.package} @ {git_url}{self.markers}'
        else:
            return f'{self.package}=={self.version}{self.markers}'

    def as_update_requirement(self):
        if self.git:
            if 'github.com' in self.url:
                # https://github.com/:org/:repo/archive/:commit-ish.tar.gz
                git_url = self.GIT_REPLACE_PATTERN.sub('/archive/', self.url) + '.tar.gz'
                git_url = git_url.replace(self.version, self.branch or 'HEAD')
                return f'{self.package} @ {git_url}'
            else:
                raise ValueError('Only github.com is supported currently.')
        else:
            return f'{self.package}'

    @property
    def markers(self):
        markers = ''
        # Exclusive-OR: Either '<dir>2' or '<dir>3', but not both
        ext = ('ext2' in self.folder) != ('ext3' in self.folder)
        lib = ('lib2' in self.folder) != ('lib3' in self.folder)
        if len(self.folder) == 1 and (ext or lib):
            major_v = self.folder[0][-1]
            markers = f" ; python_version == '{major_v}.*'"

        return markers

    @property
    def main_module(self):
        return self.modules[0]

    @property
    def is_main_module_file(self):
        """Is the main module a file? (*.py)"""
        return self.main_module.endswith('.py')

    @property
    def used_by_medusa(self):
        return self.used_by('medusa')

    def used_by(self, name):
        name_lower = name.lower()
        return any(
            (name_lower in u) if ' ' in u else (name_lower == u)
            for u in map(str.lower, self.usage)
        )
