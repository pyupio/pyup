# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from unittest import TestCase
import os
from pyup.legacy_index import get_all_packages, extract_version, remove_extension, get_all_versions


class LegacyIndexTestCase(TestCase):
    def test_get_all_versions(self):
        expected = ['2.13.0', '4.0b4']
        with open(os.path.dirname(os.path.realpath(__file__)) + "/data/legacy_index.html") as f:
            access_control_versions = get_all_versions(f.read())
        self.assertEqual(sorted(access_control_versions), sorted(expected))

    def test_fetch_packages_legacy(self):
        expected = ['AccessControl-2.13.0-py2.6-win-amd64.egg',
                    'AccessControl-4.0b4-cp27-cp27m-win_amd64.whl',
                    'AccessControl-4.0b4-cp35-cp35m-win32.whl',
                    'AccessControl-4.0b4-cp35-cp35m-win_amd64.whl',
                    'AccessControl-4.0b4-cp36-cp36m-win32.whl',
                    'AccessControl-4.0b4-cp36-cp36m-win_amd64.whl',
                    'AccessControl-4.0b4.tar.gz']
        with open(os.path.dirname(os.path.realpath(__file__)) + "/data/legacy_index.html") as f:
            access_control_versions = get_all_packages(f.read())
        self.assertEqual(sorted(access_control_versions), sorted(expected))

    def test_remove_extension(self):
        test_params = [
            ('tar.gz', '4.0b4.tar.gz', '4.0b4'),
            ('zip', '2.13.0.zip', '2.13.0'),
        ]
        for msg, package, expected in test_params:
            self.assertEqual(expected, remove_extension(package))

    def test_extract_versions(self):
        test_params = [
            ('tar.gz', 'AccessControl-4.0b4.tar.gz', '4.0b4'),
            ('whl', 'AccessControl-4.0b4-cp36-cp36m-win_amd64.whl', '4.0b4'),
            ('egg', 'AccessControl-2.13.0-py2.6-win-amd64.egg', '2.13.0'),
            ('zip', 'AccessControl-2.13.0.zip', '2.13.0')
        ]
        for msg, package, expected in test_params:
            self.assertEqual(expected, extract_version(package))
