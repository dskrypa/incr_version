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
    parser.add_argument('--encoding', '-e', default='utf-8', help='The encoding used by the version file (default: %(default)s)')

    opt_group = parser.add_argument_group('Behavior Options', 'Configure file/version handling behavior')
    opt_group.add_argument('--suffix', '-s', action='store_true', help='Force use of a numeric suffix, even on the first version for a given day')
    opt_group.add_argument('--no_add', '-A', action='store_true', help='Do not add the version file to git after making changes to it')
    opt_group.add_argument('--update_amended', '-u', action='store_true', help='Update the version even when running under `git commit --amend`')
    opt_group.add_argument('--ignore_staged', '-S', action='store_true', help='Assume already staged version file contains updated version')
    opt_group.add_argument('--ignore_cache_age', '-C', action='store_true', help='Ignore the age of the pre-commit unstaged file cache and assume the latest cache is for the current commit')

    out_group = parser.add_argument_group('Output Options', 'Configure logging behavior')
    out_group.add_argument('--no_pipe_bypass', '-B', action='store_true', help='Do not bypass pre-commit\'s stdout pipe when printing the updated version number')
    out_group.add_argument('--debug', '-d', action='store_true', help='Show debug logging')
    args = parser.parse_args()
    # fmt: on
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format='%(message)s')

    file = VersionFile.find(args.file, args.encoding)
    log.debug('Found file={}'.format(file))

    if file.should_update(args.ignore_staged, args.update_amended, args.ignore_cache_age):
        file.update_version(args.no_pipe_bypass, args.suffix)
        if args.no_add:
            log.debug('Skipping `git add {}`'.format(file.path.as_posix()))
        else:
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
