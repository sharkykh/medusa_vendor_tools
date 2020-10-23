# coding: utf-8
from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from . import PROJECT_MODULE

UsedByModuleType = TypeVar('UsedByModuleType', bound='UsedByModule')
UsedByType = TypeVar('UsedByType', bound='UsedBy')
VendoredLibraryType = TypeVar('VendoredLibraryType', bound='VendoredLibrary')
VendoredListType = TypeVar('VendoredListType', bound='VendoredList')

KeyType = Union[VendoredLibraryType, UsedByModuleType, str]
GetItemKeyType = Union[KeyType, int]

UsedByModuleJSONType = Union[str, List[str]]


def to_key(item: KeyType) -> str:
    if isinstance(item, (VendoredLibrary, UsedByModule)):
        key = item.name
    elif isinstance(item, str):
        key = item
    else:
        raise ValueError(f'Unsupported type {type(item).__name__}')

    return key.lower()


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
    def from_json(cls: Type[UsedByModule], data: UsedByModuleJSONType) -> UsedByModule:
        if isinstance(data, list):
            name, extra = data
            data = f'{name} {extra}'

        return cls(data)

    def json(self) -> UsedByModuleJSONType:
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
        name = f'**`{self.name}`**' if self.name == PROJECT_MODULE else f'`{self.name}`'
        if not self.extra:
            return name
        return ' '.join((name, self.extra))

    def __repr__(self) -> str:
        data = ', '.join(self.json())
        return f'{type(self).__name__}({data})'


class UsedBy:
    UPDATE_ME = '<UPDATE-ME>'
    _UNUSED = '<UNUSED>'

    def __init__(self, raw_used_by: Union[str, List[str]] = ''):
        # Examples:
        #   **`medusa`** (via `beautifulsoup4`), `subliminal` (cli only), `requests`
        #   `<UNUSED>`
        #   `<UPDATE-ME>`
        self._modules: Dict[str, UsedByModule] = {}

        if not raw_used_by:
            return

        if isinstance(raw_used_by, str):
            raw_used_by = raw_used_by.split(', ')

        for raw_item in raw_used_by:
            item = UsedByModule(raw_item)

            if item.match(self._UNUSED):
                self._modules = {}
                return

            self._modules[item.name.lower()] = item

    @classmethod
    def from_json(cls: Type[UsedBy], data: List[UsedByModuleJSONType]) -> UsedBy:
        result = cls()

        for raw_item in data:
            item = UsedByModule.from_json(raw_item)
            result.add(item)

        return result

    def json(self) -> List[UsedByModuleJSONType]:
        return [item.json() for item in self.ordered]

    @property
    def unused(self) -> bool:
        """Is unused?"""
        return len(self) == 0

    @property
    def ordered(self) -> List[UsedByModule]:
        """Return an ordered list."""
        result: List[UsedByModule] = []
        result_last: List[UsedByModule] = []

        for item in sorted(self._modules.values(), key=lambda x: x.name.lower()):
            if item == '?????':
                result_last.append(item)
                continue

            if item == PROJECT_MODULE:
                result.insert(0, item)
            else:
                result.append(item)

        return result + result_last

    def add(self, item: KeyType):
        """Add to usage."""
        if isinstance(item, UsedByModule):
            value = item
        elif isinstance(item, VendoredLibrary):
            value = UsedByModule(item.name)
        elif isinstance(item, str):
            value = UsedByModule(item)
        else:
            raise ValueError(f'Unsupported type {type(item).__name__}')

        key = value.name.lower()

        if key in self._modules:
            raise KeyError(f'{value.name} already exists!')

        self._modules[key] = value

    def remove(self, item: KeyType, ignore_errors: bool = False) -> Optional[UsedByModule]:
        """Remove from usage."""
        key = to_key(item)
        try:
            item = self._modules[key]
            del self._modules[key]
            return item
        except KeyError:
            if not ignore_errors:
                raise

    def __contains__(self, item: KeyType) -> bool:
        key = to_key(item)
        return key in self._modules

    def __getitem__(self, item: GetItemKeyType) -> UsedByModule:
        if isinstance(item, int):
            return self.ordered[item]

        key = to_key(item)
        return self._modules[key]

    def __iter__(self) -> Generator[UsedByModule, None, None]:
        for item in self.ordered:
            yield item

    def __next__(self):
        return next(iter(self))

    def __len__(self) -> int:
        return len(self._modules)

    def __bool__(self) -> bool:
        return len(self._modules) == 0

    def __str__(self) -> str:
        if self.unused:
            return f'`{self._UNUSED}`'

        return ', '.join(str(item) for item in self.ordered)

    def __repr__(self) -> str:
        data = ', '.join((
            repr(' '.join(item) if isinstance(item, list) else item)
            for item in self.json()
        ))
        return f'{type(self).__name__}({data})'


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

    @classmethod
    def from_json(cls: Type[VendoredLibrary], data: Dict[str, Any]) -> VendoredLibrary:
        item = data.copy()
        item['usage'] = UsedBy.from_json(item['usage'])
        return cls(**item)

    def json(self) -> Dict[str, Any]:
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

    @property
    def updatable(self) -> bool:
        if not self.url:
            return False

        if self.git and '/blob/' in self.url:
            return False

        return True

    def as_requirement(self) -> str:
        if not self.updatable:
            return ''

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
        if not self.updatable:
            return ''

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

    def as_list_item(self) -> str:
        # Folder
        ext = ('ext2' in self.folder) or ('ext3' in self.folder)
        lib = ('lib2' in self.folder) or ('lib3' in self.folder)
        folder = ' '.join(self.folder)
        if ext or lib:
            folder = f'**{folder}**'

        # Package
        package = f'`{self.package}`'
        if self.main_module_matches_package_name:
            package = f'**{package}**'

        # Version
        if self.version is None:
            version = '-'
        elif not self.git:
            version = f'[{self.version}]({self.url})'
        else:
            branch = f'{self.branch}@' if self.branch else ''
            version = f'[{branch}{self.version[:7]}]({self.url})'
            if '/pymedusa/' in self.url:
                version = f'pymedusa/{version}'

        # Usage
        usage = str(self.usage)

        # Modules
        modules = ', '.join(
            [f'`{self.main_module}`']
            + [f'`{m}`' for m in self.modules[1:]]
        )

        # Notes
        notes = []
        if len(self.modules) > 1:
            notes.append(f'Modules: {modules}')
        elif not self.main_module_matches_package_name:
            if self.is_main_module_file:
                notes.append(f'File: `{self.main_module}`')
            else:
                notes.append(f'Module: `{self.main_module}`')

        notes.extend(self.notes)
        notes = '<br>'.join(notes) if notes else '-'

        return ' | '.join((folder, package, version, usage, notes))

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

    def __str__(self) -> str:
        return self.name


class VendoredList:
    def __init__(self):
        self._items: Dict[str, VendoredLibrary] = {}

    @classmethod
    def from_json(cls: Type[VendoredList], data: List[Dict[str, Any]]) -> VendoredList:
        result = cls()

        for raw_item in data:
            item = VendoredLibrary.from_json(raw_item)
            result.add(item)

        return result

    def json(self) -> List[Dict[str, Any]]:
        return [item.json() for item in self.ordered]

    @property
    def ordered(self) -> List[VendoredLibrary]:
        """Return an ordered list."""
        return sorted(self._items.values(), key=lambda x: x.name.lower())

    @property
    def folder(self) -> str:
        try:
            return self.ordered[0].folder[0].rstrip('23')
        except IndexError:
            return ''

    def add(self, item: VendoredLibrary):
        """Add to list."""
        if not isinstance(item, VendoredLibrary):
            raise ValueError(f'Unsupported type {type(item).__name__}')

        key = item.name.lower()

        if key in self._items:
            raise KeyError(f'{item.name} already exists!')

        self._items[key] = item

    def remove(self, item: KeyType, ignore_errors: bool = False) -> Optional[VendoredLibrary]:
        """Remove from list."""
        key = to_key(item)
        try:
            item = self._items[key]
            del self._items[key]
            return item
        except KeyError:
            if not ignore_errors:
                raise

    def __contains__(self, item: KeyType) -> bool:
        key = to_key(item)
        return key in self._items

    def __getitem__(self, item: GetItemKeyType) -> VendoredLibrary:
        if isinstance(item, int):
            return self.ordered[item]

        key = to_key(item)
        return self._items[key]

    def __setitem__(self, raw_key: KeyType, item: VendoredLibrary):
        if not isinstance(item, VendoredLibrary):
            raise ValueError(f'Unsupported type {type(item).__name__}')

        key = to_key(raw_key)
        self._items[key] = item

    def __iter__(self) -> Generator[VendoredLibrary, None, None]:
        for item in self.ordered:
            yield item

    def __next__(self):
        return next(iter(self))

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f'{type(self).__name__}({len(self)})'
