# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals


class Package(object):
    def __init__(self, name):
        self.name = name
        self._versions = None

    @property
    def versions(self):
        if self._versions is None:
            self._complete_lazy()
        return self.versions

    def _complete_lazy(self):
        self._versions = ["1.2"]
