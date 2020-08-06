# coding: utf-8
"""Utility functions."""
import json
import os
import shutil
from pathlib import Path
from typing import (
    Dict,
    List,
    Union,
)

from pkg_resources._vendor.packaging.specifiers import SpecifierSet

from .models import (
    VendoredLibrary,
    VendoredList,
)
from .parse import parse_requirements


def get_py_executable() -> str:
    if os.name == 'nt':
        return 'py'

    py_path: Path = Path(__file__).parent / 'tools' / 'py'

    # Use Unix `py` tool
    # Make sure it is executable
    import stat
    cur_mode = py_path.stat().st_mode
    if not (cur_mode & stat.S_IEXEC):
        answer = input(f'Needs to execute: {py_path}, OK? [y/N] ')
        if not answer or answer.lower() != 'y':
            raise Exception('Unable to execute Unix `py` tool, requires user consent.')
        py_path.chmod(cur_mode | stat.S_IEXEC)

    return str(py_path)


def load_requirements(listpath: Path, ignore_errors: bool = False) -> VendoredList:
    """Get requirements from list."""
    requirements = VendoredList()

    for req, error in parse_requirements(listpath):
        if error and not ignore_errors:
            raise error
        requirements.add(req)

    return requirements


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


def get_renovate_config(project_path: Path) -> Dict[str, SpecifierSet]:
    if not SpecifierSet:
        return {}

    renovate_json = project_path.joinpath('renovate.json')
    if not renovate_json.is_file():
        return {}

    with renovate_json.open('r', encoding='utf-8') as fh:
        data = json.load(fh)

    try:
        python_config: Dict[str, dict] = data['python']
        python_pkg_rules: List[Dict[str, Union[List[str], str]]] = python_config['packageRules']
    except KeyError:
        return {}

    constraints: Dict[str, str] = {}
    for rule in python_pkg_rules:
        try:
            names: List[str] = rule['packageNames']
            allowed_versions: str = rule['allowedVersions']
        except KeyError:
            continue

        constraints.update({
            name.lower(): SpecifierSet(allowed_versions)
            for name in names
        })

    return constraints


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
