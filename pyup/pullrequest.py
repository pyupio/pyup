# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals


class PullRequest(object):

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
            return "update"
        elif self.title.startswith("Security"):
            return "security"
        elif self.title.startswith("Pin"):
            return "pin"
        elif self.title.startswith("Initial"):
            return "initial"
        elif self.title.startswith("Compile"):
            return "compile"
        return "unknown"

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
