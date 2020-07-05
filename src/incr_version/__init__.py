import logging
import sys
from argparse import ArgumentParser

from .exceptions import VersionIncrError
from .files import VersionFile
from .git import Git

__all__ = ['VersionIncrError', 'main']
log = logging.getLogger(__name__)


def _main():
    # fmt: off
    parser = ArgumentParser(description='Python project version incrementer (to be run as a pre-commit hook)')
    parser.add_argument('--file', '-f', metavar='PATH', help='The file that contains the version to be incremented')
    parser.add_argument('--encoding', '-e', default='utf-8', help='The encoding used by the version file')
    parser.add_argument('--ignore_staged', '-i', action='store_true', help='Assume already staged version file contains updated version')
    parser.add_argument('--debug', '-d', action='store_true', help='Show debug logging')
    parser.add_argument('--no_pipe_bypass', '-B', action='store_true', help='Do not bypass pre-commit\'s stdout pipe when printing the updated version number')
    args = parser.parse_args()
    # fmt: on
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format='%(message)s')

    file = VersionFile.find(args.file, args.encoding)
    log.debug('Found file={}'.format(file))

    if file.should_update(args.ignore_staged):
        file.update_version(args.no_pipe_bypass)
        log.debug('Adding updated version file to the commit...')
        Git.add(file.path.as_posix())


def main():
    try:
        _main()
    except KeyboardInterrupt:
        print()
    except VersionIncrError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
