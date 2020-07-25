# coding: utf-8
"""List outdated packages."""
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import (
    Callable,
    Dict,
    List,
    Union
)

import requests

from . import __version__ as VERSION
from .models import VendoredLibrary
from .parse import parse_requirements


try:
    from pkg_resources._vendor.packaging.specifiers import SpecifierSet
except ImportError:
    SpecifierSet = None


GITHUB_URL_PATTERN = re.compile(r'github\.com/(?P<slug>.+?/.+?)/', re.IGNORECASE)
session = requests.Session()
session.headers.update({
    'Accept': 'application/json',
    'User-Agent': f'mvt/{VERSION}'
})


def outdated(listfile: Union[Path, str], packages: List[str]) -> None:
    if not isinstance(listfile, Path):
        listfile = Path(listfile)

    root = listfile.parent.parent.resolve()

    renovate_config = get_renovate_config(root)

    packages_lower = [p.lower() for p in packages]

    for req, error in parse_requirements(listfile):
        name_lower = req.name.lower()
        if packages and name_lower not in packages_lower:
            continue

        if error:
            print(str(error), file=sys.stderr)
            continue

        wait = True
        current = req.version
        latest = None
        constraint = renovate_config.get(name_lower, None)

        if req.git and req.url.startswith('https://github.com'):
            print(f'{req.name}: Checking GitHub...', end=' ')
            latest = find_latest_github(req)
        elif req.url.startswith('https://pypi.org'):
            print(f'{req.name}: Checking PyPI...', end=' ')
            latest = find_latest_pypi(req, constraint)
        else:
            print(f'{req.name}: Unknown origin, skipping')
            wait = False

        if latest and latest != current:
            print(f'Outdated [CUR: {current} != NEW: {latest}]')
        else:
            print('OK')

        if wait:
            time.sleep(0.3)


def find_latest_pypi(req: VendoredLibrary, constraint: SpecifierSet) -> str:
    response = session.get(f'https://pypi.org/pypi/{req.name.lower()}/json')
    response.raise_for_status()
    data = response.json()

    if not constraint:
        # Get latest version
        return data['info']['version']

    releases: List[str] = sorted(
        data['releases'].keys(),
        key=pypi_releases_sort_key(data['releases']),
        reverse=True,
    )

    for release in releases:
        if release in constraint:
            return release

    # Unable to find version matching constraint, using latest
    return data['info']['version']


def pypi_releases_sort_key(releases_data: Dict[str, List[dict]]) -> Callable[[str], datetime]:
    def _sort_key(release: str) -> datetime:
        try:
            return datetime.fromisoformat(
                releases_data[release][0]['upload_time']
            )
        except IndexError:
            return datetime.min

    return _sort_key


def find_latest_github(req: VendoredLibrary) -> str:
    match = GITHUB_URL_PATTERN.search(req.url)
    slug = match.group(1)
    head = req.branch or 'HEAD'
    url = f'https://api.github.com/repos/{slug}/compare/{req.version}...{head}'

    response = session.get(
        url,
        params={'per_page': 100},
        headers={'Accept': 'application/vnd.github.v3+json'},
    )
    response.raise_for_status()
    data = response.json()

    # Get latest hash
    status = data['status']
    if status == 'ahead':
        return data['commits'][-1]['sha']
    if status == 'identical':
        return data['base_commit']['sha']
    return f'Unknown - different branch? (status: {status})'


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
