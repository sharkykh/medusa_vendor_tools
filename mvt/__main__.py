# coding: utf-8
import argparse

DEFAULT_INFILE = 'ext/readme.md'
DEFAULT_OUTFILE = 'requirements.txt'

def main(args=None):
    parser = argparse.ArgumentParser('mvt', description='Medusa Vendor Tools [MVT]')

    subparsers = parser.add_subparsers(dest='command', required=True)

    gen_parser = subparsers.add_parser('gen', help='Generate `requirements.txt` (or JSON) from `ext/readme.md`.')
    gen_parser.add_argument(
        '-i', '--infile', default=DEFAULT_INFILE, required=False,
        help='Input file. Defaults to `ext/readme.md`'
    )
    gen_parser.add_argument(
        '-o', '--outfile', default=DEFAULT_OUTFILE, required=False,
        help='Output file. Defaults to `requirements.txt` (with `--json`: `requirements.json`)'
    )
    gen_parser.add_argument(
        '-a', '--all-packages', action='store_true', default=False,
        help='List all packages, not just those used by Medusa'
    )
    gen_parser.add_argument(
        '-j', '--json', action='store_true', default=False,
        help='export as JSON to `requirements.json` (or OUTFILE)'
    )

    args = parser.parse_args(args)

if __name__ == '__main__':
    main()
