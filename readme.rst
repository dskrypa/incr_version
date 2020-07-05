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
