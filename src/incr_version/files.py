"""
This module provides the VersionFile class that represents a ``__version__.py`` file, and utilities for finding that
file.
"""

from __future__ import annotations

import logging
import os
import re
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from .exceptions import VersionIncrError
from .git import Git
from .utils import get_precommit_cached, running_under_precommit, updated_version_line

__all__ = ['VersionFile']
log = logging.getLogger(__name__)

_NotSet = object()
VERSION_PAT = re.compile(r'^(\s*__version__\s?=\s?)(["\'])(\d{4}\.\d{2}\.\d{2}(?:-\d+)?)\2$')


class VersionFile:
    def __init__(self, path: Path, encoding: str = 'utf-8', dry_run: bool = False):
        self.path: Path = path
        self.encoding = encoding
        self._version = _NotSet
        self.dry_run = dry_run

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[path={self.path.as_posix()}, version={self.version!r}]>'

    def should_update(self, ignore_staged=False, update_amended=False, ignore_cache_age=False) -> bool:
        if self.is_modified_and_unstaged(ignore_cache_age):
            raise VersionIncrError(
                f'File={self.path} was modified, but has not been staged to be committed - please `git add` or'
                ' `git checkout` this file to proceed'
            )
        elif self.is_staged():
            if ignore_staged:
                log.info(f'File={self} is already staged in git - assuming it has correct version already')
                return False

            log.debug(f'File={self} is already staged in git - checking the staged version number')
            if self.staged_version_was_modified():
                log.info(f'A version update was already staged for {self} - exiting')
                return False

            log.debug(f'File={self} was already staged with changes, but it does not contain a version update')
        elif Git.current_commit_is_amending():
            if not update_amended:
                log.info('The current commit is using --amend - exiting')
                return False
            log.info('The current commit is using --amend - updating')
        else:
            log.debug(f'File={self} is not already staged in git')

        return True

    def is_modified_and_unstaged(self, ignore_cache_age: bool = False) -> bool:
        if running_under_precommit():
            return self.path.as_posix() in get_precommit_cached(ignore_cache_age)
        return self.path.as_posix() in Git.get_unstaged_modified()

    def is_staged(self) -> bool:
        return self.path.as_posix() in Git.get_staged()

    def staged_version_was_modified(self) -> bool:
        return any(VERSION_PAT.match(line) for line in Git.staged_changed_lines(self.path.as_posix()))

    @property
    def version(self) -> str | None:
        if self._version is _NotSet:
            with self.path.open('r', encoding=self.encoding) as f:
                for line in f:
                    if m := VERSION_PAT.match(line):
                        self._version = m.group(3)
                        break
                else:
                    self._version = None
        return self._version

    def contains_version(self) -> bool:
        return bool(self.version)

    def update_version(self, no_pipe_bypass: bool = False, force_suffix: bool = False):
        found = False
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir).joinpath('tmp.txt')
            log.debug(f'Writing updated file to temp file={tmp_path}')
            with ExitStack() as stack:
                f_in = stack.enter_context(self.path.open('r', encoding=self.encoding))
                f_out = stack.enter_context(tmp_path.open('w', encoding=self.encoding, newline='\n'))
                for line in f_in:
                    if found:
                        f_out.write(line)
                    elif m := VERSION_PAT.match(line):
                        found = True
                        new_line = updated_version_line(m.groups(), no_pipe_bypass, force_suffix, self.dry_run)
                        f_out.write(new_line)
                    else:
                        f_out.write(line)

            if found:
                if self.dry_run:
                    log.debug(f'[DRY RUN] Would replace original file={self.path} with modified version')
                else:
                    log.debug(f'Replacing original file={self.path} with modified version')
                    tmp_path.replace(self.path)
            else:
                raise VersionIncrError(f'No valid version was found in {self.path}')

    @classmethod
    def find(cls, path: Path | str | None, *args, **kwargs) -> VersionFile:
        if path:
            path = Path(path)
            if path.is_file():
                return cls(path, *args, **kwargs)
            raise VersionIncrError('--file / -f must be the path to a file that exists')

        # TODO: Make exclusions configurable, or interpret .gitignore?
        ignore = re.compile(r'[/\\](\.?venv|site-packages|build)(?:[/\\]|$)', re.IGNORECASE).search
        for root, dirs, files in os.walk(os.getcwd()):
            if not ignore(root) and '__version__.py' in files:
                return cls(Path(root).joinpath('__version__.py'), *args, **kwargs)

        # TODO: Support setup.cfg?
        setup_path = Path('setup.py')
        if setup_path.is_file():
            return cls(setup_path, *args, **kwargs)
        raise VersionIncrError('Unable to find __version__.py or setup.py - please specify a --file / -f to modify')
