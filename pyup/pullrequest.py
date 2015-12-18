# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals


class PullRequest(object):

    def __init__(self, state, title, url, created_at):
        self.state = state
        self.title = title
        self.url = url
        self.created_at = created_at

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
        return "unknown"

    @property
    def is_open(self):
        return self.state == "open"
