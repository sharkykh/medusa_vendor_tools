# coding: utf-8
"""List outdated packages."""
import re
import sys
import time
from pathlib import Path
from typing import (
    List,
    Optional,
    Union,
)

import requests

from . import (
    __version__ as VERSION,
    parse
)
from .models import VendoredLibrary

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

    packages_lower = [p.lower() for p in packages]

    generator = parse.parse_requirements(listfile)

    # Types for the loop variables
    req: Optional[VendoredLibrary]
    error: Optional[parse.LineParseError]
    for req, error in generator:
        if packages and req.name.lower() not in packages_lower:
            continue

        if error:
            print(str(error), file=sys.stderr)
            continue

        wait = True
        current = req.version
        latest = None

        if req.git and req.url.startswith('https://github.com'):
            print(f'{req.name}: Checking GitHub...', end=' ')
            latest = find_latest_github(req)
        elif req.url.startswith('https://pypi.org'):
            print(f'{req.name}: Checking PyPI...', end=' ')
            latest = find_latest_pypi(req)
        else:
            print(f'{req.name}: Unknown origin, skipping')
            wait = False

        if latest and latest != current:
            print(f'Outdated [CUR: {current} != NEW: {latest}]')
        else:
            print('OK')

        if wait:
            time.sleep(0.3)


def find_latest_pypi(req: VendoredLibrary) -> str:
    response = session.get(f'https://pypi.org/pypi/{req.name.lower()}/json')
    response.raise_for_status()
    data = response.json()

    # Get latest version
    return data['info']['version']


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
