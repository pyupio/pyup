# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
try:  # pragma: no cover
    basestring
except NameError:  # pragma: no cover
    basestring = str


class Config(object):

    def __init__(self):
        self.close_prs = True
        self.branch = "master"
        self.pin = True
        self.search = True
        self.requirements = []

    def update(self, d):
        for key, value in d.items():
            if hasattr(self, key):
                if key == "requirements":
                    items, value = value, []
                    for item in items:
                        if isinstance(item, basestring):
                            req = RequirementConfig(path=item)
                        elif isinstance(item, dict):
                            path, item = item.popitem()
                            req = RequirementConfig(
                                path=path,
                                pin=item.get("pin", None),
                                compile=item.get("compile", False))
                        value.append(req)
                        # add constraint requirement files to config
                        if req.compile:
                            for spec in req.compile.specs:
                                value.append(RequirementConfig(path=spec, pin=False))
                setattr(self, key, value)

    def pin_file(self, path):
        for req_file in self.requirements:
            if path == req_file.path:
                return req_file.pin
        return self.pin

    def __repr__(self):
        return str(self.__dict__)


class RequirementConfig(object):

    def __init__(self, path, pin=None, compile=False):
        self.path = path
        self.pin = pin
        self.compile = CompileConfig(specs=compile.get("specs", [])) if compile else False

        # set pin default
        if self.pin is None:
            self.pin = True

    def __repr__(self):
        return str(self.__dict__)


class CompileConfig(object):

    def __init__(self, specs=list()):
        self.specs = specs

    def __repr__(self):
        return str(self.__dict__)
