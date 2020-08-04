from pathlib import Path

import pytest

from mvt import models, parse

from tests import raises_if_provided


@pytest.mark.parametrize('p', [
    {  # p0
        'value': (
            "ext | **`babelfish`** | [f403000](https://github.com/Diaoul/babelfish/tree/f403000dd63092cfaaae80be9f309f"
            "d85c7f20c9) | **`medusa`**, `guessit`, `knowit`, `subliminal` | -"
        ),
        'expected': [
            'ext',
            '**`babelfish`**',
            '[f403000](https://github.com/Diaoul/babelfish/tree/f403000dd63092cfaaae80be9f309fd85c7f20c9)',
            '**`medusa`**, `guessit`, `knowit`, `subliminal`',
            '-',
        ],
    },
    {  # p1
        'value': 'not | enough | columns',
        'expected': None,
        'raises': parse.ParseFailed,
    },
])
def test_split_columns(p):
    value = p['value']
    expected = p['expected']
    raises = p.get('raises')

    with raises_if_provided(raises):
        actual = parse._split_columns(value)
        assert actual == expected


@pytest.mark.parametrize('p', [
    {  # p0
        'value': '**ext2 ext3**',
        'expected': [
            'ext2',
            'ext3',
        ],
    },
    {  # p1
        'value': '',
        'expected': None,
        'raises': parse.ParseFailed,
    },
])
def test_parse_folder(p):
    value = p['value']
    expected = p['expected']
    raises = p.get('raises')

    with raises_if_provided(raises):
        actual = parse._parse_folder(value)
        assert actual == expected


@pytest.mark.parametrize('p', [
    {  # p0
        'value': '**`requests`**',
        'expected': tuple([
            'requests',
            [],
        ]),
    },
    {  # p1
        'value': '`beautifulsoup4[html5lib,lxml]`',
        'expected': tuple([
            'beautifulsoup4',
            [
                'html5lib',
                'lxml',
            ],
        ]),
    },
    {  # p2
        'value': '$ad^ba/',
        'expected': None,
        'raises': parse.ParseFailed,
    },
])
def test_parse_package(p):
    value = p['value']
    expected = p['expected']
    raises = p.get('raises')

    with raises_if_provided(raises):
        actual = parse._parse_package(value)
        assert actual == expected


@pytest.mark.parametrize('p', [
    {  # p0
        'value': '-',
        'expected': tuple([
            None,
            None,
            False,
            None,
        ]),
    },
    {  # p1
        'value': '[2.8.1](https://pypi.org/project/python-dateutil/2.8.1/)',
        'expected': tuple([
            '2.8.1',
            'https://pypi.org/project/python-dateutil/2.8.1/',
            False,
            None,
        ]),
    },
    {  # p2
        'value': '[f403000](https://github.com/Diaoul/babelfish/tree/f403000dd63092cfaaae80be9f309fd85c7f20c9)',
        'expected': tuple([
            None,
            'https://github.com/Diaoul/babelfish/tree/f403000dd63092cfaaae80be9f309fd85c7f20c9',
            True,
            None,
        ]),
    },
    {  # p3
        'value': (
            '[develop@76525cc](https://github.com/Diaoul/subliminal/tree/76525cc2f6545aeeccf620ca46d40c2f0aa53c6d)'
        ),
        'expected': tuple([
            None,
            'https://github.com/Diaoul/subliminal/tree/76525cc2f6545aeeccf620ca46d40c2f0aa53c6d',
            True,
            'develop',
        ]),
    },
    {  # p4
        'value': (
            'pymedusa/[develop@6efeff3](https://github.com/pymedusa/adba/tree/6efeff3a6bdcb6d45a4a79f424939ade2930e5f0)'
        ),
        'expected': tuple([
            None,
            'https://github.com/pymedusa/adba/tree/6efeff3a6bdcb6d45a4a79f424939ade2930e5f0',
            True,
            'develop',
        ]),
    },
    {  # p5
        'value': '[]()',
        'expected': None,
        'raises': parse.ParseFailed,
    },
])
def test_parse_version(p):
    value = p['value']
    expected = p['expected']
    raises = p.get('raises')

    with raises_if_provided(raises):
        actual = parse._parse_version(value)
        assert actual == expected


@pytest.mark.parametrize('p', [
    {  # p0
        'value': 'https://github.com/Diaoul/subliminal/tree/76525cc2f6545aeeccf620ca46d40c2f0aa53c6d',
        'expected': '76525cc2f6545aeeccf620ca46d40c2f0aa53c6d',
    },
    {  # p1
        'value': 'http://example.com',
        'expected': None,
        'raises': parse.ParseFailed,
    },
])
def test_parse_url_for_commit_hash(p):
    value = p['value']
    expected = p['expected']
    raises = p.get('raises')

    with raises_if_provided(raises):
        actual = parse._parse_url_for_commit_hash(value)
        assert actual == expected


@pytest.mark.parametrize('p', [
    {  # p0
        'value': '-',
        'expected': tuple([
            [],
            [],
        ]),
    },
    {  # p1
        'value': 'Modules: `bencodepy`, `bencode`<br>Monkey-patched, see `medusa/init/__init__.py`',
        'expected': tuple([
            ['Monkey-patched, see `medusa/init/__init__.py`'],
            ['bencodepy', 'bencode'],
        ]),
    },
    {  # p1
        'value': 'Module: `bs4`<br>Multiple<br>lines<br>notes',
        'expected': tuple([
            ['Multiple', 'lines', 'notes'],
            ['bs4'],
        ]),
    },
    {  # p3
        'value': 'File: `six.py`',
        'expected': tuple([
            [],
            ['six.py'],
        ]),
    },
])
def test_parse_notes(p):
    value = p['value']
    expected = p['expected']
    raises = p.get('raises')

    with raises_if_provided(raises):
        actual = parse._parse_notes(value)
        assert actual == expected


@pytest.mark.parametrize('p', [
    {  # p0
        'value': {
            'line': '',
            'line_no': 9,
        },
        'expected': None,
        'raises': parse.EndOfList,
    },
    {  # p1
        'value': {
            'line': (
                "ext | **`babelfish`** | [f403000](https://github.com/Diaoul/babelfish/tree/f403000dd63092cfaaae80be9f"
                "309fd85c7f20c9) | **`medusa`**, `guessit`, `knowit`, `subliminal` | -"
            ),
            'line_no': 4,
        },
        'expected': tuple([
            models.VendoredLibrary,
            type(None),
        ]),
    },
    {  # p2
        'value': {
            'line': 'ext | **`requests`** | [2.24.0](https://pypi.org/project/requests/2.24.0/) | **`medusa`** | -',
            'line_no': 4,
        },
        'expected': tuple([
            models.VendoredLibrary,
            type(None),
        ]),
    },
    {  # p3
        'value': {
            'line': '|',
            'line_no': 7,
        },
        'expected': tuple([
            type(None),
            parse.LineParseError,
        ]),
    },
    {  # p4
        'value': {
            'line': ' | bb | ccc | d | e',
            'line_no': 8,
        },
        'expected': tuple([
            type(None),
            parse.LineParseError,
        ]),
    },
    {  # p5
        'value': {
            'line': 'a | bb | ccc | d | e',
            'line_no': 8,
        },
        'expected': tuple([
            type(None),
            parse.LineParseError,
        ]),
    },
    {  # p6
        'value': {
            'line': 'a | `bb` | ccc | d | e',
            'line_no': 8,
        },
        'expected': tuple([
            type(None),
            parse.LineParseError,
        ]),
    },
    {  # p7
        'value': {
            'line': 'a | `bb` | [a123def](https://example.com) | d | e',
            'line_no': 8,
        },
        'expected': tuple([
            type(None),
            parse.LineParseError,
        ]),
    },
])
def test_parse_line(p):
    value = p['value']
    expected = p['expected']
    raises = p.get('raises')

    with raises_if_provided(raises):
        # TODO: Actual data comparison
        actual = parse._parse_line(**value)
        for a, b in zip(actual, expected):
            assert type(a) == b
            if type(a) == parse.LineParseError:
                assert str(a)


def test_parse_requirements():
    md_path = Path(__file__).parent.joinpath('fixtures/data.md')
    actual = parse.parse_requirements(md_path)
    for req, error in actual:
        assert error is None
        assert req is not None
