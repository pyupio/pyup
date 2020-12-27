# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
import os
from collections import namedtuple
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from .errors import UnsupportedScheduleError

from pyup import settings

TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "templates"
)


class Update(dict):

    @classmethod
    def create_update_key(cls, requirement):
        if requirement.is_pinned:
            key = "{package}-{new_version}".format(
                package=requirement.key,
                new_version=requirement.latest_version_within_specs)
        else:
            key = "{package}-pin".format(package=requirement.key)
        return key

    def __init__(self, requirement_files, config):
        super(dict, self).__init__()
        self.config = config
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

    def get_commit_message(self, requirement):
        if requirement.is_pinned:
            message_template = self.config.commit_message_template_update or "Update {package_name} from {old_version} to {new_version}"
        else:
            message_template = self.config.commit_message_template_pin or "Pin {package_name} to latest version {new_version}"
        return message_template.format(
            package_name=requirement.key,
            old_version=requirement.version,
            new_version=requirement.latest_version_within_specs
        )

    def should_update(self, requirement, requirement_file):
        """
        Determines if a requirement can be updated
        :param requirement: Requirement
        :param requirement_file: RequirementFile
        :return: bool
        """
        path = requirement_file.path
        if self.config.can_update_all(path) or \
                (self.config.can_update_insecure(path) and requirement.is_insecure):
            # handle unpinned requirements only if pin is set
            if not requirement.is_pinned:
                return self.config.can_pin(path)
            return True
        return False

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
        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        changelogs = [u.requirement for u in updates if u.requirement.changelog != {}]
        return env.get_template(
            "scheduled_update_body.md").render(
            {
                "updates": updates,
                "changelogs": changelogs,
                "api_key": settings.api_key
            }
        )

    def get_title(self):
        now = datetime.now()

        if "every day" in self.config.schedule:
            return "Scheduled daily dependency update on {}".format(now.strftime("%A"))
        elif "every week" in self.config.schedule:
            return "Scheduled weekly dependency update for week {}".format(now.strftime("%U"))
        elif "every two weeks" in self.config.schedule:
            return "Scheduled biweekly dependency update for week {}".format(now.strftime("%U"))
        elif "every month" in self.config.schedule:
            return "Scheduled monthly dependency update for {}".format(now.strftime("%B"))
        raise UnsupportedScheduleError("Unsupported schedule {}".format(self.config.schedule))

    def get_branch(self):
        return "scheduled-update-{dt}".format(
            dt=datetime.now().strftime("%Y-%m-%d")
        )


class InitialUpdate(BundledUpdate):

    @classmethod
    def get_body(cls, updates):
        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        changelogs = [u.requirement for u in updates if u.requirement.changelog != {}]
        return env.get_template(
            "initial_update_body.md"
        ).render(
            {
                "updates": updates,
                "changelogs": changelogs,
                "api_key": settings.api_key
            }
        )

    @classmethod
    def get_empty_update_body(cls):
        return "The initial setup worked, but all your packages are up to date. You can safely " \
               "close this issue."

    @classmethod
    def get_title(cls):
        return "Initial Update"

    @classmethod
    def get_branch(cls):
        return "initial-update"


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
            return "update-{}-{}-to-{}".format(
                requirement.key, requirement.version,
                requirement.latest_version_within_specs
            )
        return "pin-{}-{}".format(
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
        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        return env.get_template("sequential_update_body.md").render({
            "requirement": requirement,
            "api_key": settings.api_key
        })
