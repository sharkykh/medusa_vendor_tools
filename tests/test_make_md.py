import json
from pathlib import Path

import pytest

from mvt import models, make_md

with Path(__file__).parent.joinpath('fixtures/data.json').open('r', encoding='utf-8') as fh:
    json_data = json.load(fh)
    json_data_dict = {
        item['name'].lower(): item
        for item in json_data
    }

with Path(__file__).parent.joinpath('fixtures/data.md').open('r', encoding='utf-8') as fh:
    md_contents: str = fh.read()


@pytest.mark.parametrize('p', [
    {  # p0
        'value': models.VendoredLibrary.from_json(json_data_dict['cachecontrol']),
        'expected': (
            'ext | `CacheControl` | [0.12.6](https://pypi.org/project/CacheControl/0.12.6/)'
            ' | **`medusa`** | Module: `cachecontrol`'
        )
    },
    {  # p1
        'value': models.VendoredLibrary.from_json(json_data_dict['beautifulsoup4']),
        'expected': (
            '**ext2 ext3** | `beautifulsoup4[html5lib]` | [4.9.1](https://pypi.org/project/beautifulsoup4/4.9.1/)'
            ' | **`medusa`**, `subliminal` | Module: `bs4`'
        )
    },
    {  # p2
        'value': models.VendoredLibrary.from_json(json_data_dict['html5lib']),
        'expected': (
            'ext | **`html5lib`** | [1.1](https://pypi.org/project/html5lib/1.1/)'
            ' | **`medusa`** (via `beautifulsoup4`), `beautifulsoup4` | -'
        )
    },
    {  # p3
        'value': models.VendoredLibrary.from_json(json_data_dict['subliminal']),
        'expected': (
            'ext | **`subliminal`** | [develop@76525cc](https://github.com/Diaoul/subliminal/tree/'
            '76525cc2f6545aeeccf620ca46d40c2f0aa53c6d) | **`medusa`** | -'
        )
    },
    {  # p4
        'value': models.VendoredLibrary.from_json(json_data_dict['pytimeparse']),
        'expected': (
            'ext | **`pytimeparse`** | pymedusa/[8f28325](https://github.com/pymedusa/pytimeparse/tree/'
            '8f2832597235c6ec98c44de4dab3274927f67e29) | **`medusa`** | -'
        )
    },
    {  # p5
        'value': models.VendoredLibrary.from_json(json_data_dict['configobj']),
        'expected': (
            'ext | `configobj` | [5.0.6](https://pypi.org/project/configobj/5.0.6/) | **`medusa`**'
            ' | Modules: `configobj.py`, `validate.py`, `_version.py`'
        )
    },
    {  # p6
        'value': models.VendoredLibrary.from_json(json_data_dict['ttl-cache']),
        'expected': (
            'ext | `ttl-cache` | [1.6](https://pypi.org/project/ttl-cache/1.6/) | **`medusa`** | File: `ttl_cache.py`'
        )
    },
    {  # p7
        'value': models.VendoredLibrary.from_json(json_data_dict['zzz-not-a-package']),
        'expected': (
            'ext | `zzz-not-a-package` | - | `<UNUSED>` | Module: `my_module`'
        )
    },
    {  # p8
        'value': models.VendoredLibrary.from_json(json_data_dict['zzz-single-file-from-github']),
        'expected': (
            'ext | `zzz-single-file-from-github` | [abcdef0](https://github.com/owner/repo/blob/'
            'abcdef0123456789abcdef0123456789abcdef01/path/to/my_file.py) | `<UPDATE-ME>` | File: `my_file.py`'
        )
    },
])
def test_make_list_item(p):
    value = p['value']
    expected = p['expected']

    actual = make_md.make_list_item(value)
    assert actual == expected


def test_make_md():
    reqs = models.VendoredList.from_json(json_data)
    actual = make_md.make_md(reqs).splitlines(keepends=True)
    expected = md_contents.splitlines(keepends=True)

    assert actual == expected
