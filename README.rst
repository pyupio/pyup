.. image:: https://pyup.io/static/images/logo.png
        :target: https://pyup.io

|

.. image:: https://pyup.io/repos/github/pyupio/pyup/shield.svg
     :target: https://pyup.io/repos/github/pyupio/pyup/
     :alt: Updates

.. image:: https://img.shields.io/pypi/v/pyupio.svg
        :target: https://pypi.python.org/pypi/pyupio

.. image:: https://travis-ci.org/pyupio/pyup.svg?branch=master
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

Once your repository is up to date and the initial update is merged in, remove the `--initial` 
flag and run::

    $ pyup --repo=username/repo --user-token=<YOUR_TOKEN>
    
This will create a new branch and a pull request for every single update. Run a cronjob or a scheduled task somewhere 
that auto-updates your repository once in a while (e.g. every day) to stay on latest.

Filtering
---------

You may don't want to update all your requirements to latest, completely ignore
some of them or exclude whole files. That's what filters are for.

To exclude a whole file, add this to the first line::

    # pyup: ignore file


To ignore a package, append the `# pyup: ignore` filter::

    flask # pyup: ignore


If you want to use e.g. the long term support version of Django, which is 1.8 currently, without
updating to the latest version 1.9, just add this filter::

    Django # pyup: >=1.8,<1.9

This tells pyup to use a version that is greater or equal to `1.8` but smaller than `1.9`.

If you are a user of requires.io and you are using the `rq.filter` directive in your files: Pyup
supports that, too.
