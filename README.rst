.. image:: https://pyup.io/static/images/logo.png
        :target: https://pyup.io

|

.. image:: https://pyup.io/repos/github/pyupio/pyup/shield.svg
     :target: https://pyup.io/repos/github/pyupio/pyup/
     :alt: Updates

.. image:: https://travis-ci.org/pyupio/pyup.svg?branch=master
        :target: https://travis-ci.org/pyupio/pyup

.. image:: https://readthedocs.org/projects/pyup/badge/?version=latest
        :target: https://readthedocs.org/projects/pyup/?badge=latest
        :alt: Documentation Status


.. image:: https://codecov.io/github/pyupio/pyup/coverage.svg?branch=master
        :target: https://codecov.io/github/pyupio/pyup?branch=master

A tool that updates all your project's Python dependency files through Pull Requests on GitHub/GitLab.

.. image:: https://github.com/pyupio/pyup/raw/master/demo.gif

About
-----

This repo contains the bot that is running at pyup.io. You can install it locally and run the bot through the command line interface.

Documentation: https://pyup.io/docs/

Installation
------------

To install pyup, run::

    $ pip install pyupio

If you want to update Pipfiles, install the optional pipenv extra:

    $ pip install dparse[pipenv]

Obtain Token
------------

In order to communicate with the github API, you need to create an oauth token for your account:

* Log in to your github account
* Click on settings -> Personal access tokens
* Click on Generate new token
* Make sure to check `repo` and `email` and click on Generate token

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


Pyup also has experimental support for Gitlab.  Generate a personal access token
from your profile settings (eg. https://gitlab.com/profile/personal_access_tokens),
then run pyup from the cli::

    # gitlab.com:
    $ pyup --provider gitlab --repo=username/repo --user-token=<YOUR_TOKEN>

Custom Gitlab instance and GitHub Enterprise support
----------------------------------------------------

Pyup offer support for custom Gitlab instances and GitHub Enterprise via the provider_url option::

    $ pyup --provider github --provider_url https://github.enterprise/api/v3 --repo=username/repo --user-token=<YOUR_TOKEN>
    $ pyup --provider gitlab --provider_url https://your.gitlab/ --repo=username/repo --user-token=<YOUR_TOKEN>

    # The alternative method to add a custom gitlab instance is still valid :
    $ pyup --provider gitlab --repo=username/repo --user-token=<YOUR_TOKEN>@https://your.gitlab/


Disable verification of SSL certificate::

    $ pyup --provider github --provider_url https://github.enterprise/api/v3 --repo=username/repo --user-token=<YOUR_TOKEN> --ignore_ssl
    $ pyup --provider gitlab --repo=username/repo --user-token=<YOUR_TOKEN>@https://your.gitlab/ --ignore_ssl

Python 2.7
----------

This tool requires latest Python patch versions starting with version 3.5. We
did support Python 2.7 in the past but, as for other Python 3.x minor versions,
it reached its End-Of-Life and as such we are not able to support it anymore.

We understand you might still have Python 2.7 projects running. At the same
time, PyUp itself has a commitment to encourage developers to keep their
software up-to-date, and it would not make sense for us to work with officially
unsupported Python versions, or even those that reached their end of life.

If you still need to run PyUp from a Python 2.7 environment, please use
version 1.0.2 available at PyPi. Alternatively, you can run PyUp from a
Python 3 environment to check the requirements file for your Python 2.7
project.
