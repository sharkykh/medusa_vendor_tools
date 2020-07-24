# coding: utf-8
"""Utility functions."""
import shutil
from pathlib import Path
from typing import (
    List,
    Optional,
)

from .models import VendoredLibrary
from .parse import (
    LineParseError,
    parse_requirements,
)


def load_requirements(listpath: Path, package_name: str) -> (List[VendoredLibrary], Optional[int]):
    """Get requirements from list, try to find the provided package's index."""
    requirements: List[VendoredLibrary] = []
    req_idx: Optional[int] = None

    generator = parse_requirements(listpath)

    package_name_lower = package_name.lower()
    # Types for the loop variables
    index: int
    req: Optional[VendoredLibrary]
    error: Optional[LineParseError]
    for index, (req, error) in enumerate(generator):
        if error:
            raise error
        requirements.append(req)

        if package_name_lower == req.name.lower():
            req_idx = index

    return requirements, req_idx


def package_module_paths(req: VendoredLibrary, root: Path) -> List[Path]:
    """Make a list of all of the full module paths for deletion."""
    package_modules: List[Path] = []

    for folder in req.folder:
        target_path: Path = root / folder
        for module in req.modules:
            module_path: Path = (target_path / module).resolve()
            # Make sure we're not removing anything outside the target folder!
            if target_path not in module_path.parents:
                continue
                # raise Exception(
                #     'Stopping before removal of files outside target folder!'
                #     f' - {module_path} is not within {target_path}'
                # )

            package_modules.append(module_path)

            # Remove dangling namespace folders
            if '/' in module:
                ns_path = target_path / module.split('/', 1)[0]
                check_paths = [ns_path / '__init__.py'] + package_modules
                remaining_files = any(p not in check_paths for p in ns_path.glob('*'))
                if not remaining_files:
                    for mod in package_modules:
                        if ns_path in mod.parents:
                            package_modules.remove(mod)
                    package_modules.append(ns_path)

    return package_modules


def drop_dir(path: Path, ignore_errors=False, onerror=None):
    """Recursively delete the directory tree at `path`."""
    shutil.rmtree(str(path), ignore_errors=ignore_errors, onerror=onerror)


def remove_all(paths: List[Path]):
    """Recursively delete every file and directory tree of `paths`."""
    for path in paths:
        if path.is_dir():
            drop_dir(path)
        else:
            path.unlink()
