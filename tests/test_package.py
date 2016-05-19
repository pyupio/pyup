# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from unittest import TestCase
import requests_mock
import os
from pyup.package import fetch_package, Package

def package_factory(name, versions):
    p = Package(name=name, versions=versions)
    return p


class FetchPackageTestCase(TestCase):

    @requests_mock.mock()
    def test_fetch_package_devpi(self, requests):
        with open(os.path.dirname(os.path.realpath(__file__)) + "/data/django-devpi.json") as f:
            requests.get("https://some.foo/root/pypi/Django", text=f.read())
        package = fetch_package("Django", "https://some.foo/root/pypi/")
        self.assertNotEqual(package, None)
        self.assertEqual(
            package.versions,
            ['1.9.6', '1.9.5', '1.9.4', '1.9.3', '1.9.2', '1.9.1', '1.9', '1.9rc2', '1.9rc1',
             '1.9b1', '1.9a1', '1.8.13', '1.8.12', '1.8.11', '1.8.10', '1.8.9', '1.8.8',
             '1.8.7', '1.8.6', '1.8.5', '1.8.4', '1.8.3', '1.8.2', '1.8.1', '1.8', '1.8c1',
             '1.8b2', '1.8b1', '1.8a1', '1.7.11', '1.7.10', '1.7.9', '1.7.8', '1.7.7', '1.7.6',
             '1.7.5', '1.7.4', '1.7.3', '1.7.2', '1.7.1', '1.7', '1.6.11', '1.6.10', '1.6.9',
             '1.6.8', '1.6.7', '1.6.6', '1.6.5', '1.6.4', '1.6.3', '1.6.2', '1.6.1', '1.6',
             '1.5.12', '1.5.11', '1.5.10', '1.5.9', '1.5.8', '1.5.7', '1.5.6', '1.5.5',
             '1.5.4', '1.5.3', '1.5.2', '1.5.1', '1.5', '1.4.22', '1.4.21', '1.4.20',
             '1.4.19', '1.4.18', '1.4.17', '1.4.16', '1.4.15', '1.4.14', '1.4.13', '1.4.12',
             '1.4.11', '1.4.10', '1.4.9', '1.4.8', '1.4.7', '1.4.6', '1.4.5', '1.4.4', '1.4.3',
             '1.4.2', '1.4.1', '1.4', '1.3.7', '1.3.6', '1.3.5', '1.3.4', '1.3.3', '1.3.2',
             '1.3.1', '1.3', '1.2.7', '1.2.6', '1.2.5', '1.2.4', '1.2.3', '1.2.2', '1.2.1',
             '1.2', '1.1.4', '1.1.3']
        )


    @requests_mock.mock()
    def test_fetch_packages(self, requests):
        with open(os.path.dirname(os.path.realpath(__file__)) + "/data/django.json") as f:
            requests.get("https://pypi.python.org/pypi/Django/json", text=f.read())

        package = fetch_package("Django")
        self.assertNotEqual(package, None)
        self.assertEqual(
            package.versions,
            ['1.9rc1', '1.9b1', '1.9a1', '1.8.6', '1.8.5', '1.8.4', '1.8.3', '1.8.2', '1.8.1',
             '1.8', '1.8c1', '1.8b2', '1.8b1', '1.8a1', '1.7.10', '1.7.9', '1.7.8', '1.7.7',
             '1.7.6', '1.7.5', '1.7.4', '1.7.3', '1.7.2', '1.7.1', '1.7', '1.6.11', '1.6.10',
             '1.6.9', '1.6.8', '1.6.7', '1.6.6', '1.6.5', '1.6.4', '1.6.3', '1.6.2', '1.6.1',
             '1.6', '1.5.12', '1.5.11', '1.5.10', '1.5.9', '1.5.8', '1.5.7', '1.5.6', '1.5.5',
             '1.5.4', '1.5.3', '1.5.2', '1.5.1', '1.5', '1.4.22', '1.4.21', '1.4.20', '1.4.19',
             '1.4.18', '1.4.17', '1.4.16', '1.4.15', '1.4.14', '1.4.13', '1.4.12', '1.4.11',
             '1.4.10', '1.4.9', '1.4.8', '1.4.7', '1.4.6', '1.4.5', '1.4.4', '1.4.3', '1.4.2',
             '1.4.1', '1.4', '1.3.7', '1.3.6', '1.3.5', '1.3.4', '1.3.3', '1.3.2', '1.3.1', '1.3',
             '1.2.7', '1.2.6', '1.2.5', '1.2.4', '1.2.3', '1.2.2', '1.2.1', '1.2', '1.1.4',
             '1.1.3', '1.1.2', '1.1.1', '1.1', '1.0.4', '1.0.3', '1.0.2', '1.0.1']
        )

    @requests_mock.mock()
    def test_fetch_packages_status_code_not_200(self, requests):
        requests.get("https://pypi.python.org/pypi/Django/json", text="ERROR", status_code=500)
        self.assertEqual(fetch_package("Django"), None)

    @requests_mock.mock()
    def test_fetch_packages_404(self, requests):
        requests.get("https://pypi.python.org/pypi/Django/json", text="404", status_code=404)
        self.assertEqual(fetch_package("Django"), None)


class PackageVersionTestCase(TestCase):
    def test_version_normal(self):
        pkg = package_factory("django", ["1.8", "1.7"])
        self.assertEqual(pkg.latest_version(), "1.8")

        pkg = package_factory("django", ["1.9rc1", "1.8"])
        self.assertEqual(pkg.latest_version(), "1.8")

    def test_version_prereleases(self):
        pkg = package_factory("django", ["1.8", "1.7"])
        self.assertEqual(pkg.latest_version(), "1.8")

        pkg = package_factory("django", ["1.9rc1", "1.8"])
        self.assertEqual(pkg.latest_version(prereleases=True), "1.9rc1")

    def test_version_prereleases_only(self):
        pkg = package_factory("django", ["1.9rc1"])
        self.assertEqual(pkg.latest_version(prereleases=False), "1.9rc1")

    def test_version_empty(self):
        pkg = package_factory("django", [])
        self.assertEqual(pkg.latest_version(), None)
