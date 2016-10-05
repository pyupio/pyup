# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from pyup.updates import Update, RequirementUpdate, InitialUpdate, SequentialUpdate, ScheduledUpdate
from unittest import TestCase
from pyup.requirements import RequirementFile
from pyup.errors import UnsupportedScheduleError
from mock import Mock, patch
from datetime import datetime


class UpdateBaseTest(TestCase):

    def setUp(self):
        self.config = Mock()
        self.config.pin_file.return_value = True


class UpdateCreateUpdateKeyTest(UpdateBaseTest):
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


class UpdateGetCommitMessageTest(UpdateBaseTest):
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


class UpdateInitTestCase(UpdateBaseTest):
    def test_init_empty(self):
        update = Update([], self.config)
        self.assertEqual(update, dict())

    def test_init_with_reqs(self):
        with patch("pyup.requirements.Requirement") as req:
            req.needs_update = True
            req_files = [RequirementFile("req.txt", "django")]
            update = Update(req_files, self.config)
            self.assertEqual(len(update.keys()), 1)


class UpdateAddTest(UpdateBaseTest):
    def test_add_with_empty(self):
        update = Update([], self.config)
        req_file = Mock()
        req = Mock()
        req.key = "django"
        req.is_pinned = False
        req.latest_version_within_specs = "1.10"
        update.add(req, req_file)
        self.assertEqual("django-pin" in update, True)
        self.assertEqual(len(update["django-pin"]), 1)

    def test_add_with_match(self):
        update = Update([], self.config)
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


class UpdateGetRequirementUpdateClassTest(UpdateBaseTest):
    def test_class(self):
        update = Update([], self.config)
        self.assertEqual(RequirementUpdate, update.get_requirement_update_class())


class InitialUpdateTestBody(UpdateBaseTest):
    def test_body(self):
        self.assertEqual("", InitialUpdate.get_body([]))


class SequentialUpdateTestBody(UpdateBaseTest):
    def test_body(self):
        self.assertEqual("", SequentialUpdate.get_body([]))


class SequentialUpdateTestTitle(UpdateBaseTest):
    def test_get_title(self):
        req = Mock()
        req.key = "foo"
        req.latest_version_within_specs = "bar"
        self.assertEqual(SequentialUpdate.get_title(req), "Update foo to bar")


class SequentialUpdateTestBrach(UpdateBaseTest):

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


class SequentialUpdateTestGetUpdates(UpdateBaseTest):

    def test_get_updates_empty(self):
        update = SequentialUpdate([], self.config)
        self.assertEqual(len([u for u in update.get_updates()]), 0)

    def test_get_updates(self):
        update = SequentialUpdate([], config=self.config)
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


class InitialUpdateTestGetUpdates(UpdateBaseTest):

    def test_get_updates_empty(self):
        update = InitialUpdate([], self.config)
        self.assertEqual(len([u for u in update.get_updates()]), 0)

    def test_get_updates(self):
        update = InitialUpdate([], config=self.config)
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


class ScheduledUpdateBaseTest(UpdateBaseTest):

    def setUp(self):
        super(ScheduledUpdateBaseTest, self).setUp()
        self.config.is_valid_schedule = True
        self.config.schedule = "every day on monday"
        self.update = ScheduledUpdate([], self.config)


class ScheduledUpdateTest(ScheduledUpdateBaseTest):

    @patch("pyup.updates.datetime")
    def test_title_every_day(self, dt):
        dt.now.return_value = datetime(2016, 9, 13, 9, 21, 42, 702067)
        self.config.schedule = "every day"
        self.assertEquals(
            self.update.get_title(),
            "Scheduled daily dependency update on tuesday"
        )

    @patch("pyup.updates.datetime")
    def test_title_every_week(self, dt):
        dt.now.return_value = datetime(2016, 9, 16, 9, 21, 42, 702067)
        self.config.schedule = "every week on wednesday"
        self.assertEquals(
            self.update.get_title(),
            "Scheduled weekly dependency update for week 37"
        )

    @patch("pyup.updates.datetime")
    def test_title_every_two_weeks(self, dt):
        dt.now.return_value = datetime(2016, 9, 18, 9, 21, 42, 702067)
        self.config.schedule = "every two weeks on sunday"
        self.assertEquals(
            self.update.get_title(),
            "Scheduled biweekly dependency update for week 38"
        )

    @patch("pyup.updates.datetime")
    def test_title_every_month(self, dt):
        dt.now.return_value = datetime(2016, 12, 13, 9, 21, 42, 702067)
        self.config.schedule = "every month"
        self.assertEquals(
            self.update.get_title(),
            "Scheduled monthly dependency update for December"
        )

    def test_title_unsupported_schedule(self):
        with self.assertRaises(UnsupportedScheduleError):
            self.config.schedule = "uhm, what?"
            self.update.get_title()

    @patch("pyup.updates.datetime")
    def test_get_branch(self, dt):
        dt.now.return_value = datetime(2016, 12, 13, 9, 21, 42, 702067)
        self.assertEquals(
            self.update.get_branch(),
            "pyup-scheduled-update-12-13-2016"
        )

    def test_get_body(self):
        self.assertEquals("", self.update.get_body([]))
