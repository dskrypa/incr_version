import logging
import os
import re
from datetime import date, datetime
from pathlib import Path
from time import time

from psutil import NoSuchProcess, Process

from .exceptions import VersionIncrError

__all__ = [
    'stdout_write',
    'updated_version_line',
    'running_under_precommit',
    'get_precommit_cached',
    'get_proc',
    'get_git_commit_parent_cmdline',
    'next_version',
    'parse_bool',
]
log = logging.getLogger(__name__)
ON_WINDOWS = os.name == 'nt'


def stdout_write(msg: str, no_pipe_bypass: bool = False):
    if not no_pipe_bypass:
        try:
            # Note: this is not intended to be called more than once per run.
            with open('con:' if ON_WINDOWS else '/dev/tty', 'w', encoding='utf-8') as stdout:
                stdout.write(msg)
        except OSError:  # This may occur if committing via PyCharm, for example
            pass  # The message couldn't be written, so we will fall back to writing to stdout
        else:
            return

    print(msg, end='', flush=True)


def next_version(old_ver: str, force_suffix: bool = False) -> str:
    try:
        old_date_str, old_suffix = old_ver.split('-')
    except ValueError:
        old_date_str = old_ver
        old_suffix = ''

    old_date = datetime.strptime(old_date_str, '%Y.%m.%d').date()
    today = date.today()
    today_str = today.strftime('%Y.%m.%d')
    if old_date < today and not force_suffix:
        return today_str
    else:
        new_suffix = 1 + (int(old_suffix) if old_suffix else 0)
        return f'{today_str}-{new_suffix}'


def updated_version_line(groups, no_pipe_bypass, force_suffix=False, dry_run=False) -> str:
    old_ver = groups[2]
    new_ver = next_version(old_ver, force_suffix)
    if no_pipe_bypass:
        prefix = '[DRY RUN] Would replace' if dry_run else 'Replacing'
        log.info(f'{prefix} old version={old_ver} with new={new_ver}')
    else:
        # Even with pre-commit in verbose mode, this will be printed in-line because of the way it captures then prints
        # output instead of letting output pass thru directly
        prefix = '[DRY RUN] ' if dry_run else ''
        stdout_write(f' {prefix}({old_ver} -> {new_ver}) ')
    return '{0}{1}{2}{1}\n'.format(groups[0], groups[1], new_ver)


def get_git_commit_parent_cmdline() -> list[str] | None:
    for proc in get_proc().parents():
        cmdline = list(map(str.lower, proc.cmdline()))  # noqa
        try:
            prog, arg = cmdline[0:2]
        except (IndexError, ValueError):
            pass
        else:
            if arg == 'commit' and prog.endswith(('\\git.exe', '/git')):
                return cmdline
    return None


def running_under_precommit() -> bool:
    this_proc = get_proc()
    pre_commit_cmd = ['env', '.git/hooks/pre-commit']
    return any(proc.cmdline() == pre_commit_cmd for proc in this_proc.parents())


def get_precommit_cached(ignore_cache_age: bool = False) -> set[str]:
    """
    :param ignore_cache_age: Ignore the age of the cache file and assume that the latest file is for the current
      commit.  Pre-commit does not keep the file open, so it is not possible to examine the open files of the parent
      pre-commit process to determine which is the correct file.  It only stores the filename in its own memory; it does
      not provide any external means of correlating the pid/commit with the file.
    :return: The files that were modified, but not staged for the commit, and were cached in a patch file by pre-commit
    """
    cache_dir = Path('~/.cache/pre-commit/').expanduser().resolve()
    patches = [p.name for p in cache_dir.iterdir() if p.name.startswith('patch')]
    latest = cache_dir.joinpath(max(patches))
    age = time() - latest.stat().st_mtime
    if age > 5 and not ignore_cache_age:
        log.debug(f'The pre-commit cache file is {age:,.3f}s old - ignoring it')
        return set()

    diff_match = re.compile(r'diff --git a/(.*?) b/\1$').match
    with latest.open('r', encoding='utf-8') as f:
        return {m.group(1) for line in f if (m := diff_match(line))}


def get_proc() -> Process:
    pid = os.getpid()
    try:
        return Process(pid)
    except NoSuchProcess as e:  # Not really expected
        raise VersionIncrError(f'Unable to find process with {pid=} (this process)') from e


def parse_bool(value: str | bool) -> bool:
    original = value
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        value = value.strip().lower()
        if value in ('t', 'y', 'yes', 'true', '1'):
            return True
        elif value in ('f', 'n', 'no', 'false', '0'):
            return False
    # ValueError works with argparse to provide a useful error message
    raise ValueError(f'Unable to parse boolean value from input: {original!r}')
