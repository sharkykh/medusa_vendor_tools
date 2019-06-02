# coding: utf-8

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
