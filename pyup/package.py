# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from pkg_resources import parse_version
import requests


def fetch_package(name):
    r = requests.get("https://pypi.python.org/pypi/{name}/json".format(name=name), timeout=3)
    if r.status_code != 200:
        return None
    json = r.json()
    return Package(
        name,
        sorted(json["releases"].keys(), key=lambda v: parse_version(v), reverse=True)
    )


class Package(object):
    def __init__(self, name, versions):
        self.name = name
        self.versions = versions

    def latest_version(self, prereleases=False):
        for version in self.versions:
            if prereleases or not parse_version(version).is_prerelease:
                return version
        # we have not found a version here, we might find one in prereleases
        if self.versions and not prereleases:
            return self.latest_version(prereleases=True)
        return None
