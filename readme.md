# Medusa Vendor Tools [MVT]

Tools for dealing with the vendored libraries and requirement lists in [**pymedusa/Medusa**](https://github.com/pymedusa/Medusa).

## Notes about the tools
- They are very much a **work in progress**, and could fail at any time.
- They are made to be used on Medusa's `develop` branch and feature branches targeting `develop`.
- Their documentation isn't good.
- They are **far from perfect**, and you should always verify the changes before committing / pushing them.
- They are targeted towards Windows.

## Requirements
- Python 3.6 or later
##### Additionally, for the vendor command:
- [Python Launcher (`py`)](https://docs.python.org/3/using/windows.html#launcher) installed and in PATH
- Latest Python 2.7 installed and executable using `py -2.7`
- `pip` library installed
- [`setuptools`](https://pypi.org/project/setuptools) library installed

## Installation
```
pip install https://github.com/sharkykh/medusa_vendor_tools/archive/master.tar.gz
```
or by cloning this repository:
```
git clone https://github.com/sharkykh/medusa_vendor_tools
cd medusa_vendor_tools
pip install .
```

## Usage
The script requires that you run it within your Medusa's root folder, meaning:
```shell
cd /path/to/Medusa
mvt -h
mvt <command> [-h | <arguments>]
```

## Commands

#### [`mvt vendor`](/mvt/vendor.py)
Vendor (or update existing) libraries.

#### [`mvt gen`](/mvt/gen_req.py)
Generate `requirements.txt` (or JSON) from `ext/readme.md`.

#### [`mvt parse`](/mvt/parse.py)
Test parsing `ext/readme.md` or `lib/readme.md`.

#### [`mvt check`](/mvt/check.py)
Check vendor folders using `ext/readme.md` or `lib/readme.md`.

#### [`mvt sort`](/mvt/sort.py)
Sort `ext/readme.md` and `lib/readme.md` by package name.

#### [`mvt make`](/mvt/make_md.py)
Generate `ext/readme.md` from `requirements.json`.

## A list of the targeted files and folders
- [`ext`](https://github.com/pymedusa/Medusa/tree/develop/ext) - Vendored libraries that are Python2/Python3 compatible.
- [`ext2`](https://github.com/pymedusa/Medusa/tree/develop/ext2) - Vendored libraries that are only for Python2.
- [`ext3`](https://github.com/pymedusa/Medusa/tree/develop/ext3) - Vendored libraries that are only for Python3.
- [`ext/readme.md`](https://github.com/pymedusa/Medusa/blob/develop/ext/readme.md) - A listing of the vendored libraries present in the folders above.
- [`lib`](https://github.com/pymedusa/Medusa/blob/develop/lib) - Vendored libraries whose codes are customized to fit Medusa's needs, and other miscellaneous stuff.
- [`lib/readme.md`](https://github.com/pymedusa/Medusa/blob/develop/lib/readme.md) - A listing of everything present in the folder above.
- [`requirements.txt`](https://github.com/pymedusa/Medusa/blob/develop/requirements.txt) - A listing of Medusa's direct dependencies (imported by the `medusa` package). [Renovate](https://github.com/apps/renovate) uses this to provide version updates.
