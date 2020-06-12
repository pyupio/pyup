# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals


class PullRequest(object):

    UPDATE_TYPE = "update"
    SECURITY_TYPE = "security"
    PIN_TYPE = "pin"
    INITIAL_TYPE = "initial"
    COMPILE_TYPE = "compile"
    SCHEDULED_TYPE = "scheduled"
    CONFIG_ERROR_TYPE = "config"
    UNKNOWN_TYPE = "unknown"

    def __init__(self, state, title, url, created_at, number=None, issue=False):
        self.state = state
        self.title = title
        self.url = url
        self.created_at = created_at
        self.number = number
        self.issue = issue

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.number == other.number

    def canonical_title(self, prefix):
        return self.title.replace("{} ".format(prefix), "") if prefix else self.title

    @property
    def type(self):
        if "Update " in self.title:
            return PullRequest.UPDATE_TYPE
        elif "Security" in self.title:
            return PullRequest.SECURITY_TYPE
        elif "Pin" in self.title:
            return PullRequest.PIN_TYPE
        elif "Initial" in self.title:
            return PullRequest.INITIAL_TYPE
        elif "Compile" in self.title:
            return PullRequest.COMPILE_TYPE
        elif "Scheduled" in self.title:
            return PullRequest.SCHEDULED_TYPE
        elif "Invalid .pyup.yml" in self.title:
            return PullRequest.CONFIG_ERROR_TYPE
        return PullRequest.UNKNOWN_TYPE

    @property
    def is_update(self):
        return self.type == self.UPDATE_TYPE

    @property
    def is_security(self):
        return self.type == self.SECURITY_TYPE

    @property
    def is_pin(self):
        return self.type == self.PIN_TYPE

    @property
    def is_initial(self):
        return self.type == self.INITIAL_TYPE

    @property
    def is_compile(self):
        return self.type == self.COMPILE_TYPE

    @property
    def is_scheduled(self):
        return self.type == self.SCHEDULED_TYPE

    @property
    def is_config_error(self):
        return self.type == self.CONFIG_ERROR_TYPE

    @property
    def is_open(self):
        return self.state in ("open", "opened")

    @property
    def is_valid(self):
        return self.is_update or self.is_security \
               or self.is_pin or self.is_initial \
               or self.is_compile or self.is_scheduled \
               or self.is_config_error

    def get_requirement(self, prefix=""):
        if self.type != "initial":
            title = self.canonical_title(prefix)
            parts = title.split(" ")
            if len(parts) >= 2:
                return parts[1].lower()
        return None
