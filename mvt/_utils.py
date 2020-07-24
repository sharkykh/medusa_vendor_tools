# coding: utf-8
"""Utility functions."""
from pathlib import Path
from typing import List

from .models import VendoredLibrary


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
