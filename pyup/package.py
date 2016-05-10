# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from pkg_resources import parse_version
import requests


def fetch_package(name, index_server=None):
    url = index_server + name if index_server else \
        "https://pypi.python.org/pypi/{name}/json".format(name=name)
    r = requests.get(url, timeout=3)
    if r.status_code != 200:
        return None
    json = r.json()
    if index_server:
        releases = sorted(json["result"].keys(), key=lambda v: parse_version(v), reverse=True)
    else:
        releases = sorted(json["releases"].keys(), key=lambda v: parse_version(v), reverse=True)
    return Package(name, releases)


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
