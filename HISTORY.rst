.. :changelog:

History
-------

0.7.0 (2017-7-13)
-----------------

* Fixed a bug on the CLI that prevented hashed requirements to be parsed correctly
* Switched to the new dparse library, adding experimental support for tox and conda files.
* Added support for GitHubs new collaborator invitation system.
* The bot now correctly parses requirement files that begin with a whitespace.
* Fixed a bug with requirement files that had special characters in the filepath.
* Overall improvements with hashed requirement files. Almost all flavors should now be parsed
 correctly
* Added support for Gitlab, thanks a lot to @samdroid-apps
* Added support for compatible releases

0.6.0 (2017-2-1)
----------------

* Fixed the CLI, it should be working again
* Now supports GitHub Integrations (experimental)
* Added new config: PR prefixes, branch prefixes
* Fixed an error not correclty formatting whitespace
* Added support for hashed requirement files
* The bot is now able to write config files to the repo
* Support for environment markers in requirements has been added
* It's now possible to have finer grained control over what's being updated.

0.5.0 (2016-10-21)
------------------
* The bot now parses requirement extras correctly
* Made the config parser more robust
* Fixed a possible endless loop on conflicting PRs
* Added schedules to the config parser
* Now using PyGithub again

0.4.0 (2016-8-30)
-----------------
* Added a new feature: The bot can now add a label to pull requests.

0.3.0 (2016-7-28)
-----------------

* Fixed a bug where a race condition occurred when committing too fast.
* Various parser enhancements
* Empty commits are now filtered out automatically
* The bot now supports custom branches and custom index servers
* Stale pull requests will now be closed automatically
* Switched to setuptools new Requirement implementation
* Enhanced logging
* A lot of smaller bugfixes

0.2.0 (2016-1-7)
----------------

* Added advanced filtering options

0.1.4 (2015-12-30)
------------------

* Fixed a bug with the github provider when committing too fast.
* Requirement content replace function had a bug where not always the right requirement
was replaced

0.1.3 (2015-12-27)
------------------

* PyGithub should be installed as a specific dependency to keep things sane and simple until the
changes on upstream are merged.

0.1.2 (2015-12-27)
------------------

* Use development version of pygithub.

0.1.1 (2015-12-27)
------------------

* Fixed minor packing issue.

0.1 (2015-12-27)
----------------

* (silent) release on PyPI.
