# coding: utf-8
"""Vendor (or update existing) libraries."""
import csv
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tarfile import TarFile
from textwrap import dedent
from typing import (
    List,
    Mapping,
    Optional,
    Pattern,
    Union,
)
from zipfile import ZipFile

import pkg_resources
from pkg_resources._vendor.packaging.requirements import InvalidRequirement, Requirement
from pkg_resources._vendor.packaging.markers import Marker

from . import parse as parse_md
from .gen_req import generate_requirements
from .get_setup_kwargs import get_setup_kwargs
from .make_md import make_md
from .models import VendoredLibrary

# Typing
AnyDistribution = Union[
    pkg_resources.Distribution,
    pkg_resources.DistInfoDistribution,
    pkg_resources.EggInfoDistribution
]

MIN_PYTHON_2 = '2.7.10'
MIN_PYTHON_3 = '3.5.2'
# https://github.com/:owner/:repo/archive/:commit-ish.tar.gz#egg=name
# https://codeload.github.com/:owner/:repo/tar.gz/:commit-ish#egg=name
# name@https://github.com/:owner/:repo/archive/:commit-ish.tar.gz
# Can also use `zip` in place of `tar.gz`, `#egg=name` is not needed if using `name @` prefix
GITHUB_URL_PATTERN: Pattern = re.compile(r'github\.com/(?P<slug>.+?/.+?)/[^/]+?/(?P<commit_ish>.+?)(?:\.tar\.gz|\.zip)?(?:#|$)', re.IGNORECASE)


# Main method
def vendor(listfile: str, package: str, dependents: List[str], py2: bool, py3: bool, py6: bool) -> None:
    listpath = Path(listfile).resolve()
    root = listpath.parent.parent

    # Parse package name / version constraint from argument
    parsed_package = parse_input(package)
    package_name: str = parsed_package.name

    print(f'Starting vendor script for: {parsed_package}')

    # Get requirements from list, try to find the package we're vendoring right now
    requirements, req_idx = load_requirements(listpath, package_name)
    target = listpath.parent.name  # `ext` or `lib`

    if req_idx is not None:
        req = requirements[req_idx]
    else:
        req = None

    if req:
        # Remove old folder(s)/file(s) first using info from `[target]/readme.md`
        package_modules: List[Path] = []
        for folder in req.folder:
            target_path: Path = root / folder
            for module in req.modules:
                module_path: Path = (target_path / module).resolve()
                # Make sure we're not removing anything outside the target folder!
                if target_path not in module_path.parents:
                    raise Exception(
                        'Stopping before removal of files outside target folder!'
                        f' - {module_path} is not within {target_path}'
                    )
                package_modules.append(module_path)

        modules_csv = ', '.join(map(str, package_modules))
        print(f'Removing: [{modules_csv}]')
        try:
            remove_all(package_modules)
        except OSError:
            pass

        if not py2 and not py3 and not py6:
            print(f'Package {package_name} found in list, using that')
            install_folders = req.folder
            py2 = f'{target}2' in install_folders
            py3 = f'{target}3' in install_folders
            py6 = len(install_folders) == 1 and target in install_folders
        else:
            print(f'Installing {package_name} to targets according to CLI switches')
            install_folders = None
    else:
        print(f'Package {package_name} not found in list, assuming new package')
        install_folders = None

    # Download source code (removed later)
    download_target: Path = root / '.mvt-temp'
    temp_install_dir: Path = download_target / '__install__'

    try:
        source_archive = download_source(parsed_package, download_target, py2=py2, py3=py3)
        extracted_source, source_commit_hash = extract_source(source_archive)
        setup_py_results = check_setup_py(extracted_source, py2=py2, py3=py3)
    except InstallFailed as error:
        drop_dir(download_target)
        print(f'Error: {error!r}')
        return

    if not install_folders:
        install_folders = make_list_of_folders(target, py6=py6, **setup_py_results['versions'])

    dependencies = setup_py_results['dependencies']

    installed = None
    for folder in install_folders:
        installed = install(
            vendor_dir=root / folder,
            temp_install_dir=temp_install_dir,
            source_dir=extracted_source,
            source_commit_hash=source_commit_hash,
            parsed_package=parsed_package,
            py2=folder.endswith('2'),
        )

        print(f'Installed: {installed.package}=={installed.version} to {folder}')

    installed.folder = install_folders

    # Remove downloaded source after installation
    drop_dir(download_target)

    if req:
        installed.usage = req.usage
        installed.notes += req.notes

    # Dependency checks
    run_dependency_checks(installed, dependencies, dependents, requirements)

    if not installed.usage:
        installed.usage = ['<UPDATE-ME>']

    readme_name = '/'.join(listpath.parts[-2:])
    print(f'Updating {readme_name}')

    if req_idx is not None:
        requirements[req_idx] = installed
    else:
        requirements.append(installed)

    md_data = make_md(requirements)

    if not listpath.parent.exists():
        os.makedirs(listpath.parent, exist_ok=True)

    with listpath.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(''.join(md_data))

    if target == 'ext':
        print('Updating requirements.txt')
        reqs_file = root / 'requirements.txt'
        generate_requirements(
            infile=str(listpath),
            outfile=str(reqs_file),
            all_packages=False,
            json_output=False,
        )

    print('Done!')


def parse_input(package: str) -> Requirement:
    """Parse package name / version constraint from argument."""
    try:
        return Requirement(package)
    except InvalidRequirement:
        pass

    try:
        egg_value = re.search(r'#egg=(.+)(?:&|$)', package)
        package = f'{egg_value.group(1)}@{package}'
        return Requirement(package)
    except (InvalidRequirement, AttributeError):
        # AttributeError: 'NoneType' object has no attribute 'group'
        pass

    raise ValueError(f'Unable to parse {package}')


def load_requirements(listpath: Path, package_name: str) -> (List[VendoredLibrary], Optional[int]):
    """Get requirements from list, try to find the package we're vendoring right now."""
    requirements: List[VendoredLibrary] = []
    req_idx: Optional[int] = None

    generator = parse_md.parse_requirements(listpath)

    package_name_lower = package_name.lower()
    # Types for the loop variables
    index: int
    req: Optional[VendoredLibrary]
    error: Optional[parse_md.LineParseError]
    for index, (req, error) in enumerate(generator):
        if error:
            raise error
        requirements.append(req)

        if package_name_lower == req.name.lower():
            req_idx = index

    return requirements, req_idx


def download_source(parsed_package: Requirement, download_target: Path, py2: bool = False, py3: bool = False) -> Path:
    remove_all(download_target.glob('**/*'))
    download_target.mkdir(exist_ok=True)

    (download_target / '.gitignore').write_text('*', encoding='utf-8')

    print(f'Downloading source for {parsed_package.name}')

    with_py2 = py2 and not py3
    args: List[str] = executable(with_py2) + [
        '-m', 'pip', '--no-python-version-warning', 'download', '--no-binary', ':all:', '--no-deps', '--no-cache-dir',
        '--dest', str(download_target), str(parsed_package),
    ]
    if with_py2:
        # Some versions of Pip for Python 2.7 on Windows can sometimes fail when the progress bar is enabled
        # See: https://github.com/pypa/pip/issues/5665
        args += ['--progress-bar', 'off']

    print('+++++ [ pip download ] +++++')
    pip_result = subprocess.run(args)
    print('----- [ pip download ] -----')

    if pip_result.returncode != 0:
        raise SourceDownloadFailed('Pip failed')

    return next(
        f for f in download_target.glob('*')
        if f.name not in ('.gitignore', '__install__')
    )


def executable(py2: bool) -> List[str]:
    if py2:
        # Use "Python Launcher for Windows" (available since Python 3.3)
        return ['py', '-2.7']

    # Use currently running Python version (3.7+)
    return [sys.executable]


class SourceDownloadFailed(Exception):
    pass


def extract_source(source_path: Path) -> (Path, Optional[str]):
    """Extract the source archive, return the extracted path and optionally the commit hash stored inside."""
    extracted_path = source_path.with_name(source_path.stem)
    commit_hash = None

    # Determine the source archive type before extracting it
    # Inspired by: https://stackoverflow.com/a/13044946/7597273
    magic_dict = {
        b'\x1f\x8b\x08': 'gz',
        b'\x42\x5a\x68': 'bz2',
        b'\x50\x4b\x03\x04': 'zip',
    }
    max_len = max(len(x) for x in magic_dict)

    with source_path.open('rb') as f:
        file_start: bytes = f.read(max_len)

    for magic, archive_type in magic_dict.items():
        if file_start.startswith(magic):
            break
    else:
        raise TypeError(f'Unknown source archive type: `{source_path.name}`')

    if archive_type in ('gz', 'bz2'):
        with TarFile.open(str(source_path), 'r:' + archive_type) as tar:
            # Commit hash (if downloaded from GitHub)
            commit_hash = tar.pax_headers.get('comment')
            # Update extracted path because:
            # `<commit-hash>[.tar.gz]` extracts a folder named `repo-name-<commit-hash>`
            # `<branch-name>[.tar.gz]` extracts a folder named `repo-name-<branch-name>`
            root_files = [name for name in tar.getnames() if '/' not in name]
            if len(root_files) == 1:
                extracted_path = source_path.with_name(root_files[0])

            tar.extractall(str(extracted_path.parent))

    elif archive_type == 'zip':
        with ZipFile(str(source_path), 'r') as zipf:
            # Commit hash (if downloaded from GitHub)
            if zipf.comment:
                commit_hash = zipf.comment.decode('utf-8')
            # Update extracted path because:
            # `<commit-hash>[.zip]` extracts a folder named `repo-name-<commit-hash>`
            # `<branch-name>[.zip]` extracts a folder named `repo-name-<branch-name>`
            root_folders = []
            root_files = []
            for name in zipf.namelist():
                if name.count('/') == 1 and name.endswith('/'):
                    root_folders.append(name.rstrip('/'))
                if name.count('/') == 0:
                    root_files.append(name)
            # If only one root folder
            if len(root_folders) == 1 and len(root_files) == 0:
                extracted_path = source_path.with_name(root_folders[0])

            zipf.extractall(str(extracted_path.parent))

    return extracted_path, commit_hash


# `extras_require` can be complex...
def compile_extras_require(data: Optional[Mapping[str, List[str]]]) -> List[str]:
    extras = []
    if not data:
        return extras

    for extra_key, packages in data.items():
        # Convert `extras_require` format to a list of requirement strings
        # {"socks:python_version == '2.7'": [...]}
        # {":python_version == '2.7'": [...]}
        # {'': [...]}
        extra, markers = extra_key.split(':') if ':' in extra_key else [extra_key, '']

        # Skip `test` and `dev` extras
        if extra in ('dev', 'test'):
            continue

        for package in packages:
            req = Requirement(package)
            old_marker = str(req.marker) if req.marker else ''

            new_markers = []
            if markers:
                new_markers.append(f'({markers})')
            if extra:
                new_markers.append(f"extra == '{extra}'")
            if old_marker:
                new_markers.insert(0, f'({old_marker})')

            req.marker = Marker(' and '.join(new_markers))

        extras.append(str(req))

    return extras


def check_setup_py(package_path: Path, py2: bool, py3: bool) -> dict:
    process_all = not py2 and not py3
    process_py3 = py3 or process_all
    process_py2 = py2 or process_all
    process_any = process_py3 and process_py2

    # Check with Python 3
    if process_py3:
        kwargs_py3 = get_setup_kwargs(setup_path=package_path, python_version=MIN_PYTHON_3)
    else:
        kwargs_py3 = {}

    # Check with Python 2 (may try to spawn Python a Python 2 executable)
    if process_py2:
        kwargs_py2 = get_setup_kwargs(setup_path=package_path, python_version=MIN_PYTHON_2)
    else:
        kwargs_py2 = {}

    # Merge unique dependencies, update missing markers for python versions
    deps_py2 = kwargs_py2.get('install_requires', [])
    deps_py3 = kwargs_py3.get('install_requires', [])

    deps_py2 += compile_extras_require(kwargs_py2.get('extras_require', {}))
    deps_py3 += compile_extras_require(kwargs_py3.get('extras_require', {}))

    dependencies = filter_unique_dependencies(deps_py2, deps_py3)

    result = {
        'versions': {'py3': py3, 'py2': py2},
        'dependencies': dependencies
    }

    separate_versions = any([
        kwargs_py3.get('use_2to3', False),
        process_any and kwargs_py3.get('package_dir') != kwargs_py2.get('package_dir'),
    ])
    if separate_versions and not all(result['versions'].values()):
        result['versions'] = {'py3': True, 'py2': True}

    return result


def filter_unique_dependencies(deps_py2: List[str], deps_py3: List[str]) -> List[Requirement]:
    parsed_deps = {
        2: list(map(Requirement, deps_py2)),
        3: list(map(Requirement, deps_py3)),
    }

    dependencies = []
    deps_seen = set()
    deps_unique = set(map(str, parsed_deps[2])).difference(map(str, parsed_deps[3]))

    for version, deps in parsed_deps.items():
        for dep in deps:
            dep_as_str = str(dep)

            # Mark seen dependencies to filter out the duplicates
            if dep_as_str in deps_seen:
                continue
            deps_seen.add(dep_as_str)

            if dep_as_str in deps_unique:
                # If marker has the "python_version" key, we don't need to change anything
                if dep.marker and 'python_version' not in str(dep.marker):
                    # Unique to one of the Python versions, update markers
                    old_marker = f'({dep.marker}) and ' if dep.marker else ''
                    dep.marker = Marker(old_marker + f"python_version == '{version}.*'")

            dependencies.append(dep)

    return dependencies


def make_list_of_folders(target: str, py2: bool, py3: bool, py6: bool) -> List[str]:
    """Generate a list of target folders based on targeted Python versions."""
    install_folders: List[str] = []
    if py6 or (not py2 and not py3):  # if py6 or neither, normal
        install_folders.append(target)
    else:  # if either one, or both, target for each major version
        if py2:  # py2 only
            install_folders.append(f'{target}2')
        if py3:  # py3 only
            install_folders.append(f'{target}3')
    return install_folders


def run_dependency_checks(
    installed: VendoredLibrary,
    dependencies: List[Requirement],
    dependents: List[str],
    requirements: List[VendoredLibrary]
) -> None:
    """
    Run dependency checks.
    - Check if a dependency of a previous version is not needed now and remove it
    - Check that the dependencies are installed (partial),
        and that their versions match the new specifier (also partial)
    - Set usage for installed library, if provided.

    Note: May mutate items of `requirements`.
    """
    print('+++++++++++++++++++++')
    print('+ Dependency checks +')
    print('+-------------------+')

    installed_pkg_lower = installed.name.lower()
    installed_pkg_extras = [None] + installed.extras

    deps_fmt = '\n  '.join(map(str, dependencies)) or 'no dependencies'
    print(f'Package {installed.package} depends on:\n  {deps_fmt}\n')

    dependents_lower = list(map(str.lower, dependents))

    def remove_dependent(name):
        i = dependents_lower.index(name)
        dependents_lower.pop(i)
        dependents.pop(i)

    # Filter out dependencies that are required by "extras" we did not install
    filtered_dependencies = list(filter(
        lambda d: not d.marker or any(d.marker.evaluate({'extra': ex}) for ex in installed_pkg_extras),
        dependencies
    ))
    # Check if a dependency of a previous version is not needed now and remove it
    dep_names: List[str] = [d.name.lower() for d in filtered_dependencies]
    # Types for the loop variables
    idx: int
    req: VendoredLibrary
    for idx, req in enumerate(requirements):
        req_lower = req.name.lower()
        usage_lower = list(map(str.lower, req.usage))

        # Does this library use the installed package?
        if dependents_lower and req_lower in dependents_lower and not installed.used_by(req_lower):
            print(f'Adding `{req.name}` to the "usage" column of `{installed.name}`')
            installed.usage.append(req.name)
            remove_dependent(req_lower)

        if installed_pkg_lower in usage_lower and req_lower not in dep_names:
            idx = usage_lower.index(installed_pkg_lower)
            req.usage.pop(idx)
            print(f'Removed `{installed.name}` usage from dependency `{req.name}`')

    # Check that the dependencies are installed (partial),
    #   and that their versions match the new specifier (also partial)
    req_names: List[str] = [r.name.lower() for r in requirements]
    # Types for the loop variables
    dep: Requirement
    for dep in filtered_dependencies:
        try:
            dep_req_idx = req_names.index(dep.name.lower())
        except ValueError:
            # raised if dependency was not found
            specifier = str(dep.specifier) or 'any version'
            text = f'May need to install new dependency `{dep.name}` @ {specifier}'
            if dep.marker:
                text += f', but only for {dep.marker!s}'
            print(text)
            continue

        dep_req = requirements[dep_req_idx]
        dep_req_name = dep_req.name
        dep_req_ver = dep_req.version
        if dep_req_ver not in dep.specifier:
            if dep_req.git:
                print(f'May need to update `{dep_req_name}` (git dependency) to match specifier: {dep.specifier}')
            else:
                print(f'Need to update `{dep_req_name}` from {dep_req_ver} to match specifier: {dep.specifier}')

        if not dep_req.used_by(installed_pkg_lower):
            print(f'Adding `{installed.name}` to the "usage" column of `{dep_req_name}`')
            dep_req.usage.append(installed.name)

            if '<UPDATE-ME>' in dep_req.usage:
                dep_req.usage.remove('<UPDATE-ME>')
            if '<UNUSED>' in dep_req.usage:
                dep_req.usage.remove('<UNUSED>')

    # Add remaining dependents
    for d in dependents:
        if d.lower() == 'medusa':
            d = 'medusa'
        if not installed.used_by(d):
            print(f'Adding `{d}` to the "usage" column of `{installed.name}`')
            installed.usage.append(d)
            remove_dependent(d)

    usage_sans_placeholders = list(filter(lambda s: s not in ('<UPDATE-ME>', '<UNUSED>'), installed.usage))
    if usage_sans_placeholders:
        installed.usage = usage_sans_placeholders

    print('+++++++++++++++++++++')


def drop_dir(path: Path, **kwargs) -> None:
    """Recursively delete the directory tree at `path`."""
    shutil.rmtree(str(path), **kwargs)


def remove_all(paths: List[Path]) -> None:
    """Recursively delete every file and directory tree of `paths`."""
    for path in paths:
        if path.is_dir():
            drop_dir(path)
        else:
            path.unlink()


def install(
    vendor_dir: Path,
    temp_install_dir: Path,
    source_dir: Path,
    source_commit_hash: Optional[str],
    parsed_package: Requirement,
    py2: bool = False
) -> VendoredLibrary:
    """Install package from `source_dir` into `vendor_dir` using pip, and return a vendored package object and a list of dependencies."""
    print(f'Installing vendored library `{parsed_package.name}` to `{vendor_dir.name}`')

    # Create the temp install folder
    temp_install_dir.mkdir(exist_ok=True)

    args: List[str] = executable(py2) + [
        '-m', 'pip', 'install', '--no-python-version-warning', '--no-compile', '--no-deps',
    ]
    if py2:
        # Some versions of Pip for Python 2.7 on Windows can sometimes fail when the progress bar is enabled
        # See: https://github.com/pypa/pip/issues/5665
        args += ['--progress-bar', 'off']
    args += ['--target', str(temp_install_dir), str(source_dir)]

    major_version = 2 if py2 else 3

    print(f'+++++ [ pip | py{major_version} ] +++++')
    pip_result = subprocess.run(args)
    print(f'----- [ pip | py{major_version} ] -----')

    if pip_result.returncode != 0:
        raise InstallFailed('Pip failed')

    # Drop the bin directory (contains easy_install, distro, chardetect etc.)
    # Might not appear on all OSes, so ignoring errors
    drop_dir(temp_install_dir / 'bin', ignore_errors=True)

    # Drop interpreter and OS specific files.
    remove_all(temp_install_dir.glob('**/*.pyd'))
    remove_all(temp_install_dir.glob('msgpack/*.so'))

    # Get installed package
    working_set = pkg_resources.WorkingSet([str(temp_install_dir)])  # Must be a list to work
    try:
        installed_pkg: AnyDistribution = working_set.by_key[parsed_package.name.lower()]
    except KeyError:
        # Unable to find installed package by the package name provided for installing
        all_installed = list(working_set)
        if len(all_installed) != 1:
            raise InstallFailed(f'Unable to grab installed package info. WorkingSet: {all_installed}')
        installed_pkg: AnyDistribution = all_installed[0]

    # Fix bad packaging. I don't care about 3rd-party tests.
    drop_dir(temp_install_dir / 'tests', ignore_errors=True)

    # Extras
    if not parsed_package.extras.issubset(installed_pkg.extras):
        print('Invalid extras detected, they will be removed.')
        print(f'Not all members of {parsed_package.extras} are in {installed_pkg.extras}')
    extras = list(parsed_package.extras.intersection(installed_pkg.extras))

    # Modules
    modules = get_modules(temp_install_dir, installed_pkg)

    # Update version and url
    version, url, is_git, branch = get_version_and_url(installed_pkg, parsed_package, source_commit_hash)

    result = VendoredLibrary(
        folder=[vendor_dir.name],
        name=installed_pkg.project_name,
        extras=extras,
        version=version,
        modules=modules,
        git=is_git,
        branch=branch,
        url=url,
    )

    # Remove the package info folder
    drop_dir(Path(installed_pkg.egg_info))

    # Move the files to the target vendor folder
    move_subtrees_r(temp_install_dir, vendor_dir, False)

    # Remove the temp install folder
    try:
        temp_install_dir.rmdir()
    except OSError:
        pass

    return result


class InstallFailed(Exception):
    pass


def move_subtrees_r(source: Path, target: Path, use_replace: bool = True):
    """Recursive tree merge."""
    path_attr = 'replace' if use_replace else 'rename'

    subtree: Path
    for subtree in source.glob('*'):
        target_path = target / subtree.name
        try:
            getattr(subtree, path_attr)(target_path)
        except FileExistsError:
            move_subtrees_r(subtree, target_path)

    source.rmdir()


def get_modules(temp_install_dir: Path, installed_pkg: AnyDistribution) -> List[str]:
    """Get a list of all the top-level modules/files names, with the "main" module being the first."""
    using: str = None
    checklist: List[str] = [
        # Use RECORD first because it's more reliable
        # (Extensions are picked up by `top_level.txt` - see `PyYAML`)
        'RECORD',
        'top_level.txt',
    ]
    while using is None and checklist:
        checkpath: str = checklist.pop(0)
        try:
            raw_top_level: List[str] = installed_pkg.get_metadata(checkpath).splitlines(keepends=False)
            using = checkpath
        except IOError:
            pass

    if not using:
        raise Exception('Unable to read module info')

    # Make a simple list of top level directories / file names
    parsed_top_level: List[str] = []

    if using == 'top_level.txt':
        for ln in raw_top_level:
            name = ln
            if (temp_install_dir / (name + '.py')).is_file():
                name += '.py'
            parsed_top_level.append(name)
    elif using == 'RECORD':
        # six.py,sha256=h9jch2pS86y4R36pKRS3LOYUCVFNIJMRwjZ4fJDtJ44,32452
        # setuptools/wheel.py,sha256=94uqXsOaKt91d9hW5z6ZppZmNSs_nO66R4uiwhcr4V0,8094

        # backports/__init__.py,sha256=elt6uFwbaEv80X8iGWsCJ_w_n_h1X8repgOoNrN0Syg,212
        # backports/configparser/__init__.py,sha256=thhQqB1qWNKf-F3CpZFYsjC8YT-_I_vF0w4JiuQfiWI,56628
        namespace_packages: List[str] = []
        NAMESPACE_PACKAGE_PATTERN = re.compile(r'__path__\s*=.*?extend_path\(__path__, __name__\)')

        for (file_path, _, _) in csv.reader(raw_top_level):
            file_path: Path = Path(file_path)

            top_level_name: str = file_path.parts[0]
            package_path = file_path.parent.as_posix()
            package_path_s = package_path + '/'

            # six-1.12.0.dist-info/top_level.txt,sha256=_iVH_iYEtEXnD8nYGQYpYFUvkUW9sEO1GYbkeKSAais,4
            if top_level_name.endswith(('.dist-info', '.egg-info')):
                continue
            # ../../bin/subliminal.exe,sha256=_00-qFoXoJiPYvmGWSVsK5WspavdE6umXt82G980GiA,102763
            if top_level_name == '..':
                continue
            if top_level_name == 'tests':
                continue

            inside_namespace = next((True for ns in namespace_packages if package_path_s != ns and package_path_s.startswith(ns)), False)
            if inside_namespace:
                # Use the sub-package path as the module
                parsed_top_level.append(package_path)
            else:
                # Is this a namespace package? (`backports`)
                if bool(
                    file_path.name == '__init__.py' and
                    re.search(NAMESPACE_PACKAGE_PATTERN, (temp_install_dir / file_path).read_text())
                ):
                    # Mark this package path as a namespace package
                    namespace_packages.append(package_path_s)
                else:
                    # Use the left-most name (directory or file)
                    parsed_top_level.append(top_level_name)

    # Determine the main module and check how the name matches
    top_level: List[str] = []
    for name in parsed_top_level:
        # Skip already added
        if name in top_level:
            continue

        cur_path = temp_install_dir / name
        real_name = installed_pkg.project_name
        lower_name = real_name.lower()
        stripped_name = lower_name.replace('.', '')

        # If a directory:
        #   1. Top level package matches package name
        #      Example: `requests`
        #   2. Top level package matches package name, only when it's lowercase
        #      Example: `Mako`
        #   3. Top level package matches package name with stripped chars (case-insensitive)
        #      Example: name `bencode.py`, directory `bencodepy`

        # If a file:
        #   1. Top level package matches package name
        #      Example: name `six`, file `six.py`
        #   2. Top level package matches package name, only when it's lowercase
        #      Example: name `PackageName`, file `packagename.py` (it's rare?)

        if (
            name in (real_name, lower_name) or
            cur_path.is_file() and name[:-3] in (real_name, lower_name) or
            name.lower() == stripped_name
        ):
            top_level.insert(0, name)
        else:
            top_level.append(name)

    return top_level


def get_version_and_url(
    installed_pkg: AnyDistribution,
    parsed_package: Requirement,
    source_commit_hash: Optional[str],
) -> (str, str, bool, Optional[str]):
    """Get the installed package's version and url, and whether or not it's a git dependency."""
    is_git = bool(source_commit_hash)
    branch = None
    if is_git:
        match = None
        if parsed_package.url and 'github.com' in parsed_package.url:
            match = re.search(GITHUB_URL_PATTERN, parsed_package.url)
            url = 'https://github.com/{slug}/tree/{commit}'

        if not match:
            print(dedent("""
            ---------------------------------------------
                                    ERROR
            ---------------------------------------------
            Failed to parse the URL.
            Note that currently only GitHub is supported.
            ---------------------------------------------
            """))
            slug = 'unknown/unknown'
        else:
            groups: Mapping[str, str] = match.groupdict()
            slug = groups['slug']
            # If the extracted commit hash is different from the one in the provided URL,
            # we've been provided with a branch name.
            # Note: `HEAD` just points to the default branch, so it should not be marked.
            if source_commit_hash != groups['commit_ish'] and groups['commit_ish'] != 'HEAD':
                branch = groups['commit_ish']

        url = url.format(slug=slug, commit=source_commit_hash)
        version = source_commit_hash
    else:
        version = installed_pkg.version
        url = f'https://pypi.org/project/{installed_pkg.project_name}/{version}/'

    return version, url, is_git, branch
