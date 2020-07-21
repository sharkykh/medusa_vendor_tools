# coding: utf-8

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import (
    Dict,
    Iterator,
    List,
    TypeVar,
    Union,
)

VendoredLibraryType = TypeVar('VendoredLibraryType', bound='VendoredLibrary')
UsedByModuleType = TypeVar('UsedByModuleType', bound='UsedByModule')
UsedByType = TypeVar('UsedByType', bound='UsedBy')
UsageItemType = Union[VendoredLibraryType, UsedByModuleType, str]


class UsedByModule:
    def __init__(self, raw_module: str):
        # Examples:
        #   **`medusa`** (via `beautifulsoup4`)
        #   `subliminal` (cli only)
        #   `requests`
        #   `<UNUSED>`
        #   `<UPDATE-ME>`
        # re.sub(r'(?:\*\*)?`(.+?)`(?:\*\*)?(?: (.+))?', '', raw_module)
        try:
            name, extra = raw_module.split(' ', 1)
        except ValueError:
            name, extra = raw_module, ''

        self.name = name.strip('*`')
        self.extra = extra

    @classmethod
    def from_json(cls, data: Union[str, List[str]]) -> UsedByModuleType:
        try:
            name, extra = data
            return cls(name + ' ' + extra)
        except ValueError:
            return cls(data)

    def json(self) -> Union[str, List[str]]:
        if self.extra:
            return [self.name, self.extra]
        return self.name

    def __eq__(self, value: str) -> bool:
        """Case-insensitive name match."""
        return self.name.lower() == value.lower()

    def match(self, value: str) -> bool:
        """Normal (case-sensitive) name match."""
        return self.name == value

    def __str__(self) -> str:
        name = f'**`{self.name}`**' if self.name == 'medusa' else f'`{self.name}`'
        if not self.extra:
            return name
        return ' '.join((name, self.extra))



class UsedBy:
    UPDATE_ME = '<UPDATE-ME>'
    _UNUSED = '<UNUSED>'

    def __init__(self, raw_used_by: Union[str, List[str]] = ''):
        # Examples:
        #   **`medusa`** (via `beautifulsoup4`), `subliminal` (cli only), `requests`
        #   `<UNUSED>`
        #   `<UPDATE-ME>`
        self.modules: Dict[str, UsedByModule] = {}

        if not raw_used_by:
            return

        def process(items: List[str]):
            for raw_item in items:
                item = UsedByModule(raw_item)

                if item.match(self._UNUSED):
                    self.modules = {}
                    return

                self.modules[item.name.lower()] = item

        if isinstance(raw_used_by, list):
            process(raw_used_by)
        else:
            process(raw_used_by.split(', '))

    @classmethod
    def from_json(cls, data: List[Union[str, List[str]]]) -> UsedByType:
        result = cls()

        for raw_item in data:
            item = UsedByModule.from_json(raw_item)
            result.modules[item.name.lower()] = item

        return result

    def json(self) -> List[str]:
        return [item.json() for item in self.ordered]

    @property
    def unused(self) -> bool:
        """Is unused?"""
        return len(self) == 0

    @property
    def ordered(self) -> List[UsedByModule]:
        """Return an ordered list."""
        result = sorted(self.modules.values(), key=lambda x: x.name.lower())

        usage: List[UsedByModule] = []
        usage_last: List[UsedByModule] = []
        for item in result:
            if item == '?????':
                usage_last.append(item)
                continue

            if item == 'medusa':
                usage.insert(0, item)
            else:
                usage.append(item)

        return usage + usage_last

    @staticmethod
    def _to_key(item: UsageItemType) -> str:
        if isinstance(item, (VendoredLibrary, UsedByModule)):
            key = item.name
        elif isinstance(item, str):
            key = item
        else:
            raise ValueError(f'Unsupported type {item.__class__.__name__}')

        return key.lower()

    def add(self, item: UsageItemType):
        """Add to usage."""
        if isinstance(item, UsedByModule):
            value = item
        elif isinstance(item, VendoredLibrary):
            value = UsedByModule(item.name)
        elif isinstance(item, str):
            value = UsedByModule(item)
        else:
            raise ValueError(f'Unsupported type {item.__class__.__name__}')

        key = value.name.lower()

        if key in self.modules:
            raise ValueError(f'{value.name} already exists!')

        self.modules[key] = value

    def remove(self, item: UsageItemType, ignore_errors: bool = False):
        """Remove from usage."""
        key = self._to_key(item)
        try:
            del self.modules[key]
        except KeyError:
            if not ignore_errors:
                raise

    def __contains__(self, item: UsageItemType) -> bool:
        key = self._to_key(item)
        return key in self.modules

    def __getitem__(self, item: UsageItemType) -> UsedByModule:
        key = self._to_key(item)
        return self.modules[key]

    def __iter__(self) -> Iterator[UsedByModule]:
        for item in self.ordered:
            yield item

    def __len__(self) -> int:
        return len(self.modules)

    def __str__(self) -> str:
        if self.unused:
            return f'`{self._UNUSED}`'

        return ', '.join([str(item) for item in self.ordered])


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
    usage: UsedBy = field(default_factory=UsedBy)
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
            ('usage', self.usage.json()),
            ('notes', self.notes),
        ])

    @property
    def package(self) -> str:
        extras = ','.join(self.extras)
        return self.name + (f'[{extras}]' if extras else '')

    def as_requirement(self) -> str:
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

    def as_update_requirement(self) -> str:
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
    def markers(self) -> str:
        markers = ''
        # Exclusive-OR: Either '<dir>2' or '<dir>3', but not both
        ext = ('ext2' in self.folder) != ('ext3' in self.folder)
        lib = ('lib2' in self.folder) != ('lib3' in self.folder)
        if len(self.folder) == 1 and (ext or lib):
            major_v = self.folder[0][-1]
            markers = f" ; python_version == '{major_v}.*'"

        return markers

    @property
    def main_module(self) -> str:
        return self.modules[0]

    @property
    def main_module_matches_package_name(self) -> bool:
        """Is the main module named exactly like `package`?"""
        return self.main_module == self.package

    @property
    def is_main_module_file(self) -> bool:
        """Is the main module a file? (*.py)"""
        return self.main_module.endswith('.py')

    @property
    def used_by_medusa(self) -> bool:
        return 'medusa' in self.usage

    @property
    def updatable(self) -> bool:
        if self.git:
            if not self.url:
                return False
            if '/blob/' in self.url:
                return False

        return True
