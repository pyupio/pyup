# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from collections import namedtuple
from datetime import datetime
from .errors import UnsupportedScheduleError


class Update(dict):

    @classmethod
    def create_update_key(cls, requirement):
        key = requirement.key
        if not requirement.is_pinned:
            key += '-pin'
        else:
            key += "-" + requirement.latest_version_within_specs
        return key

    def __init__(self, requirement_files, config):
        super(dict, self).__init__()
        self.config = config
        for requirement_file in requirement_files:
            if self.config.pin_file(requirement_file.path):
                for requirement in requirement_file.requirements:
                    if requirement.needs_update:
                        self.add(requirement, requirement_file)

    def add(self, requirement, requirement_file):
        key = self.create_update_key(requirement)
        update = RequirementUpdate(
            requirement=requirement,
            requirement_file=requirement_file,
            commit_message=self.get_commit_message(requirement)
        )
        if key in self:
            self[key].append(update)
        else:
            self[key] = [update]

    @classmethod
    def get_commit_message(cls, requirement):
        if requirement.is_pinned:
            return "Update {} from {} to {}".format(
                requirement.key, requirement.version,
                requirement.latest_version_within_specs
            )
        return "Pin {} to latest version {}".format(
            requirement.key,
            requirement.latest_version_within_specs
        )

    def should_update(self, requirement, requirement_file):
        # handle unpinned requirements only if pin is set
        return self.config.pin_file(requirement_file.path)

    def get_requirement_update_class(self):
        return RequirementUpdate


class BundledUpdate(Update):

    def get_updates(self):
        if self:
            yield (
                self.get_title(),
                self.get_body([update for updates in self.values() for update in updates
                               if
                               self.should_update(update.requirement, update.requirement_file)]),
                self.get_branch(),
                [update for updates in self.values() for update in updates if
                 self.should_update(update.requirement, update.requirement_file)]
            )

    @classmethod
    def get_branch(cls):  # pragma: no cover
        raise NotImplementedError

    @classmethod
    def get_body(cls, updates):  # pragma: no cover
        raise NotImplementedError

    @classmethod
    def get_empty_update_body(cls):  # pragma: no cover
        raise NotImplementedError

    @classmethod
    def get_title(cls):  # pragma: no cover
        raise NotImplementedError


class ScheduledUpdate(BundledUpdate):

    @classmethod
    def get_body(cls, updates):
        return ""

    def get_title(self):
        now = datetime.now()

        if "every day" in self.config.schedule:
            return "Scheduled daily dependency update on {}".format(now.strftime("%A").lower())
        elif "every week" in self.config.schedule:
            return "Scheduled weekly dependency update for week {}".format(now.strftime("%U"))
        elif "every two weeks" in self.config.schedule:
            return "Scheduled biweekly dependency update for week {}".format(now.strftime("%U"))
        elif "every month" in self.config.schedule:
            return "Scheduled monthly dependency update for {}".format(now.strftime("%B"))
        raise UnsupportedScheduleError("Unsupported schedule {}".format(self.config.schedule))

    def get_branch(self):
        return "pyup-scheduled-update-{dt}".format(
            dt=datetime.now().strftime("%m-%d-%Y")
        )


class InitialUpdate(BundledUpdate):

    @classmethod
    def get_body(cls, updates):
        return ""

    @classmethod
    def get_empty_update_body(cls):
        return "The initial setup worked, but all your packages are up to date. You can safely " \
               "close this issue."

    @classmethod
    def get_title(cls):
        return "Initial Update"

    @classmethod
    def get_branch(cls):
        return "pyup-initial-update"


RequirementUpdate = namedtuple(
    "RequirementUpdate",
    ["requirement_file", "requirement", "commit_message"]
)


class SequentialUpdate(Update):

    def get_updates(self):
        for key, updates in self.items():
            requirement, req_file = updates[0].requirement, updates[0].requirement_file
            if self.should_update(requirement, req_file):
                yield (
                    self.get_title(requirement),
                    self.get_body(requirement),
                    self.get_branch(requirement),
                    updates
                )

    @classmethod
    def get_branch(cls, requirement):
        if requirement.is_pinned:
            return "pyup-update-{}-{}-to-{}".format(
                requirement.key, requirement.version,
                requirement.latest_version_within_specs
            )
        return "pyup-pin-{}-{}".format(
            requirement.key,
            requirement.latest_version_within_specs
        )

    @classmethod
    def get_title(cls, requirement):
        if requirement.is_pinned:
            return "Update {} to {}".format(
                requirement.key,
                requirement.latest_version_within_specs
            )
        return "Pin {} to latest version {}".format(
            requirement.key,
            requirement.latest_version_within_specs
        )

    @classmethod
    def get_body(cls, requirement):
        return ""
