# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from pyup.updates import Update
from unittest import TestCase
from pyup.requirements import Requirement
from unittest.mock import Mock


class UpdateCreateUpdateKeyTest(TestCase):
    def test_unpinned_requirement(self):
        req = Mock()
        req.key = "django"
        req.is_pinned = False
        self.assertEqual(Update.create_update_key(req), "django-pin")

    def test_latest_version_within_specs(self):
        req = Mock()
        req.key = "django"
        req.is_pinned = True
        req.latest_version_within_specs = "1.10"
        self.assertEqual(Update.create_update_key(req), "django-1.10")


class UpdateGetCommitMessageTest(TestCase):

    def test_unpinned_requirement(self):
        req = Mock()
        req.key = "django"
        req.is_pinned = False
        req.latest_version_within_specs = "1.10"
        self.assertEqual(Update.get_commit_message(req), "Pin django to latest version 1.10")

    def test_pinned_requirement(self):
        req = Mock()
        req.key = "django"
        req.is_pinned = True
        req.latest_version_within_specs = "1.10"
        req.version = "1.0"
        self.assertEqual(Update.get_commit_message(req), "Update django from 1.0 to 1.10")


class UpdateInitTestCase(TestCase):
    pass
