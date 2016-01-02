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

    def __init__(self, requirement_files, pin_unpinned=False):
        super(dict, self).__init__()
        self.pin_unpinned = pin_unpinned
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

    def should_update(self, requirement):
        # handle unpinned requirements only if pin_unpinned is set
        return requirement.is_pinned or self.pin_unpinned

    def get_requirement_update_class(self):
        return RequirementUpdate


class InitialUpdate(Update):

    def get_updates(self):
        if self:
            yield (
                self.get_title(),
                self.get_body([update for updates in self.values() for update in updates
                               if self.should_update(update.requirement)]),
                "pyup-initial-update",
                [update for updates in self.values() for update in updates if
                 self.should_update(update.requirement)]
            )

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


RequirementUpdate = namedtuple(
    "RequirementUpdate",
    ["requirement_file", "requirement", "commit_message"]
)


class SequentialUpdate(Update):

    def get_updates(self):
        for key, updates in self.items():
            requirement = updates[0].requirement
            if self.should_update(requirement):
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
