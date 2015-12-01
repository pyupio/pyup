# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from datetime import datetime


class PullRequest(object):

    def __init__(self, state, title, url, created_at):
        self.state = state
        self.title = title
        self.url = url
        self.created_at = created_at

    def __eq__(self, other):
        return \
            self.state == other.state and \
            self.title == other.title and \
            self.url == other.url and \
            self.created_at == other.created_at


    @property
    def type(self):
        if self.title.startswith("Update"):
            return "update"
        elif self.title.startswith("Security"):
            return "security"
        elif self.title.startswith("Pin"):
            return "pin"
        return "unknown"

    @property
    def is_open(self):
        return self.state == "open"
