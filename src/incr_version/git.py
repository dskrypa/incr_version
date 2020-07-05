import logging
from subprocess import Popen, PIPE

from .exceptions import VersionIncrError

__all__ = ['Git']

log = logging.getLogger(__name__)


class Git:
    @classmethod
    def run(cls, *args):
        cmd = ['git']
        cmd.extend(args)
        cmd_str = ' '.join(cmd)
        log.debug('Executing `{}`'.format(cmd_str))
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        code = proc.wait()
        if code != 0:
            err_msg_parts = ['Error executing `{}` - exit code={}'.format(cmd_str, code)]
            if stdout:
                err_msg_parts.append('stdout:\n{}'.format(stdout))
            if stderr:
                prefix = '\n' if stdout else ''
                err_msg_parts.append('{}stderr:\n{}'.format(prefix, stderr))
            raise VersionIncrError('\n'.join(err_msg_parts))
        if stderr:
            log.warning('Found stderr for cmd=`{}`:\n{}'.format(cmd_str, stderr))
        return stdout.decode('utf-8')

    @classmethod
    def add(cls, *args):
        return cls.run('add', *args)

    @classmethod
    def get_staged(cls):
        files = cls.run('diff', '--name-only', '--cached').splitlines()
        log.debug('Files staged in the current commit:\n{}'.format('\n'.join(files)))
        return set(files)

    @classmethod
    def has_stashed(cls):
        return bool(cls.run('stash', 'list').strip())

    @classmethod
    def staged_changed_lines(cls, path):
        stdout = cls.run('diff', '--staged', '--no-color', '-U0', path)
        for line in stdout.splitlines():
            if line.startswith('+') and not line.startswith('+++ b/'):
                yield line[1:]

    @classmethod
    def get_unstaged_modified(cls):
        if cls.has_stashed():
            staged = cls.get_staged()
            cmd = ('stash', 'show', '--name-status')
        else:
            staged = set()
            cmd = ('diff', '--name-status')

        files = set()
        for line in cls.run(*cmd).splitlines():
            log.debug('diff line={!r}'.format(line))
            status, file = map(str.strip, line.split(maxsplit=1))
            if status == 'M' and file not in staged:
                files.add(file)
            else:
                log.debug('Ignoring file={!r} with status={!r}'.format(file, status))
        log.debug('Modified files NOT staged in the current commit:\n{}'.format('\n'.join(files)))
        return files
