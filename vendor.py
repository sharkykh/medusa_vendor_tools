#!/usr/bin/env python3
# coding: utf-8
"""Vendor (or update existing) libraries."""
import email.parser
import re
import shutil
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from textwrap import dedent
from typing import (
    List,
    Mapping,
    Match,
    Optional,
    Pattern,
    Union,
)

import pkg_resources
from pkg_resources._vendor.packaging.requirements import InvalidRequirement, Requirement
from pkg_resources._vendor.packaging.markers import Marker
# from pkg_resources._vendor.packaging.version import parse as parse_version

import parse_md
from gen_requirements import main as gen_requirements
from make_md import make_md

# Typing
AnyDistribution = Union[
    pkg_resources.Distribution,
    pkg_resources.DistInfoDistribution,
    pkg_resources.EggInfoDistribution
]


# https://github.com/:owner/:repo@eea9ac18e38c930230cf81b5dca4a9af9fb10d4e
# https://github.com/:owner/:repo.git@eea9ac18e38c930230cf81b5dca4a9af9fb10d4e
# https://codeload.github.com/:owner/:repo/tar.gz/eea9ac18e38c930230cf81b5dca4a9af9fb10d4e
# Not perfect, but close enough? Can't handle branches ATM anyway
GITHUB_URL_PATTERN: Pattern = re.compile(r'github.com/(?P<slug>.+?/.+?)/.+/(?P<commit>[a-f0-9]{40})/?', re.IGNORECASE)

DEFAULT_LISTFILE = 'ext/readme.md'


def main(listfile: str, package: str, py2: bool, py3: bool) -> None:
    listpath = Path(listfile)
    root = listpath.parent.parent.absolute()

    # Parse package name / version constraint from argument
    parsed_package = parse_input(package)
    package_name: str = parsed_package.name

    print(f'Starting vendor script for: {package_name}{parsed_package.specifier!s}')
    if parsed_package.extras:
        csv_extras = ','.join(parsed_package.extras)
        print('=' * 60)
        print(f'You provided a package with extra(s) ({package_name}[{csv_extras}]).')
        print('Please note that extras can not be expressed on the lists!')
        print('=' * 60)
        if input('Press ENTER to continue (to abort - type anything and then press ENTER)'):
            return

    # Get requirements from list, try to find the package we're vendoring right now
    requirements, req_idx = load_requirements(listpath, package_name)

    if req_idx is not None:
        req = requirements[req_idx]

        # Remove old folder(s)/file(s) first using info from `ext/readme.md`
        package_modules: List[Path] = [
            (root / folder / module)
            for module in req['modules']
            for folder in req['folder']
        ]
        modules_csv = ', '.join(map(str, package_modules))
        print(f'Removing: [{modules_csv}]')
        try:
            remove_all(package_modules)
        except OSError:
            pass

        if not py2 and not py3:
            print(f'Package {package_name} found in list, using that')
            install_folders = req['folder']
        else:
            print(f'Installing {package_name} to targets according to CLI switches')
            target = req['folder'][0].strip('23')
            install_folders = make_list_of_folders(target, py2, py3)
    else:
        print(f'Package {package_name} not found in list, assuming new package')

        target = listpath.parent.name  # ext | lib
        install_folders = make_list_of_folders(target, py2, py3)

    installed = None
    for folder in install_folders:
        installed = vendor(root / folder, package, parsed_package, py2=folder.endswith('2'))

        print(f'Installed: {installed["package"]}=={installed["version"]} to {folder}')

    installed['folder'] = install_folders

    if req_idx is not None:
        installed['usage'] = req['usage']
        if req['notes']:
            installed['notes'] += req['notes']
    else:
        installed['usage'] = ['<UPDATE-ME>']

    # Dependency checks
    run_dependency_checks(installed, requirements)

    readme_name = '/'.join(listpath.absolute().parts[-2:])
    print(f'Updating {readme_name}')

    if req_idx is not None:
        requirements[req_idx] = installed
    else:
        requirements.append(installed)

    md_data = make_md(requirements)

    with listpath.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(''.join(md_data))

    print('Updating requirements.txt')
    reqs_file = root / 'requirements.txt'
    gen_requirements(
        infile=str(listpath.absolute()),
        outfile=str(reqs_file.absolute()),
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

    egg_value = re.search(r'#egg=(.+)(?:&|$)', package)
    if not egg_value:
        raise ValueError(f'Unable to parse {package}')

    return Requirement(egg_value.group(1))


def load_requirements(listpath: Path, package_name: str) -> (List[OrderedDict], Optional[int]):
    """Get requirements from list, try to find the package we're vendoring right now."""
    requirements: List[OrderedDict] = []
    req_idx: Optional[int] = None

    absolute_path = str(listpath.absolute())
    generator = parse_md.parse_requirements(absolute_path)

    package_name_lower = package_name.lower()
    # Types for the loop variables
    index: int
    req: Optional[OrderedDict]
    error: Optional[parse_md.LineParseError]
    for index, (req, error) in enumerate(generator):
        if error:
            raise error
        requirements.append(req)

        if package_name_lower == req['package'].lower():
            req_idx = index

    return requirements, req_idx


def make_list_of_folders(target: str, py2: bool, py3: bool) -> List[str]:
    """Generate a list of target folders based on targeted Python versions."""
    install_folders: List[str] = []
    if not py2 and not py3:  # if neither, normal
        install_folders.append(target)
    else:  # if either one, or both, target for each major version
        if py2:  # py2 only
            install_folders.append(target + '2')
        if py3:  # py3 only
            install_folders.append(target + '3')
    return install_folders


def run_dependency_checks(installed: OrderedDict, requirements: List[OrderedDict]) -> None:
    """
    Run dependency checks.
    - Check if a dependency of a previous version is not needed now and remove it
    - Check that the dependencies are installed (partial),
        and that their versions match the new specifier (also partial)

    Note: May mutate items of `requirements`.
    """
    print('+++++++++++++++++++++')
    print('+ Dependency checks +')
    print('+-------------------+')

    dependencies: List[Requirement] = installed.pop('dependencies', [])
    installed_pkg_name: str = installed['package']
    installed_pkg_lower = installed_pkg_name.lower()

    deps_csv = ', '.join(map(str, dependencies)) or 'no dependencies'
    print(f'Package {installed_pkg_name} depends on: {deps_csv}')

    # Check if a dependency of a previous version is not needed now and remove it
    dep_names: List[str] = [d.name.lower() for d in dependencies]
    for idx, req in enumerate(requirements):
        req_name = req['package']
        usage_lower = list(map(str.lower, req['usage']))

        if installed_pkg_lower in usage_lower and req_name.lower() not in dep_names:
            idx = usage_lower.index(installed_pkg_lower)
            req['usage'].pop(idx)
            print(f'Removed `{installed_pkg_name}` usage from dependency `{req_name}`')

    # Check that the dependencies are installed (partial),
    #   and that their versions match the new specifier (also partial)
    req_names: List[str] = [r['package'].lower() for r in requirements]
    for dep in dependencies:
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
        dep_req_name = dep_req['package']
        dep_req_ver = dep_req['version']  # parse_version(dep_req['version'])
        if dep_req_ver not in dep.specifier:
            if dep_req['git']:
                print(f'May need to update {dep_req_name} (git dependency) to match specifier: {dep.specifier}')
            else:
                print(f'Need to update {dep_req_name} from {dep_req_ver} to match specifier: {dep.specifier}')

        if installed_pkg_lower not in map(str.lower, dep_req['usage']):
            print(f'Adding {installed_pkg_name} to the "usage" column of {dep_req_name}')
            dep_req['usage'].append(installed_pkg_name)

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


def vendor(vendor_dir: Path, package: str, parsed_package: Requirement, py2: bool = False) -> OrderedDict:
    """Install `package` into `vendor_dir` using pip, and return a vendored package object."""
    print(f'Installing vendored library `{parsed_package.name}` to `{vendor_dir.name}`')

    # We use `--no-deps` because we want to ensure that all of our dependencies are added to the list.
    # This includes all dependencies recursively up the chain.
    executable = 'py'
    args: List[str] = [
        executable,  # Use the Windows launcher
        '-3' if not py2 else '-2.7',
        '-m', 'pip', 'install', '--no-compile', '--no-deps', '--upgrade',
    ]
    if py2:
        # Some versions of pip for Python 2.7 on Windows have an issue where the progress bar can fail the install
        args += ['--progress-bar', 'off']
    args += ['--target', str(vendor_dir), package]

    major_version = 2 if py2 else 3

    print(f'+++++ [ pip | py{major_version} ] +++++')
    pip_result = subprocess.call(args)
    print(f'----- [ pip | py{major_version} ] -----')

    if pip_result != 0:
        raise Exception('Pip failed')

    # Drop the bin directory (contains easy_install, distro, chardetect etc.)
    # Might not appear on all OSes, so ignoring errors
    drop_dir(vendor_dir / 'bin', ignore_errors=True)

    # Drop interpreter and OS specific files.
    remove_all(vendor_dir.glob('**/*.pyd'))
    remove_all(vendor_dir.glob('msgpack/*.so'))

    # Get installed package
    working_set = pkg_resources.WorkingSet([str(vendor_dir)])  # Must be a list to work
    installed_pkg: AnyDistribution = working_set.by_key[parsed_package.name.lower()]

    # Modules
    modules = get_modules(vendor_dir, installed_pkg, parsed_package)

    # Dependencies
    dependencies = get_dependencies(installed_pkg, parsed_package)

    # Update version and url
    version, url, is_git = get_version_and_url(package, installed_pkg)

    result = OrderedDict()
    result['folder'] = [vendor_dir.name]
    result['package'] = installed_pkg.project_name
    result['version'] = version
    result['modules'] = modules
    result['git'] = is_git
    result['url'] = url
    result['usage'] = []
    result['notes'] = []

    result['dependencies'] = dependencies

    # Remove the package info folder
    drop_dir(Path(installed_pkg.egg_info))

    return result


def get_modules(vendor_dir: Path, installed_pkg: AnyDistribution, parsed_package: Requirement) -> List[str]:
    """Get a list of all the top-level modules/files names, with the "main" module being the first."""
    using: str = None
    checklist: List[str] = [
        'top_level.txt',
        'RECORD',
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
    for ln in raw_top_level:
        if using == 'top_level.txt':
            name = ln
            if (vendor_dir / (name + '.py')).is_file():
                name += '.py'
            parsed_top_level.append(name)
        elif using == 'RECORD':
            # six-1.12.0.dist-info/top_level.txt,sha256=_iVH_iYEtEXnD8nYGQYpYFUvkUW9sEO1GYbkeKSAais,4
            # six.py,sha256=h9jch2pS86y4R36pKRS3LOYUCVFNIJMRwjZ4fJDtJ44,32452
            # setuptools/wheel.py,sha256=94uqXsOaKt91d9hW5z6ZppZmNSs_nO66R4uiwhcr4V0,8094

            # Get the left-most name (directory or file) of the left-most item
            name = ln.split(',', 1)[0].split('/', 1)[0]
            if name.endswith(('.dist-info', '.egg-info')):
                continue
            parsed_top_level.append(name)

    # Determine the main module and check how the name matches
    top_level: List[str] = []
    for name in parsed_top_level:
        # Skip already added
        if name in top_level:
            continue

        cur_path = vendor_dir / name
        real_name = installed_pkg.project_name
        lower_name = installed_pkg.project_name.lower()

        # If a directory:
        #   1. Top level package matches package name
        #      Example: requests
        #   2. Top level package matches package name, only when it's lowercase
        #      Example: Mako

        # If a file:
        #   1. Top level package matches package name
        #      Example: six[.py]
        #   2. Top level package matches package name, only when it's lowercase
        #      Example: PackageName[.py] (it's rare?)

        if name in (real_name, lower_name) or cur_path.is_file() and name[:-3] in (real_name, lower_name):
            top_level.insert(0, name)
        else:
            top_level.append(name)

    return top_level


def get_dependencies(installed_pkg: AnyDistribution, parsed_package: Requirement) -> List[Requirement]:
    """Get a list of all the installed package dependencies."""
    raw_metadata = installed_pkg.get_metadata(installed_pkg.PKG_INFO)
    metadata = email.parser.Parser().parsestr(raw_metadata)

    if isinstance(installed_pkg, pkg_resources.EggInfoDistribution):
        requires = []
        for extra, reqs in installed_pkg._dep_map.items():
            if extra is None:
                requires.extend(reqs)
            else:
                for req in reqs:
                    old_marker = ''
                    if req.marker:
                        old_marker = f'({req.marker}) and '
                    req.marker = Marker(old_marker + f"extra == '{extra}'")
                    requires.append(req)
    else:
        requires = metadata.get_all('Requires-Dist') or []

    deps: List[Requirement] = []
    for req in requires:
        # Requires-Dist: chardet (<3.1.0,>=3.0.2)
        # Requires-Dist: win-inet-pton; (sys_platform == "win32" and python_version == "2.7") and extra == 'socks'
        # Requires-Dist: funcsigs; python_version == "2.7"
        if isinstance(req, str):
            req = Requirement(req)

        def eval_extra(extra: Optional[str], python_version: str) -> bool:
            return req.marker.evaluate({'extra': extra, 'python_version': python_version})

        extras = [None] + list(parsed_package.extras)
        eval_py27 = req.marker and any(eval_extra(ex, '2.7') for ex in extras)
        eval_py35 = req.marker and any(eval_extra(ex, '3.5') for ex in extras)
        if not req.marker or eval_py27 or eval_py35:
            deps.append(req)

    return deps


def get_version_and_url(package: str, installed_pkg: AnyDistribution) -> (str, str, bool):
    """Get the installed package's version and url, and whether or not it's a git dependency."""
    if 'github.com' in package:
        is_git = True
        match: re.Match = GITHUB_URL_PATTERN.search(package)
        url = 'https://github.com/{slug}/tree/{commit}'
        if not match:
            print(dedent("""
            -----------------------------------------------------
                                    ERROR
            -----------------------------------------------------
            Failed to parse the URL from repo and commit hash
            Be sure to include the commit hash in the install URL
            -----------------------------------------------------
            """))
            # Put some random data so the script doesn't fail to parse the line
            from hashlib import sha1
            version = sha1(b'commit').hexdigest()
            url = url.format(slug='unknown/unknown', commit=version)
        else:
            groups: Mapping[str, str] = match.groupdict()
            url = url.format(**groups)
            version = groups['commit']
    else:
        is_git = False
        version = installed_pkg.version
        url = f'https://pypi.org/project/{installed_pkg.project_name}/{version}/'

    return version, url, is_git


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Vendor package')
    parser.add_argument('package', help='Package to vendor')
    parser.add_argument('-2', '--py2', action='store_true', help='Install Python 2 version to ext2')
    parser.add_argument('-3', '--py3', action='store_true', help='Install Python 3 version to ext3')
    parser.add_argument('-i', '--listfile', default=DEFAULT_LISTFILE,
                        help='List file to update (affects target folders). Defaults to `ext/readme.md`')

    args = parser.parse_args()

    main(**args.__dict__)
