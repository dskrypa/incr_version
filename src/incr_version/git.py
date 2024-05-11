import logging
from subprocess import PIPE, Popen
from typing import Iterator

from .exceptions import VersionIncrError
from .utils import get_git_commit_parent_cmdline

__all__ = ['Git']
log = logging.getLogger(__name__)


class Git:
    @classmethod
    def run(cls, *args: str) -> str:
        cmd = ['git', *args]
        cmd_str = ' '.join(cmd)
        log.debug(f'Executing `{cmd_str}`')
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        if (code := proc.wait()) != 0:
            err_msg_parts = [f'Error executing `{cmd_str}` - exit {code=}']
            if stdout:
                err_msg_parts.append(f'stdout:\n{stdout}')
            if stderr:
                prefix = '\n' if stdout else ''
                err_msg_parts.append(f'{prefix}stderr:\n{stderr}')
            raise VersionIncrError('\n'.join(err_msg_parts))
        if stderr:
            log.warning(f'Found stderr for cmd=`{cmd_str}`:\n{stderr}')
        return stdout.decode('utf-8')

    @classmethod
    def add(cls, *args: str) -> str:
        return cls.run('add', *args)

    @classmethod
    def get_staged(cls) -> set[str]:
        files = cls.run('diff', '--name-only', '--cached').splitlines()
        log.debug('Files staged in the current commit:\n' + '\n'.join(files))
        return set(files)

    @classmethod
    def has_stashed(cls) -> bool:
        return bool(cls.run('stash', 'list').strip())

    @classmethod
    def staged_changed_lines(cls, path: str) -> Iterator[str]:
        stdout = cls.run('diff', '--staged', '--no-color', '-U0', path)
        for line in stdout.splitlines():
            if line.startswith('+') and not line.startswith('+++ b/'):
                yield line[1:]

    @classmethod
    def get_unstaged_modified(cls) -> set[str]:
        if cls.has_stashed():
            staged = cls.get_staged()
            cmd = ('stash', 'show', '--name-status')
        else:
            staged = set()
            cmd = ('diff', '--name-status')

        files = set()
        for line in cls.run(*cmd).splitlines():
            log.debug(f'diff {line=}')
            status, file = map(str.strip, line.split(maxsplit=1))
            if status == 'M' and file not in staged:
                files.add(file)
            else:
                log.debug(f'Ignoring {file=} with {status=}')
        log.debug('Modified files NOT staged in the current commit:\n' + '\n'.join(files))
        return files

    @classmethod
    def get_current_commit_command(cls) -> list[str] | None:
        return get_git_commit_parent_cmdline()

    @classmethod
    def current_commit_is_amending(cls) -> bool:
        if cmdline := get_git_commit_parent_cmdline():
            return '--amend' in cmdline
        return False
