"""Command-line tool to run YAMLine.
Usage:

    $ python -m yamline.tool yamline_file [yamline_alias_file]
"""
import sys
from mixin import get_pipeline


def main():
    if len(sys.argv) == 1:
        raise SyntaxError(sys.argv[0] + " yamline_file [yamline_alias_file]")
    elif len(sys.argv) == 2:
        yamline = get_pipeline(sys.argv[1])
    elif len(sys.argv) == 3:
        yamline = get_pipeline(sys.argv[1], sys.argv[2])
    else:
        raise SystemExit(sys.argv[0] + " yamline_file [yamline_alias_file]")
    yamline.execute()


if __name__ == '__main__':
    main()
