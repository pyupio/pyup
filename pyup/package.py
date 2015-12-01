# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from pkg_resources import parse_version

class Package(object):
    def __init__(self, name):
        self.name = name
        self._versions = None

    @property
    def versions(self):
        if self._versions is None:
            self._complete_lazy()
        return self._versions

    def _complete_lazy(self):
        self._versions = ["1.2"]

    def latest_version(self, prereleases=False):
        for version in self.versions:
            if prereleases or not parse_version(version).is_prerelease:
                return version
        # we have not found a version here, we might find one in prereleases
        if self.versions and not prereleases:
            return self.latest_version(prereleases=True)
        return None

