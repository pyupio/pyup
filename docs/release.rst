Releasing
======================================

In order to release a new version, add the changes under the new version number to HISTORY.rst
and then run::

    $ bumpversion [major|minor|patch]
    $ git push origin master

When all tests are passing, travis will auto release a new version.
