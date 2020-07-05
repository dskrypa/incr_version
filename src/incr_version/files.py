import logging
import os
import re
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from .exceptions import VersionIncrError
from .git import Git
from .utils import running_under_precommit, get_precommit_cached, updated_version_line

__all__ = ['VersionFile']
log = logging.getLogger(__name__)

_NotSet = object()
VERSION_PAT = re.compile(r'^(\s*__version__\s?=\s?)(["\'])(\d{4}\.\d{2}\.\d{2})((?:-\d+)?)\2$')


class VersionFile:
    def __init__(self, path: Path, encoding: str = 'utf-8'):
        self.path = path  # type: Path
        self.encoding = encoding
        self._version = _NotSet

    def __repr__(self):
        return '<{}[path={}, version={!r}]>'.format(self.__class__.__name__, self.path.as_posix(), self.version)

    def should_update(self, ignore_staged=False):
        if self.is_modified_and_unstaged():
            fmt = (
                'File={} was modified, but has not been staged to be committed - please `git add` or `git checkout` '
                'this file to proceed'
            )
            raise VersionIncrError(fmt.format(self.path))
        elif self.is_staged():
            if ignore_staged:
                log.info('File={} is already staged in git - assuming it has correct version already'.format(self))
                return False

            log.debug('File={} is already staged in git - checking the staged version number'.format(self))
            if self.staged_version_was_modified():
                log.info('A version update was already staged for {} - exiting'.format(self))
                return False

            log.debug('File={} was already staged with changes, but it does not contain a version update'.format(self))
        else:
            log.debug('File={} is not already staged in git'.format(self))

        # TODO: If parent git process has --amend arg, determine whether the version was updated in the original commit
        # ['C:\\Program Files\\Git\\mingw64\\bin\\git.exe', 'commit', '-m', '<message>', '--amend']
        # ['/.../git', 'commit', '-m', '<message>', '--amend']
        return True

    def is_modified_and_unstaged(self):
        if running_under_precommit():
            return self.path.as_posix() in get_precommit_cached()
        return self.path.as_posix() in Git.get_unstaged_modified()

    def is_staged(self):
        return self.path.as_posix() in Git.get_staged()

    def staged_version_was_modified(self):
        for line in Git.staged_changed_lines(self.path.as_posix()):
            if VERSION_PAT.match(line):
                return True
        return False

    @property
    def version(self):
        if self._version is _NotSet:
            with self.path.open('r', encoding=self.encoding) as f:
                for line in f:
                    m = VERSION_PAT.match(line)
                    if m:
                        self._version = m.group(3) + m.group(4)
                        break
                else:
                    self._version = None
        return self._version

    def contains_version(self):
        return bool(self.version)

    def update_version(self, no_pipe_bypass=False, force_suffix=False):
        found = False
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).joinpath('tmp.txt')
            log.debug('Writing updated file to temp file={}'.format(tmp_path))
            with ExitStack() as stack:
                f_in = stack.enter_context(self.path.open('r', encoding=self.encoding))
                f_out = stack.enter_context(tmp_path.open('w', encoding=self.encoding, newline='\n'))
                for line in f_in:
                    if found:
                        f_out.write(line)
                    else:
                        m = VERSION_PAT.match(line)
                        if m:
                            found = True
                            new_line = updated_version_line(m.groups(), no_pipe_bypass, force_suffix)
                            f_out.write(new_line)
                        else:
                            f_out.write(line)
            if found:
                log.debug('Replacing original file={} with modified version'.format(self.path))
                tmp_path.replace(self.path)
            else:
                raise VersionIncrError('No valid version was found in {}'.format(self.path))

    @classmethod
    def find(cls, path, *args, **kwargs):
        if path:
            path = Path(path)
            if path.is_file():
                return cls(path, *args, **kwargs)
            raise VersionIncrError('--file / -f must be the path to a file that exists')

        for root, dirs, files in os.walk(os.getcwd()):
            root = Path(root)
            for file in files:
                path = root.joinpath(file)
                if path.name == '__version__.py':
                    return cls(path, *args, **kwargs)

        setup_path = Path('setup.py')
        if setup_path.is_file():
            return cls(setup_path, *args, **kwargs)
        raise VersionIncrError('Unable to find __version__.py or setup.py - please specify a --file / -f to modify')
