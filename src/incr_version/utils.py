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
    'get_git_commit_parent_cmdline'
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


def updated_version_line(groups, no_pipe_bypass, force_suffix=False):
    old_date_str = groups[2]
    old_date = datetime.strptime(old_date_str, '%Y.%m.%d').date()
    old_suffix = groups[3]
    old_ver = old_date_str + old_suffix

    today = datetime.now().date()
    today_str = today.strftime('%Y.%m.%d')
    if old_date < today and not force_suffix:
        # log.info('Replacing old version={} with new={}'.format(old_ver, today_str))
        stdout_write('\nUpdating version from {} to {}\n'.format(old_ver, today_str), no_pipe_bypass)
        return '{0}{1}{2}{1}\n'.format(groups[0], groups[1], today_str)
    else:
        if old_suffix:
            new_suffix = int(old_suffix[1:]) + 1
        else:
            new_suffix = 1
        # log.info('Replacing old version={} with new={}-{}'.format(old_ver, today_str, new_suffix))
        stdout_write('\nUpdating version from {} to {}-{}\n'.format(old_ver, today_str, new_suffix), no_pipe_bypass)
        return '{0}{1}{2}-{3}{1}\n'.format(groups[0], groups[1], today_str, new_suffix)


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
