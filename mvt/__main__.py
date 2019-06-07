# coding: utf-8
DEFAULT_EXT_README = 'ext/readme.md'
DEFAULT_LIB_README = 'lib/readme.md'
DEFAULT_REQUIREMENTS_TXT = 'requirements.txt'
DEFAULT_REQUIREMENTS_JSON = DEFAULT_REQUIREMENTS_TXT[:-3] + 'json'

def main(args=None):
    import argparse
    parser = argparse.ArgumentParser('mvt', description='Medusa Vendor Tools [MVT]')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Command: vendor
    vendor_parser = subparsers.add_parser('vendor', help='Vendor (or update existing) libraries.')
    vendor_parser.add_argument('package', help='Package to vendor')
    vendor_parser.add_argument('-2', '--py2', action='store_true', help='Install Python 2 version to ext2')
    vendor_parser.add_argument('-3', '--py3', action='store_true', help='Install Python 3 version to ext3')
    vendor_parser.add_argument(
        '-f', '--listfile', default=DEFAULT_EXT_README,
        help=f'List file to update (affects target folders). Defaults to `{DEFAULT_EXT_README}`'
    )

    # Command: gen
    gen_parser = subparsers.add_parser('gen', help='Generate `requirements.txt` (or JSON) from `ext/readme.md`.')
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

    # Command: parse
    parse_parser = subparsers.add_parser('parse', help='Test parsing `ext/readme.md` or `lib/readme.md`.')
    parse_parser.add_argument('file', help='The list file to test.')

    # Command: check
    check_parser = subparsers.add_parser('check', help='Check vendor folders using `ext/readme.md` or `lib/readme.md`.')
    check_parser.add_argument('file', help='The list file to test.')

    # Command: sort
    sort_parser = subparsers.add_parser('sort', help='Sort `ext/readme.md` and `lib/readme.md` by package name.')

    # Command: make
    make_parser = subparsers.add_parser('make', help='Generate `ext/readme.md` from JSON')
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
        from .vendor import main as vendor
        vendor(
            listfile=args.listfile,
            package=args.package,
            py2=args.py2,
            py3=args.py3,
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
