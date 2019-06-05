#!/usr/bin/env python3
# coding: utf-8
"""Vendor (or update existing) libraries."""
import email.parser
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict
from contextlib import suppress
from difflib import ndiff
from pathlib import Path
from textwrap import dedent

from pkg_resources import WorkingSet, EggInfoDistribution
from pkg_resources._vendor.packaging.requirements import InvalidRequirement, Requirement
from pkg_resources._vendor.packaging.markers import Marker
# from pkg_resources._vendor.packaging.version import parse as parse_version

from gen_requirements import (
    main as gen_requirements
)

from parse_md import (
    LineParseError,
    parse_requirements,
)
from make_md import (
    make_md,
    make_packages_pattern,
    make_list_item,
)

# https://github.com/:owner/:repo@eea9ac18e38c930230cf81b5dca4a9af9fb10d4e
# https://github.com/:owner/:repo.git@eea9ac18e38c930230cf81b5dca4a9af9fb10d4e
# https://codeload.github.com/:owner/:repo/tar.gz/eea9ac18e38c930230cf81b5dca4a9af9fb10d4e
# Not perfect, but close enough? Can't handle branches ATM anyway
GITHUB_URL_PATTERN = re.compile(r'github.com/(?P<slug>.+?/.+?)(?:\.git@|/tar\.gz/)?(?P<commit>[a-f0-9]{40})/?', re.IGNORECASE)

DEFAULT_LISTFILE = 'ext/readme.md'


def make_list_of_folders(target, py2, py3):
    install_folders = []
    if not py2 and not py3:  # normal
        install_folders.append(target)
    else:  # if both, separate codebase for each major version
        if py2:  # py2 only
            install_folders.append(target + '2')
        if py3:  # py3 only
            install_folders.append(target + '3')
    return install_folders


def main(listfile, package, py2, py3):
    listpath = Path(listfile)
    root = listpath.parent.parent.absolute()

    # Parse package name / version specifier from argument
    try:
        parsed_package = Requirement(package)
        package_name = parsed_package.name
        specifier = str(parsed_package.specifier)
    except InvalidRequirement:
        egg_value = re.search(r'#egg=(.+)(?:&|$)', package)
        if egg_value:
            parsed_package = Requirement(egg_value.group(1))
            package_name = parsed_package.name
            specifier = str(parsed_package.specifier)
        else:
            raise ValueError('Unable to parse {}'.format(package))

    print('Starting vendor script for: {}'.format(package_name + specifier))

    # Remove old folder(s)/file(s) first using info from `ext/readme.md`
    requirements = [req for req, _ in parse_requirements(listfile)]
    req_idx = next(
        (i for (i, req) in enumerate(requirements) if package_name.lower() == req['package'].lower()),
        None
    )
    if req_idx is not None:
        req = requirements[req_idx]

        package_modules = [
            (root / f / mod)
            for mod in req['modules']
            for f in req['folder']
        ]
        print('Removing:', package_modules)
        try:
            remove_all(package_modules)
        except OSError:
            pass

        if not py2 and not py3:
            print('Package %s found in list, using that' % package_name)
            install_folders = req['folder']
        else:
            print('Installing %s as a new package due to CLI switches' % package_name)
            target = req['folder'][0].strip('23')
            install_folders = make_list_of_folders(target, py2, py3)
    else:
        if py2 or py3:
            print('Installing %s as a new package due to CLI switches' % package_name)
        else:
            print('Package %s not found in list, assuming new package' % package_name)

        target = listpath.parent.name  # ext | lib
        install_folders = make_list_of_folders(target, py2, py3)

    installed = None
    for f in install_folders:
        installed = vendor(root / f, package, parsed_package, py2=f.endswith('2'))

        print('Installed: %s==%s to %s' % (
            installed['package'], installed['version'], f
        ))

    installed['folder'] = install_folders

    if req_idx is not None:
        installed['usage'] = req['usage']
        if req['notes']:
            installed['notes'] += req['notes']
    else:
        installed['usage'] = ['<UPDATE-ME>']

    print('+++++++++++++++++++++')
    print('+ Dependency checks +')
    print('+-------------------+')

    dependencies = installed.pop('dependencies', [])
    dep_names = [d.name.lower() for d in dependencies]
    req_names = [r['package'].lower() for r in requirements]

    # Check if a dependency of a previous version is not needed now and remove it
    installed_pkg_lower = installed['package'].lower()
    for idx, r in enumerate(requirements):
        r_pkg_lower = r['package'].lower()

        usage_lower = list(map(str.lower, r['usage']))
        if installed_pkg_lower in usage_lower and r_pkg_lower not in dep_names:
            idx = usage_lower.index(installed_pkg_lower)
            r['usage'].pop(idx)
            print('Removed `{0}` usage from dependency `{1}`'.format(installed['package'], r['package']))

    # Check that the dependencies are installed (partial),
    #   and that their versions match the new specifier (also partial)
    deps_csv = ', '.join(map(str, dependencies)) or 'no dependencies'
    print('Package {0} depends on: {1}'.format(installed['package'], deps_csv))
    for d in dependencies:
        d_pkg_lower = d.name.lower()
        if d_pkg_lower not in req_names:
            text = 'May need to install new dependency `{0}` @ {1}'.format(d.name, str(d.specifier) or 'any version')
            if d.marker:
                text += ', but only for {}'.format(str(d.marker))
            print(text)
            continue
        idx = req_names.index(d_pkg_lower)
        dep_req = requirements[idx]
        # ver = parse_version(dep_req['version'])
        ver = dep_req['version']
        if ver not in d.specifier:
            if dep_req['git']:
                print('May need to update {0} (git dependency) to match specifier: {1}'.format(dep_req['package'], d.specifier))
            else:
                print('Need to update {0} from {1} to match specifier: {2}'.format(dep_req['package'], ver, d.specifier))
        if installed_pkg_lower not in map(str.lower, dep_req['usage']):
            print('Adding {0} to the "usage" column of {1}'.format(installed['package'], dep_req['package']))
            dep_req['usage'].append(installed['package'])

    print('+++++++++++++++++++++')

    print('Updating {0}'.format(listpath.name))

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


def drop_dir(path, **kwargs):
    shutil.rmtree(str(path), **kwargs)


def remove_all(paths):
    for path in paths:
        if path.is_dir():
            drop_dir(path)
        else:
            path.unlink()


def vendor(vendor_dir, package, parsed_package, py2=False):
    print('Installing vendored library `%s` to `%s`' % (parsed_package.name, vendor_dir.name))

    # We use `--no-deps` because we want to ensure that all of our dependencies are added to the list.
    # This includes all dependencies recursively up the chain.
    prog = [sys.executable] if not py2 else ['py', '-2.7']
    args = prog + [
        '-m', 'pip', 'install', '-t', str(vendor_dir), package,
        '--no-compile', '--no-deps', '--upgrade',
    ] + (['--progress-bar', 'off'] if py2 else [])

    print('+++++ [ pip | py%d ] +++++' % (2 if py2 else 3))
    pip_result = subprocess.call(args)
    print('----- [ pip | py%d ] -----' % (2 if py2 else 3))

    if pip_result != 0:
        raise Exception('Pip failed')

    working_set = WorkingSet([str(vendor_dir)])  # Must be a list to work
    installed_pkg = working_set.by_key[parsed_package.name.lower()]

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

    # Drop the bin directory (contains easy_install, distro, chardetect etc.)
    # Might not appear on all OSes, so ignoring errors
    drop_dir(vendor_dir / 'bin', ignore_errors=True)

    remove_all(vendor_dir.glob('**/*.pyd'))

    # Drop interpreter and OS specific msgpack libs.
    # Pip will rely on the python-only fallback instead.
    remove_all(vendor_dir.glob('msgpack/*.so'))

    return result


def get_modules(vendor_dir, installed_pkg, parsed_package):
    using = None
    checklist = [
        'top_level.txt',
        'RECORD',
    ]
    while using is None and checklist:
        checkpath = checklist.pop(0)
        try:
            raw_top_level = installed_pkg.get_metadata(checkpath).splitlines(keepends=False)
            using = checkpath
        except IOError:
            pass

    if not using:
        raise Exception('Unable to read module info')

    # Make a simple list of top level directories / file names
    parsed_top_level = []
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
    top_level = []
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


def get_dependencies(installed_pkg, parsed_package):
    raw_metadata = installed_pkg.get_metadata(installed_pkg.PKG_INFO)
    metadata = email.parser.Parser().parsestr(raw_metadata)

    if isinstance(installed_pkg, EggInfoDistribution):
        requires = []
        for extra, reqs in installed_pkg._dep_map.items():
            if extra is None:
                requires.extend(reqs)
            else:
                for req in reqs:
                    old_marker = ''
                    if req.marker:
                        old_marker = '({0}) and '.format(req.marker)
                    req.marker = Marker(old_marker + "extra == '{0}'".format(extra))
                    requires.append(req)
    else:
        requires = metadata.get_all('Requires-Dist') or []

    deps = []
    for req in requires:
        # Requires-Dist: chardet (<3.1.0,>=3.0.2)
        # Requires-Dist: win-inet-pton; (sys_platform == "win32" and python_version == "2.7") and extra == 'socks'
        # Requires-Dist: funcsigs; python_version == "2.7"
        if isinstance(req, str):
            req = Requirement(req)

        def eval_extra(extra, python_version):
            return req.marker.evaluate({'extra': extra, 'python_version': python_version})

        extras = [None] + list(parsed_package.extras)
        eval_py27 = req.marker and any(eval_extra(ex, '2.7') for ex in extras)
        eval_py35 = req.marker and any(eval_extra(ex, '3.5') for ex in extras)
        if not req.marker or eval_py27 or eval_py35:
            deps.append(req)

    return deps


def get_version_and_url(package, installed_pkg):
    if 'github.com' in package:
        is_git = True
        match = GITHUB_URL_PATTERN.search(package)
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
            groups = match.groupdict()
            url = url.format(**groups)
            version = groups['commit']
    else:
        is_git = False
        version = installed_pkg.version
        url = 'https://pypi.org/project/%s/%s/' % (installed_pkg.project_name, version)

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
