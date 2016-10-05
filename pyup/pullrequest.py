# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals


class PullRequest(object):

    UPDATE_TYPE = "update"
    SECURITY_TYPE = "security"
    PIN_TYPE = "pin"
    INITIAL_TYPE = "initial"
    COMPILE_TYPE = "compile"
    SCHEDULED_TYPE = "scheduled"
    UNKNOWN_TYPE = "unknown"

    def __init__(self, state, title, url, created_at, number=None, issue=False):
        self.state = state
        self.title = title
        self.url = url
        self.created_at = created_at
        self.number = number
        self.issue = issue

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    @property
    def type(self):
        if self.title.startswith("Update"):
            return PullRequest.UPDATE_TYPE
        elif self.title.startswith("Security"):
            return PullRequest.SECURITY_TYPE
        elif self.title.startswith("Pin"):
            return PullRequest.PIN_TYPE
        elif self.title.startswith("Initial"):
            return PullRequest.INITIAL_TYPE
        elif self.title.startswith("Compile"):
            return PullRequest.COMPILE_TYPE
        elif self.title.startswith("Scheduled"):
            return PullRequest.SCHEDULED_TYPE
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
    def is_open(self):
        return self.state == "open"

    @property
    def requirement(self):
        if self.type != "initial":
            parts = self.title.split(" ")
            if len(parts) >= 2:
                return parts[1].lower()
        return None
