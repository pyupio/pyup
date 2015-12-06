# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from collections import namedtuple


class Update(dict):

    @classmethod
    def create_update_key(cls, requirement):
        key = requirement.key
        if not requirement.is_pinned:
            key += '-pin'
        else:
            key += "-" + requirement.latest_version_within_specs
        return key

    def __init__(self, requirement_files):
        super(dict, self).__init__()

        for requirement_file in requirement_files:
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

    def get_requirement_update_class(self):
        return RequirementUpdate


class InitialUpdate(Update):

    def get_updates(self):
        if self:
            yield (
                "Initial Update",
                self.get_body([update for updates in self.values() for update in updates]),
                "pyup-initial-update",
                [update for updates in self.values() for update in updates]
            )

    @classmethod
    def get_body(cls, updates):
        return ""


RequirementUpdate = namedtuple("RequirementUpdate", ["requirement_file", "requirement", "commit_message"])


class SequentialUpdate(Update):

    def get_updates(self):
        for key, updates in self.items():
            requirement = updates[0]
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
        return "Update {} to {}".format(
            requirement.key,
            requirement.latest_version_within_specs
        )

    @classmethod
    def get_body(cls, requirement):
        return ""
