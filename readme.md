# Medusa Vendor Tools [MVT]

Tools for dealing with the vendored libraries and requirement lists in [**pymedusa/Medusa**](https://github.com/pymedusa/Medusa).

## Notes about the tools
- They are very much a **work in progress**, and could fail at any time.
- They are made to be used on Medusa's `develop` branch and feature branches targeting `develop`.
- Their documentation isn't good.
- They are **far from perfect**, and you should always verify the changes before committing / pushing them.
- They are targeted towards Windows.

## Requirements
- Python 3.7 or later
##### Additionally, for the `vendor` command:
- [Python Launcher (`py`)](https://docs.python.org/3/using/windows.html#launcher) installed and in PATH
- Latest Python 2.7 installed and executable using `py -2.7`
- `pip` tool installed
- [`setuptools`](https://pypi.org/project/setuptools) library installed
##### Additionally, for the `outdated` command:
- [`requests`](https://pypi.org/project/requests) library installed

## Installation
**Recommended:** Clone this repository and install in "editable" mode:
```shell
git clone https://github.com/sharkykh/medusa_vendor_tools
cd medusa_vendor_tools
pip install -e .
```
Then update using `git pull` in the repository directory.

**Or:** Install from archive:
```shell
pip install https://github.com/sharkykh/medusa_vendor_tools/archive/master.tar.gz
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
```
usage: mvt vendor [-h] [-2] [-3] [-f LISTFILE] package

positional arguments:
  package               Package to vendor

optional arguments:
  -h, --help            show this help message and exit
  -2, --py2             Install Python 2 version to [target]2
  -3, --py3             Install Python 3 version to [target]3
  -f LISTFILE, --listfile LISTFILE
                        List file to update (affects target folders). Defaults
                        to `ext/readme.md`
```

#### [`mvt gen`](/mvt/gen_req.py)
Generate `requirements.txt` (or JSON) from `ext/readme.md`.
```
usage: mvt gen [-h] [-i INFILE] [-o OUTFILE] [-a] [-j]

optional arguments:
  -h, --help            show this help message and exit
  -i INFILE, --infile INFILE
                        Input file. Defaults to `ext/readme.md`
  -o OUTFILE, --outfile OUTFILE
                        Output file. Defaults to `requirements.txt` (with
                        `--json`: `requirements.json`)
  -a, --all-packages    List all packages, not just those used by Medusa
  -j, --json            export as JSON to `requirements.json` (or OUTFILE)
```

#### [`mvt outdated`](/mvt/outdated.py)
List outdated packages.
```
usage: mvt outdated [-h] [-f LISTFILE] [package [package ...]]

positional arguments:
  package              Package(s) to check. If not provided, checks all of
                        the packages.

optional arguments:
  -h, --help            show this help message and exit
  -f LISTFILE, --listfile LISTFILE
                        List file to check. Defaults to `ext/readme.md`
```

#### [`mvt parse`](/mvt/parse.py)
Test parsing `ext/readme.md` or `lib/readme.md`.
```
usage: mvt parse [-h] file

positional arguments:
  file        The list file to test.

optional arguments:
  -h, --help  show this help message and exit
```

#### [`mvt check`](/mvt/check.py)
Check vendor folders using `ext/readme.md` or `lib/readme.md`.
```
usage: mvt check [-h] file

positional arguments:
  file        The list file to test.

optional arguments:
  -h, --help  show this help message and exit
```

#### [`mvt sort`](/mvt/sort.py)
Sort `ext/readme.md` and `lib/readme.md` by package name.
```
usage: mvt sort [-h]

optional arguments:
  -h, --help  show this help message and exit
```

#### [`mvt make`](/mvt/make_md.py)
Generate `ext/readme.md` from `requirements.json`.
```
usage: mvt make [-h] [-i INFILE] [-o OUTFILE]

optional arguments:
  -h, --help            show this help message and exit
  -i INFILE, --infile INFILE
                        JSON input file. Defaults to `requirements.json`
  -o OUTFILE, --outfile OUTFILE
                        Markdown output file. Defaults to `ext/readme.md`
```

## Targeted files and folders
- [`ext`](https://github.com/pymedusa/Medusa/tree/develop/ext) - Vendored libraries that are Python2/Python3 compatible.
- [`ext2`](https://github.com/pymedusa/Medusa/tree/develop/ext2) - Vendored libraries that are only for Python2.
- [`ext3`](https://github.com/pymedusa/Medusa/tree/develop/ext3) - Vendored libraries that are only for Python3.
- [`ext/readme.md`](https://github.com/pymedusa/Medusa/blob/develop/ext/readme.md) - A listing of the vendored libraries present in the folders above.
- [`lib`](https://github.com/pymedusa/Medusa/blob/develop/lib) - Vendored libraries whose codes are customized to fit Medusa's needs, and other miscellaneous stuff.
- [`lib/readme.md`](https://github.com/pymedusa/Medusa/blob/develop/lib/readme.md) - A listing of everything present in the folder above.
- [`requirements.txt`](https://github.com/pymedusa/Medusa/blob/develop/requirements.txt) - A listing of Medusa's direct dependencies (imported by the `medusa` package). [Renovate](https://github.com/apps/renovate) uses this to provide version updates.
