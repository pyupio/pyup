.. image:: https://pyupio.a.cdnify.io/images/logo.png
        :target: https://pyup.io

|

.. image:: https://img.shields.io/pypi/v/pyupio.svg
        :target: https://pypi.python.org/pypi/pyupio

.. image:: https://img.shields.io/travis/pyupio/pyup.svg
        :target: https://travis-ci.org/pyupio/pyup

.. image:: https://readthedocs.org/projects/pyup/badge/?version=latest
        :target: https://readthedocs.org/projects/pyup/?badge=latest
        :alt: Documentation Status


.. image:: https://codecov.io/github/pyupio/pyup/coverage.svg?branch=master
        :target: https://codecov.io/github/pyupio/pyup?branch=master

A tool to update all your project's requirement files with a single command directly on github.

.. image:: https://github.com/pyupio/pyup/blob/master/demo.gif

About
-----

Pyup is the open source version of the online service that is running behind pyup.io. The online
service comes with a user interface to manage all your project dependencies at a single place and a
lot of additional features. It's currently in closed beta. If you are interested to try it out,
make sure to request an invite at https://pyup.io


Installation
------------

To install pyup, run::

    $ pip install pyupio
    $ pip install -e git+https://github.com/jayfk/PyGithub.git@top#egg=PyGithub


Obtain Token
------------

In order to communicate with the github API, you need to create an oauth token for your account:

* Log in to your github account
* Click on settings -> Personal access tokens
* Click on Generate new token
* Make sure to check 'repo' and click on Generate token

Run your first Update
---------------------

Run::

    $ pyup --repo=username/repo --user-token=<YOUR_TOKEN> --initial


This will check all your requirement files and search for new package versions. If there are
updates available, pyup will create a new branch on your repository and create a new commit for
every single update. Once all files are up to date, pyup will create a single pull request containing
all commits.
