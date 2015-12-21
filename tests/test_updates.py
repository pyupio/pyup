# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from pyup.updates import Update, RequirementUpdate, InitialUpdate, SequentialUpdate
from unittest import TestCase
from pyup.requirements import RequirementFile
from mock import Mock, patch


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
    def test_init_empty(self):
        update = Update([])
        self.assertEqual(update, dict())

    def test_init_with_reqs(self):
        with patch("pyup.requirements.Requirement") as req:
            req.needs_update = True
            req_files = [RequirementFile("req.txt", "django")]
            update = Update(req_files)
            self.assertEqual(len(update.keys()), 1)


class UpdateAddTest(TestCase):
    def test_add_with_empty(self):
        update = Update([])
        req_file = Mock()
        req = Mock()
        req.key = "django"
        req.is_pinned = False
        req.latest_version_within_specs = "1.10"
        update.add(req, req_file)
        self.assertEqual("django-pin" in update, True)
        self.assertEqual(len(update["django-pin"]), 1)

    def test_add_with_match(self):
        update = Update([])
        req_file = Mock()
        req = Mock()
        req.key = "django"
        req.is_pinned = False
        req.latest_version_within_specs = "1.10"
        update.add(req, req_file)
        self.assertEqual("django-pin" in update, True)
        self.assertEqual(len(update["django-pin"]), 1)
        update.add(req, req_file)
        self.assertEqual(len(update["django-pin"]), 2)


class UpdateGetRequirementUpdateClassTest(TestCase):
    def test_class(self):
        update = Update([])
        self.assertEqual(RequirementUpdate, update.get_requirement_update_class())


class InitialUpdateTestBody(TestCase):
    def test_body(self):
        self.assertEqual("", InitialUpdate.get_body([]))


class SequentialUpdateTestBody(TestCase):
    def test_body(self):
        self.assertEqual("", SequentialUpdate.get_body([]))


class SequentialUpdateTestTitle(TestCase):
    def test_get_title(self):
        req = Mock()
        req.key = "foo"
        req.latest_version_within_specs = "bar"
        self.assertEqual(SequentialUpdate.get_title(req), "Update foo to bar")


class SequentialUpdateTestBrach(TestCase):

    def test_requirement_pinned(self):
        req = Mock()
        req.key = "django"
        req.is_pinned = True
        req.latest_version_within_specs = "1.10"
        req.version = "1.0"
        self.assertEqual(SequentialUpdate.get_branch(req), "pyup-update-django-1.0-to-1.10")

    def test_requirement_not_pinned(self):
        req = Mock()
        req.key = "django"
        req.is_pinned = False
        req.latest_version_within_specs = "1.10"
        self.assertEqual(SequentialUpdate.get_branch(req), "pyup-pin-django-1.10")


class SequentialUpdateTestGetUpdates(TestCase):

    def test_get_updates_empty(self):
        update = SequentialUpdate([])
        self.assertEqual(len([u for u in update.get_updates()]), 0)

    def test_get_updates(self):
        update = SequentialUpdate([], pin_unpinned=True)
        req_file = Mock()
        req = Mock()
        req.key = "django"
        req.is_pinned = False
        req.latest_version_within_specs = "1.10"
        update.add(req, req_file)
        self.assertEqual("django-pin" in update, True)
        self.assertEqual(len(update["django-pin"]), 1)
        update.add(req, req_file)
        self.assertEqual(len(update["django-pin"]), 2)

        updates = [u for u in update.get_updates()]
        self.assertEqual(len(updates), 1)


class InitialUpdateTestGetUpdates(TestCase):

    def test_get_updates_empty(self):
        update = InitialUpdate([])
        self.assertEqual(len([u for u in update.get_updates()]), 0)

    def test_get_updates(self):
        update = InitialUpdate([], pin_unpinned=True)
        req_file = Mock()
        req = Mock()
        req.key = "django"
        req.is_pinned = False
        req.latest_version_within_specs = "1.10"
        update.add(req, req_file)
        self.assertEqual("django-pin" in update, True)
        self.assertEqual(len(update["django-pin"]), 1)
        update.add(req, req_file)
        self.assertEqual(len(update["django-pin"]), 2)

        updates = [u for u in update.get_updates()]
        self.assertEqual(len(updates), 1)
