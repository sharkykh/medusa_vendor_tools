# coding: utf-8
from . import __version__

DEFAULT_EXT_README = 'ext/readme.md'
DEFAULT_LIB_README = 'lib/readme.md'
DEFAULT_REQUIREMENTS_TXT = 'requirements.txt'
DEFAULT_REQUIREMENTS_JSON = DEFAULT_REQUIREMENTS_TXT[:-4] + '.json'


def main(args=None):
    import argparse
    parser = argparse.ArgumentParser('mvt', description=f'Medusa Vendor Tools [MVT] v{__version__}')

    subparsers = parser.add_subparsers(metavar='command', help='The task to perform', dest='command', required=True)

    # Command: vendor
    vendor_help = 'Vendor (or update existing) libraries.'
    vendor_parser = subparsers.add_parser('vendor', help=vendor_help, description=vendor_help)
    vendor_parser.add_argument('package', help='Package to vendor')
    vendor_parser.add_argument('-2', '--py2', action='store_true', help='Force install Python 2 version to [target]2')
    vendor_parser.add_argument('-3', '--py3', action='store_true', help='Force install Python 3 version to [target]3')
    vendor_parser.add_argument('-6', '--py6', action='store_true', help='Force install Python 3 version to [target]')
    vendor_parser.add_argument(
        '-f', '--listfile', default=DEFAULT_EXT_README,
        help=f'List file to update (affects target folders). Defaults to `{DEFAULT_EXT_README}`'
    )

    # Command: update
    update_help = 'Update already-vendored library by name.'
    update_parser = subparsers.add_parser('update', help=update_help, description=update_help)
    update_parser.add_argument('package', help='Package name to update')
    update_parser.add_argument(
        '-c', '--cmd', action='store_true', default=False,
        help=f'Generate a `vendor` command for the provided package (does not update)'
    )
    update_parser.add_argument(
        '-f', '--listfile', default=DEFAULT_EXT_README,
        help=f'List file to update (affects target folders). Defaults to `{DEFAULT_EXT_README}`'
    )

    # Command: gen
    gen_help = 'Generate `requirements.txt` (or JSON) from `ext/readme.md`.'
    gen_parser = subparsers.add_parser('gen', help=gen_help, description=gen_help)
    gen_parser.add_argument(
        '-i', '--infile', default=DEFAULT_EXT_README, required=False,
        help=f'Input file. Defaults to `{DEFAULT_EXT_README}`'
    )
    gen_parser.add_argument(
        '-o', '--outfile', default=DEFAULT_REQUIREMENTS_TXT, required=False,
        help=f'Output file. Defaults to `{DEFAULT_REQUIREMENTS_TXT}` (with `--json`: `{DEFAULT_REQUIREMENTS_JSON}`)'
    )
    gen_parser.add_argument(
        '-a', '--all-packages', action='store_true', default=False,
        help='List all packages, not just those used by Medusa'
    )
    gen_parser.add_argument(
        '-j', '--json', action='store_true', default=False,
        help=f'export as JSON to `{DEFAULT_REQUIREMENTS_JSON}` (or OUTFILE)'
    )

    # Command: outdated
    outdated_help = 'List outdated packages.'
    outdated_parser = subparsers.add_parser('outdated', help=outdated_help, description=outdated_help)
    outdated_parser.add_argument(
        'packages', nargs='*', metavar='package',
        help=f'Package(s) to check. If not provided, checks all of the packages.'
    )
    outdated_parser.add_argument(
        '-f', '--listfile', default=DEFAULT_EXT_README,
        help=f'List file to check. Defaults to `{DEFAULT_EXT_README}`'
    )

    # Command: remove
    remove_help = 'Remove vendored library by name.'
    remove_parser = subparsers.add_parser('remove', help=remove_help, description=remove_help)
    remove_parser.add_argument('package', help='Package name to remove')
    remove_parser.add_argument(
        '-f', '--listfile', default=DEFAULT_EXT_README,
        help=f'List file to update (affects target folders). Defaults to `{DEFAULT_EXT_README}`'
    )

    # Command: parse
    parse_help = 'Test parsing `ext/readme.md` or `lib/readme.md`.'
    parse_parser = subparsers.add_parser('parse', help=parse_help, description=parse_help)
    parse_parser.add_argument('file', help='The list file to test.')

    # Command: check
    check_help = 'Check vendor folders using `ext/readme.md` or `lib/readme.md`.'
    check_parser = subparsers.add_parser('check', help=check_help, description=check_help)
    check_parser.add_argument('file', help='The list file to test.')

    # Command: sort
    sort_help = 'Sort `ext/readme.md` and `lib/readme.md` by package name.'
    sort_parser = subparsers.add_parser('sort', help=sort_help, description=sort_help)

    # Command: make
    make_help = 'Generate `ext/readme.md` from `requirements.json`.'
    make_parser = subparsers.add_parser('make', help=make_help, description=make_help)
    make_parser.add_argument(
        '-i', '--infile', default=DEFAULT_REQUIREMENTS_JSON, required=False,
        help=f'JSON input file. Defaults to `{DEFAULT_REQUIREMENTS_JSON}`'
    )
    make_parser.add_argument(
        '-o', '--outfile', default=DEFAULT_EXT_README, required=False,
        help=f'Markdown output file. Defaults to `{DEFAULT_EXT_README}`'
    )

    args = parser.parse_args(args)

    if args.command == 'vendor':
        if args.py6 and (args.py2 or args.py3):
            print('ERROR: --py6 and --py2/--py3 cannot be combined.')
            return

        from .vendor import vendor
        vendor(
            listfile=args.listfile,
            package=args.package,
            py2=args.py2,
            py3=args.py3,
            py6=args.py6,
        )

    if args.command == 'update':
        from .update import update
        update(
            listfile=args.listfile,
            package=args.package,
            cmd=args.cmd,
        )

    if args.command == 'gen':
        if args.json and args.outfile == DEFAULT_REQUIREMENTS_TXT:
            args.outfile = DEFAULT_REQUIREMENTS_JSON

        from .gen_req import generate_requirements
        generate_requirements(
            infile=args.infile,
            outfile=args.outfile,
            all_packages=args.all_packages,
            json_output=args.json,
        )

    if args.command == 'outdated':
        from .outdated import outdated
        outdated(
            listfile=args.listfile,
            packages=args.packages,
        )

    if args.command == 'remove':
        from .remove import remove
        remove(
            listfile=args.listfile,
            package=args.package,
        )

    if args.command == 'parse':
        from .parse import test
        test(args.file)

    if args.command == 'check':
        from .check import check
        check(args.file)

    if args.command == 'sort':
        from .sort import sort_md
        sort_md(DEFAULT_EXT_README)
        sort_md(DEFAULT_LIB_README)

    if args.command == 'make':
        from .make_md import main as gen_md
        gen_md(
            infile=args.infile,
            outfile=args.outfile,
        )


if __name__ == '__main__':
    main()
