# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from packaging.version import parse as parse_version
from pyup import legacy_index
import requests


def _extract_releases(response, index_server):
    try:
        json = response.json()
        if index_server:
            return sorted(json["result"].keys(), key=lambda v: parse_version(v), reverse=True)
        else:
            return sorted(json["releases"].keys(), key=lambda v: parse_version(v), reverse=True)
    except ValueError:
        if index_server:
            return sorted(legacy_index.get_all_versions(response.text), key=lambda v: parse_version(v), reverse=True)


def fetch_package(name, index_server=None):
    url = index_server + name if index_server else \
        "https://pypi.org/pypi/{name}/json".format(name=name)
    r = requests.get(url, timeout=3)
    if r.status_code != 200:
        return None
    return Package(name, _extract_releases(r, index_server))


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
