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

from pkg_resources import WorkingSet
from pkg_resources._vendor.packaging.requirements import InvalidRequirement, Requirement
# from pkg_resources._vendor.packaging.version import parse as parse_version

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
            installed['usage'] += [
                note for note in req['notes']
                if note not in installed['notes']
                and not note.startswith(('Module: ', 'File: '))
            ]

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

    print('Updating list')

    if req_idx is not None:
        pkg_ptrn = make_packages_pattern(requirements)
        before = make_list_item(requirements[req_idx], pkg_ptrn) + '\n'
        after = make_list_item(installed, pkg_ptrn) + '\n'
        print('Before / After:')
        print(''.join(
            ndiff([before], [after])
        ), end='')

        requirements[req_idx] = installed
    else:
        requirements.append(installed)

    md_data = make_md(requirements)

    with listpath.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(''.join(md_data))


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
    subprocess.call(args)
    print('----- [ pip | py%d ] -----' % (2 if py2 else 3))

    working_set = WorkingSet([str(vendor_dir)])  # Must be a list to work
    installed_pkg = working_set.by_key[parsed_package.name.lower()]

    dist_dir = Path(installed_pkg.egg_info)
    pkg_real_name = installed_pkg.project_name
    version = installed_pkg.version

    using = None
    checklist = [
        dist_dir / 'top_level.txt',
        dist_dir / 'RECORD',
    ]
    while using is None and checklist:
        checkpath = checklist.pop(0)
        try:
            with checkpath.open('r', encoding='utf-8') as fh:
                raw_top_level = fh.read().splitlines(keepends=False)
            using = checkpath.name
        except IOError:
            continue

    if not using:
        raise Exception('Unable to read module info')

    top_level = []
    has_lower_name = False
    has_real_name = False
    for ln in raw_top_level:
        if using == 'RECORD':
            name = ln.split(',', 1)[0].split('/', 1)[0]
        elif using == 'top_level.txt':
            name = ln
        if name.endswith(('.dist-info', '.egg-info')):
            continue
        if name in top_level or name + '.py' in top_level:
            continue
        if (vendor_dir / (name + '.py')).is_file():
            if name == parsed_package.name:
                has_lower_name = 'File'
                top_level.insert(0, name + '.py')
            elif name == pkg_real_name:
                has_real_name = 'File'
                top_level.insert(0, name + '.py')
            else:
                top_level.append(name + '.py')
        elif (vendor_dir / name).is_dir():
            if name == parsed_package.name:
                has_lower_name = 'Module'
                top_level.insert(0, name)
            elif name == pkg_real_name:
                has_real_name = 'Module'
                top_level.insert(0, name)
            else:
                top_level.append(name)

    # Notes
    notes = []
    if has_real_name:
        notes.append('%s: %s' % (has_real_name, top_level[0]))
    elif has_lower_name:
        pass
    else:
        # print('Unable to determine if package name == module')
        pass

    if not notes:
        notes = []

    # Dependencies
    dependencies = get_dependencies(installed_pkg, parsed_package)

    # Update version and url
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
        url = 'https://pypi.org/project/%s/%s/' % (pkg_real_name, version)

    result = OrderedDict()
    result['folder'] = [vendor_dir.name]
    result['package'] = pkg_real_name
    result['version'] = version
    result['modules'] = top_level
    result['git'] = is_git
    result['url'] = url
    result['usage'] = []
    result['notes'] = notes

    result['dependencies'] = dependencies

    drop_dir(dist_dir)

    # Drop the bin directory (contains easy_install, distro, chardetect etc.)
    # Might not appear on all OSes, so ignoring errors
    drop_dir(vendor_dir / 'bin', ignore_errors=True)

    remove_all(vendor_dir.glob('**/*.pyd'))

    # Drop interpreter and OS specific msgpack libs.
    # Pip will rely on the python-only fallback instead.
    remove_all(vendor_dir.glob('msgpack/*.so'))

    return result


def get_dependencies(installed_pkg, parsed_package):
    raw_metadata = installed_pkg.get_metadata(installed_pkg.PKG_INFO)
    metadata = email.parser.Parser().parsestr(raw_metadata)

    deps = []
    for meta_line in metadata.get_all('Requires-Dist'):
        # Requires-Dist: chardet (<3.1.0,>=3.0.2)
        # Requires-Dist: win-inet-pton; (sys_platform == "win32" and python_version == "2.7") and extra == 'socks'
        # Requires-Dist: funcsigs; python_version == "2.7"
        req = Requirement(meta_line)

        def eval_extra(extra, python_version):
            return req.marker.evaluate({'extra': extra, 'python_version': python_version})

        extras = parsed_package.extras
        eval_py27 = req.marker and any(eval_extra(ex, '2.7') for ex in extras)
        eval_py35 = req.marker and any(eval_extra(ex, '3.5') for ex in extras)
        if not req.marker or eval_py27 or eval_py35:
            deps.append(req)

    return deps


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
