# Medusa Vendor Tools [MVT]

Tools for dealing with the vendored libraries and requirement lists in [**pymedusa/Medusa**](https://github.com/pymedusa/Medusa).

## Notes about the tools
- They are very much a **work in progress**, and could fail at any time.
- They are made to be used on Medusa's `develop` branch and feature branches targeting `develop`.
- Their documentation isn't good.
- They are **far from perfect**, and you should always verify the changes before committing / pushing them.
- They are targeted towards Windows.

## Plans
- Hammer out the details on the vendor script. It's working but it feels very fragile.
- Combine the tools into a package with one entrypoint script with sub-commands.
- Make code more structured and more readable.

## Requirements
- Python 3.6 or later
##### Additionally, for the vendor script:
- [Python Launcher (`py`)](https://docs.python.org/3/using/windows.html#launcher) installed and in PATH
- Latest Python 2.7 installed and executable using `py -2.7`
- `pip` library installed
- [`setuptools`](https://pypi.org/project/setuptools) library installed

## Usage
The scripts require that you run them with your in Medusa's root folder, meaning:
```shell
cd /path/to/Medusa
python /path/to/medusa_vendor_tools/<script>.py [<arguments>]
```
You can use `-h` to see some help on some of the scripts.

## Contents

#### [`check.py`](/check.py)
Check vendor folders using `ext/readme.md`.

#### [`gen_requirements.py`](/gen_requirements.py)
Generate `requirements.txt` (or JSON) from `ext/readme.md`.

#### [`make_md.py`](/make_md.py)
Helper functions to generate vendor readme.md files from JSON spec.

#### [`parse_md.py`](/parse_md.py)
Helper functions to parse vendor readme.md files.

#### [`sort_md.py`](/sort_md.py)
Sort `ext/readme.md` and `lib/readme.md` by package name.

#### [`vendor.py`](/vendor.py)
Vendor (or update existing) libraries.

## A list of the targeted files and folders
- [`ext`](https://github.com/pymedusa/Medusa/tree/develop/ext) - Vendored libraries that are Python2/Python3 compatible.
- [`ext2`](https://github.com/pymedusa/Medusa/tree/develop/ext2) - Vendored libraries that are only for Python2.
- [`ext3`](https://github.com/pymedusa/Medusa/tree/develop/ext3) - Vendored libraries that are only for Python3.
- [`ext/readme.md`](https://github.com/pymedusa/Medusa/blob/develop/ext/readme.md) - A listing of the vendored libraries present in the folders above.
- [`lib`](https://github.com/pymedusa/Medusa/blob/develop/lib) - Vendored libraries whose codes are customized to fit Medusa's needs, and other miscellaneous stuff.
- [`lib/readme.md`](https://github.com/pymedusa/Medusa/blob/develop/lib/readme.md) - A listing of everything present in the folder above.
- [`requirements.txt`](https://github.com/pymedusa/Medusa/blob/develop/requirements.txt) - A listing of Medusa's direct dependencies (imported by the `medusa` package). [Renovate](https://github.com/apps/renovate) uses this to provide version updates.
