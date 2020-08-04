import json
from pathlib import Path

import pytest

from mvt import models

from tests import raises_if_provided


with Path(__file__).parent.joinpath('fixtures/data.json').open('r', encoding='utf-8') as fh:
    json_data = json.load(fh)
    json_data_dict = {
        item['name'].lower(): item
        for item in json_data
    }


@pytest.mark.parametrize('p', [
    {  # p0
        'value': 'MyKey',
        'expected': 'mykey',
    },
    {  # p1
        'value': models.VendoredLibrary.from_json(json_data_dict['cachecontrol']),
        'expected': 'cachecontrol',
    },
    {  # p2
        'value': models.UsedByModule.from_json('Mako'),
        'expected': 'mako',
    },
    {  # p3
        'value': 3,
        'expected': None,
        'raises': ValueError,
    },
])
def test_to_key(p):
    value = p['value']
    expected = p['expected']
    raises = p.get('raises')

    with raises_if_provided(raises):
        assert models.to_key(value) == expected


@pytest.mark.parametrize('p', [
    {  # p0
        'value': '**`medusa`** (via `beautifulsoup4`), `tornado`, `requests`, `adba`',
        'expected': [
            ('medusa', '(via `beautifulsoup4`)'),
            ('adba', ''),
            ('requests', ''),
            ('tornado', ''),
        ],
        'expected_str': '**`medusa`** (via `beautifulsoup4`), `adba`, `requests`, `tornado`',
        'expected_repr': "UsedBy('medusa (via `beautifulsoup4`)', 'adba', 'requests', 'tornado')",
    },
    {  # p1
        'value': f'`{models.UsedBy._UNUSED}`',
        'expected': [],
        'expected_str': f'`{models.UsedBy._UNUSED}`',
        'expected_repr': "UsedBy()",
    },
    {  # p2
        'value': f'`{models.UsedBy.UPDATE_ME}`',
        'expected': [
            (models.UsedBy.UPDATE_ME, ''),
        ],
        'expected_str': f'`{models.UsedBy.UPDATE_ME}`',
        'expected_repr': f"UsedBy('{models.UsedBy.UPDATE_ME}')",
    },
    {  # p3
        'value': ['subliminal', 'requests', 'future'],
        'expected': [
            ('future', ''),
            ('requests', ''),
            ('subliminal', ''),
        ],
        'expected_str': '`future`, `requests`, `subliminal`',
        'expected_repr': "UsedBy('future', 'requests', 'subliminal')",
    },
])
def test_used_by(p):
    value = p['value']
    expected = p['expected']
    expected_str = p['expected_str']
    expected_repr = p['expected_repr']
    # raises = p.get('raises')

    actual = models.UsedBy(value)

    # Verify size
    assert len(actual) == len(expected)

    # Verify repr
    assert repr(actual) == expected_repr

    # Verify string representation
    assert str(actual) == expected_str

    # Verify JSON representation
    expected_json = [
        [name, extra] if extra else name
        for name, extra in expected
    ]
    assert actual.json() == expected_json

    # Verify data & order
    for index, (name, extra) in enumerate(expected):
        assert actual[name].name == name
        assert actual[name].extra == extra
        assert actual.ordered.index(name.lower()) == index

    # Test empty
    empty_usage = models.UsedBy()
    assert repr(empty_usage) == 'UsedBy()'

    # Add
    temp_usage = models.UsedBy()
    with pytest.raises(ValueError):
        temp_usage.add(123)
    temp_usage.add('PyGithub')
    assert 'PyGithub' in temp_usage
    assert temp_usage['PyGithub'].name == 'PyGithub'
    assert temp_usage['PyGithub'].extra == ''
    with pytest.raises(KeyError):
        temp_usage.add('PyGithub')

    # Remove
    with pytest.raises(ValueError):
        temp_usage.remove(1)
    temp_usage.remove('PyGithub')
    assert 'PyGithub' not in temp_usage
    with pytest.raises(KeyError):
        assert temp_usage.remove('PyGithub') == 'PyGithub'
    assert temp_usage.remove('PyGithub', ignore_errors=True) is None


@pytest.mark.parametrize('p', [
    {  # p0
        'value': json_data_dict['adba'],
        'expected': {
            'folder': ['ext'],
            'name': 'adba',
            'extras': [],
            'version': '6efeff3a6bdcb6d45a4a79f424939ade2930e5f0',
            'modules': ['adba'],
            'git': True,
            'branch': None,
            'url': 'https://github.com/pymedusa/adba/tree/6efeff3a6bdcb6d45a4a79f424939ade2930e5f0',
            'usage': ['medusa'],
            'notes': [],
            'package': 'adba',
            'markers': '',
            'updatable': True,
            'as_requirement': (
                'adba @ https://codeload.github.com/pymedusa/adba/tar.gz/6efeff3a6bdcb6d45a4a79f424939ade2930e5f0'
            ),
            'as_update_requirement': 'adba @ https://github.com/pymedusa/adba/archive/HEAD.tar.gz',
            'main_module': 'adba',
            'main_module_matches_package_name': True,
            'is_main_module_file': False,
        },
    },
    {  # p1
        'value': json_data_dict['appdirs'],
        'expected': {
            'folder': ['ext'],
            'name': 'appdirs',
            'extras': [],
            'version': '1.4.3',
            'modules': ['appdirs.py'],
            'git': False,
            'branch': None,
            'url': 'https://pypi.org/project/appdirs/1.4.3/',
            'usage': ['simpleanidb', ['subliminal', '(cli only)']],
            'notes': [],
            'package': 'appdirs',
            'markers': '',
            'updatable': True,
            'as_requirement': 'appdirs==1.4.3',
            'as_update_requirement': 'appdirs',
            'main_module': 'appdirs.py',
            'main_module_matches_package_name': False,
            'is_main_module_file': True,
        },
    },
    {  # p2
        'value': json_data_dict['backports_abc'],
        'expected': {
            'folder': ['ext2'],
            'name': 'backports_abc',
            'extras': [],
            'version': '0.5',
            'modules': ['backports_abc.py'],
            'git': False,
            'branch': None,
            'url': 'https://pypi.org/project/backports_abc/0.5/',
            'usage': ['tornado'],
            'notes': [],
            'package': 'backports_abc',
            'markers': " ; python_version == '2.*'",
            'updatable': True,
            'as_requirement': "backports_abc==0.5 ; python_version == '2.*'",
            'as_update_requirement': 'backports_abc',
            'main_module': 'backports_abc.py',
            'main_module_matches_package_name': False,
            'is_main_module_file': True,
        },
    },
    {  # p3
        'value': json_data_dict['beautifulsoup4'],
        'expected': {
            'folder': ['ext2', 'ext3'],
            'name': 'beautifulsoup4',
            'extras': ['html5lib'],
            'version': '4.9.1',
            'modules': ['bs4'],
            'git': False,
            'branch': None,
            'url': 'https://pypi.org/project/beautifulsoup4/4.9.1/',
            'usage': ['medusa', 'subliminal'],
            'notes': [],
            'package': 'beautifulsoup4[html5lib]',
            'markers': '',
            'updatable': True,
            'as_requirement': 'beautifulsoup4[html5lib]==4.9.1',
            'as_update_requirement': 'beautifulsoup4[html5lib]',
            'main_module': 'bs4',
            'main_module_matches_package_name': False,
            'is_main_module_file': False,
        },
    },
    {  # p4
        'value': json_data_dict['zzz-not-a-package'],
        'expected': {
            'folder': ['ext'],
            'name': 'zzz-not-a-package',
            'extras': [],
            'version': None,
            'modules': ['my_module'],
            'git': False,
            'branch': None,
            'url': None,
            'usage': [],
            'notes': [],
            'package': 'zzz-not-a-package',
            'markers': '',
            'updatable': False,
            'as_requirement': None,
            'as_update_requirement': None,
            'main_module': 'my_module',
            'main_module_matches_package_name': False,
            'is_main_module_file': False,
        },
    },
    {  # p5
        'value': json_data_dict['zzz-single-file-from-github'],
        'expected': {
            'folder': ['ext'],
            'name': 'zzz-single-file-from-github',
            'extras': [],
            'version': 'abcdef0123456789abcdef0123456789abcdef01',
            'modules': ['my_file.py'],
            'git': True,
            'branch': None,
            'url': 'https://github.com/owner/repo/blob/abcdef0123456789abcdef0123456789abcdef01/path/to/my_file.py',
            'usage': ['<UPDATE-ME>'],
            'notes': [],
            'package': 'zzz-single-file-from-github',
            'markers': '',
            'updatable': False,
            'as_requirement': None,
            'as_update_requirement': None,
            'main_module': 'my_file.py',
            'main_module_matches_package_name': False,
            'is_main_module_file': True,
        },
    },
])
def test_vendored_library(p):
    value = p['value']
    expected = p['expected']
    # raises = p.get('raises')

    lib = models.VendoredLibrary.from_json(value)
    assert lib.folder == expected['folder']
    assert lib.name == expected['name']
    assert lib.extras == expected['extras']
    assert lib.version == expected['version']
    assert lib.modules == expected['modules']
    assert lib.git == expected['git']
    assert lib.branch == expected['branch']
    assert lib.url == expected['url']
    for u in expected['usage']:
        if isinstance(u, list):
            name, extra = u
        elif isinstance(u, str):
            name, extra = u, ''
        assert lib.usage[name].name == name
        assert lib.usage[name].extra == extra
    assert lib.notes == expected['notes']

    assert lib.package == expected['package']
    assert lib.markers == expected['markers']
    assert lib.updatable == expected['updatable']
    assert lib.as_requirement() == expected['as_requirement']
    assert lib.as_update_requirement() == expected['as_update_requirement']
    assert lib.main_module == expected['main_module']
    assert lib.main_module_matches_package_name == expected['main_module_matches_package_name']
    assert lib.is_main_module_file == expected['is_main_module_file']

    assert str(lib) == expected['name']
    assert repr(lib) == f"VendoredLibrary({repr(expected['name'])})"


def test_vendored_list():
    requirements = models.VendoredList.from_json(json_data)

    # Verify size
    assert len(requirements) == len(json_data)

    # Verify order
    sorted_json_data = sorted(json_data, key=lambda x: x['name'].lower())
    for lib, expected in zip(requirements.ordered, sorted_json_data):
        assert lib.name == expected['name']

    # Verify repr
    repr_data = ', '.join(repr(item['name']) for item in sorted_json_data)
    assert repr(requirements) == f"VendoredList[{len(json_data)}]({repr_data})"

    # Verify JSON representation
    assert requirements.json() == json_data
    requirements.folder == json_data[0]['folder'][0].strip('23')

    # Test empty list
    empty_list = models.VendoredList()
    assert empty_list.folder is None
    assert repr(empty_list) == 'VendoredList[0]()'

    # Add
    temp_list = models.VendoredList()
    with pytest.raises(ValueError):
        temp_list.add('should fail')
    temp_list.add(requirements[0])
    assert requirements[0].name in temp_list
    with pytest.raises(KeyError):
        temp_list.add(requirements[0])

    # Remove
    with pytest.raises(ValueError):
        temp_list.remove(1)
    temp_list.remove(requirements[0])
    assert requirements[0].name not in temp_list
    with pytest.raises(KeyError):
        assert temp_list.remove(requirements[0]) == requirements[0].name
    assert temp_list.remove(requirements[0], ignore_errors=True) is None
