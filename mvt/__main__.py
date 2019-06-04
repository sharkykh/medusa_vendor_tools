# coding: utf-8
import argparse

DEFAULT_EXT_README = 'ext/readme.md'
DEFAULT_REQUIREMENTS_TXT = 'requirements.txt'
DEFAULT_REQUIREMENTS_JSON = DEFAULT_REQUIREMENTS_TXT[:-3] + '.json'

def main(args=None):
    parser = argparse.ArgumentParser('mvt', description='Medusa Vendor Tools [MVT]')

    subparsers = parser.add_subparsers(dest='command', required=True)

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

    args = parser.parse_args(args)

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


if __name__ == '__main__':
    main()
