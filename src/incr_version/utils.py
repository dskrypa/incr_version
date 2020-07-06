import logging
import os
import platform
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

from .exceptions import VersionIncrError

__all__ = [
    'stdout_write', 'updated_version_line', 'running_under_precommit', 'get_precommit_cached', 'get_proc',
    'get_git_commit_parent_cmdline', 'next_version', 'parse_bool'
]
log = logging.getLogger(__name__)

ON_WINDOWS = platform.system().lower() == 'windows'


def stdout_write(msg, no_pipe_bypass=False):
    if no_pipe_bypass:
        sys.stdout.write(msg)
        sys.stdout.flush()
    else:  # Not intended to be called more than once per run.
        with open('con:' if ON_WINDOWS else '/dev/tty', 'w', encoding='utf-8') as stdout:
            stdout.write(msg)


def next_version(old_ver, force_suffix=False):
    try:
        old_date_str, old_suffix = old_ver.split('-')
    except ValueError:
        old_date_str = old_ver
        old_suffix = ''

    old_date = datetime.strptime(old_date_str, '%Y.%m.%d').date()
    today = datetime.now().date()
    today_str = today.strftime('%Y.%m.%d')
    if old_date < today and not force_suffix:
        return today_str
    else:
        new_suffix = 1 + (int(old_suffix) if old_suffix else 0)
        return '{}-{}'.format(today_str, new_suffix)


def updated_version_line(groups, no_pipe_bypass, force_suffix=False, dry_run=False):
    old_ver = groups[2]
    new_ver = next_version(old_ver, force_suffix)
    if no_pipe_bypass:
        prefix = '[DRY RUN] Would replace' if dry_run else 'Replacing'
        log.info('{} old version={} with new={}'.format(prefix, old_ver, new_ver))
    else:
        # Even with pre-commit in verbose mode, this will be printed in-line because of the way it captures then prints
        # output instead of letting output pass thru directly
        prefix = '[DRY RUN] ' if dry_run else ''
        stdout_write(' {}({} -> {}) '.format(prefix, old_ver, new_ver))
    return '{0}{1}{2}{1}\n'.format(groups[0], groups[1], new_ver)


def get_git_commit_parent_cmdline():
    for proc in get_proc().parents():
        cmdline = list(map(str.lower, proc.cmdline()))
        try:
            prog, arg = cmdline[0:2]
        except (IndexError, ValueError):
            pass
        else:
            if arg == 'commit' and prog.endswith(('\\git.exe', '/git')):
                return cmdline
    return None


def running_under_precommit():
    this_proc = get_proc()
    pre_commit_cmd = ['env', '.git/hooks/pre-commit']
    return any(proc.cmdline() == pre_commit_cmd for proc in this_proc.parents())


def get_precommit_cached(ignore_cache_age=False):
    """
    :param bool ignore_cache_age: Ignore the age of the cache file and assume that the latest file is for the current
      commit.  Pre-commit does not keep the file open, so it is not possible to examine the open files of the parent
      pre-commit process to determine which is the correct file.  It only stores the filename in its own memory; it does
      not provide any external means of correlating the pid/commit with the file.
    :return set: The files that were modified, but not staged for the commit, and were cached in a patch file by
      pre-commit
    """
    cache_dir = Path('~/.cache/pre-commit/').expanduser().resolve()
    patches = [p.name for p in cache_dir.iterdir() if p.name.startswith('patch')]
    latest = cache_dir.joinpath(max(patches))
    age = time.time() - latest.stat().st_mtime
    if age > 5 and not ignore_cache_age:
        log.debug('The pre-commit cache file is {:,.3f}s old - ignoring it')
        return set()

    diff_match = re.compile(r'diff --git a/(.*?) b/\1$').match
    files = set()
    with latest.open('r', encoding='utf-8') as f:
        for line in f:
            m = diff_match(line)
            if m:
                files.add(m.group(1))
    return files


def get_proc():
    pid = os.getpid()
    for proc in psutil.process_iter():
        if proc.pid == pid:
            return proc
    raise VersionIncrError('Unable to find process with pid={} (this process)'.format(pid))


def parse_bool(value):
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
    raise ValueError('Unable to parse boolean value from input: {!r}'.format(original))
