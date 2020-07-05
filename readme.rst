incr_version
============

Python project version auto-incrementer


Installation
------------

To configure incr_version as a pre-commit hook, add the following to your ``.pre-commit-config.yaml``::

    repos:
      - repo: https://github.com/dskrypa/incr_version
        rev: HEAD
        hooks:
          - id: incr_version

If your ``__version__`` file is not automatically detected, then you can specify the path to it like this::

      - repo: https://github.com/dskrypa/incr_version
        rev: HEAD
        hooks:
          - id: incr_version
            args: ['-f', 'path/to/__version__.py']


Note: The ``HEAD`` value will be updated to a specific revision when you run ``pre-commit autoupdate``.  Running it
again when a new version is available will continue to result in receiving the updated version if that value is saved.


Options
-------

+-------------------------------+--------------------------------------------------------------------------------------+
| Argument                      | Description                                                                          |
+===============================+======================================================================================+
| ``--file`` / ``-f``           | The file that contains the version to be incremented                                 |
+-------------------------------+--------------------------------------------------------------------------------------+
| ``--encoding`` / ``-e``       | The encoding used by the version file (default: utf-8)                               |
+-------------------------------+--------------------------------------------------------------------------------------+
| ``--suffix`` / ``-s``         | Force use of a numeric suffix, even on the first version for a given day             |
+-------------------------------+--------------------------------------------------------------------------------------+
| ``--no_add`` / ``-A``         | Do not add the version file to git after making changes to it (for testing purposes) |
+-------------------------------+--------------------------------------------------------------------------------------+
| ``--ignore_staged`` / ``-i``  | Assume already staged version file contains updated version                          |
+-------------------------------+--------------------------------------------------------------------------------------+
| ``--no_pipe_bypass`` / ``-B`` | Do not bypass pre-commit's stdout pipe when printing the updated version number      |
+-------------------------------+--------------------------------------------------------------------------------------+
| ``--debug`` / ``-d``          | Show debug logging                                                                   |
+-------------------------------+--------------------------------------------------------------------------------------+
