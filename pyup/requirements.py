from __future__ import unicode_literals
import re
from pkg_resources import Requirement as RequirementBase, parse_requirements
from pkg_resources import parse_version
from pkg_resources import RequirementParseError
from pkg_resources._vendor.packaging.specifiers import SpecifierSet
from .updates import InitialUpdate, SequentialUpdate
from .pullrequest import PullRequest
import logging
from .package import Package, fetch_package

logger = logging.getLogger(__name__)


class RequirementsBundle(list):
    def has_file_in_path(self, path):
        return path in [req_file.path for req_file in self]

    def get_updates(self, inital):
        return self.get_initial_update_class()(self).get_updates() if inital \
            else self.get_sequential_update_class()(self).get_updates()

    @property
    def requirements(self):
        for req_file in self:
            for req in req_file.requirements:
                yield req

    def __str__(self):
        return "Requirements: {}".format(",".join([r.path for r in self]))

    def pull_requests(self):
        returned = []
        for pr in sorted([r.pull_request for r in self.requirements if r.pull_request is not None],
                         key=lambda r: r.created_at):
            if pr not in returned:
                returned.append(pr)
                yield pr

    def get_pull_request_class(self):  # pragma: no cover
        return PullRequest

    def get_requirement_class(self):  # pragma: no cover
        return Requirement

    def get_requirement_file_class(self):  # pragma: no cover
        return RequirementFile

    def get_initial_update_class(self):  # pragma: no cover
        return InitialUpdate

    def get_sequential_update_class(self):  # pragma: no cover
        return SequentialUpdate


class RequirementFile(object):
    def __init__(self, path, content, sha=None):
        self.path = path
        self.content = content
        self.sha = sha
        self._requirements = None
        self._other_files = None
        self._is_valid = None

    def __str__(self):
        return "RequirementFile: {}".format(self.path)

    @property
    def is_valid(self):
        if self._is_valid is None:
            self._parse()
        return self._is_valid

    @property
    def requirements(self):
        if not self._requirements:
            self._parse()
        return self._requirements

    @property
    def other_files(self):
        if not self._other_files:
            self._parse()
        return self._other_files

    def _parse(self):
        self._requirements, self._other_files = [], []
        for num, line in enumerate(self.content.splitlines()):
            line = line.strip()
            if line == '':
                continue
            elif not line or line.startswith('#'):
                # comments are lines that start with # only
                continue
            elif line.startswith('-r') or line.startswith('--requirement'):
                self._other_files.append(self.resolve_file(self.path, line))
            elif line.startswith('-f') or line.startswith('--find-links') or \
                    line.startswith('-i') or line.startswith('--index-url') or \
                    line.startswith('--extra-index-url') or \
                    line.startswith('--no-index') or line.startswith('--allow-external') or \
                    line.startswith('--allow-unverified') or \
                    line.startswith('-Z') or line.startswith('--always-unzip'):
                continue
            else:
                try:
                    klass = self.get_requirement_class()
                    req = klass.parse(line, num + 1)
                    if req.package is not None:
                        self._requirements.append(req)
                except RequirementParseError:
                    # print("can't parse", line)
                    continue
        self._is_valid = len(self._requirements) > 0 or len(self._other_files) > 0

    @classmethod
    def resolve_file(cls, file_path, line):
        line = line.replace("-r ", "").replace("--requirement ", "")
        parts = file_path.split("/")
        if " #" in line:
            line = line.split("#")[0].strip()
        if len(parts) == 1:
            return line
        return "/".join(parts[:-1]) + "/" + line

    def get_requirement_class(self):   # pragma: no cover
        return Requirement


# inherit from object to make this a new style class for older versions of pip
class Requirement(RequirementBase, object):
    def __init__(self, project_name, specs, extras, line, lineno, pull_request=None):
        super(Requirement, self).__init__(project_name, specs, extras)
        self.line = line
        self.lineno = lineno
        self.pull_request = pull_request
        self._fetched_package = False
        self._package = None

    @property
    def is_pinned(self):
        if len(self.specs) == 1 and self.specs[0][0] == "==":
            return True
        return False

    @property
    def is_ranged(self):
        return len(self.specs) >= 1 and not self.is_pinned

    @property
    def is_loose(self):
        return len(self.specs) == 0

    @property
    def filter(self):
        if "rq.filter:" in self.line:
            try:
                rqfilter = self.line.split("rq.filter:")[1]
                rqfilter, = parse_requirements("filter " + rqfilter)
                if len(rqfilter.specs) > 0:
                    return rqfilter.specs
            except RequirementParseError:
                pass
        return False

    @property
    def version(self):
        if self.is_pinned:
            return self.specs[0][1]

        specs = self.specs
        if self.filter:
            specs += self.filter
        return self.get_latest_version_within_specs(
            specs,
            versions=self.package.versions,
            prereleases=self.prereleases
        )

    @property
    def latest_version_within_specs(self):
        if self.filter:
            return self.get_latest_version_within_specs(
                self.filter,
                versions=self.package.versions,
                prereleases=self.prereleases
            )
        return self.latest_version

    @property
    def latest_version(self):
        return self.package.latest_version(self.prereleases)

    @property
    def prereleases(self):
        return self.is_pinned and parse_version(self.specs[0][1]).is_prerelease

    @staticmethod
    def get_latest_version_within_specs(specs, versions, prereleases=None):
        spec_set = SpecifierSet(
            ",".join(["".join([x, y]) for x, y in specs])
        )
        candidates = []
        # print("specs are", spec_set)
        for version in versions:
            if spec_set.contains(version, prereleases=prereleases):
                candidates.append(version)
                # else:
                # print(spec_set, "does not contain", version)
        candidates = sorted(candidates, key=lambda v: parse_version(v), reverse=True)
        if len(candidates) > 0:
            # print("candidates are", candidates)
            return candidates[0]
        return None

    @property
    def name(self):
        return self.project_name

    @property
    def package(self):
        if not self._fetched_package:
            self._package = fetch_package(self.name)
        return self._package

    @property
    def needs_update(self):
        if self.is_pinned or self.is_ranged:
            return self.is_insecure or self.is_outdated
        return True

    @property
    def is_insecure(self):
        # todo: implement
        return False

    @property
    def is_outdated(self):
        return parse_version(self.version) < parse_version(self.latest_version_within_specs)

    def update_content(self, content):
        new_line = "{}=={}".format(self.project_name, self.latest_version)
        if "#" in self.line:
            new_line += " #" + "#".join(self.line.split("#")[1:])
        regex = r"^{}".format(self.line)
        return re.sub(regex, new_line, content, flags=re.MULTILINE)

    @classmethod
    def parse(cls, s, lineno):
        parsed, = parse_requirements(s)
        return cls(
            project_name=parsed.project_name,
            specs=parsed.specs,
            extras=parsed.extras,
            line=s,
            lineno=lineno,
        )

    def get_package_class(self):  # pragma: no cover
        return Package
