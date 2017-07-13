from __future__ import unicode_literals
from pkg_resources import parse_requirements
from pkg_resources import parse_version
from pkg_resources._vendor.packaging.specifiers import SpecifierSet
import hashin
from .updates import InitialUpdate, SequentialUpdate, ScheduledUpdate
from .pullrequest import PullRequest
import logging
from .package import Package, fetch_package

from dparse import parse, parser, updater, filetypes
from dparse.dependencies import Dependency

PYTHON_VERSIONS = [
    "2.7", "3.0", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6"
]
logger = logging.getLogger(__name__)


class RequirementsBundle(list):

    def __init__(self, *args, **kwargs):
        super(RequirementsBundle, self).__init__(*args, **kwargs)
        self.pull_requests = []

    def has_file_in_path(self, path):
        return path in [req_file.path for req_file in self]

    def get_updates(self, initial, scheduled, config):
        return self.get_update_class(
            initial=initial,
            scheduled=scheduled,
            config=config
        )(self, config).get_updates()

    def get_update_class(self, initial, scheduled, config):
        if initial:
            return self.get_initial_update_class()
        elif scheduled and config.is_valid_schedule():
            return self.get_scheduled_update_class()
        return self.get_sequential_update_class()

    @property
    def requirements(self):
        for req_file in self:
            for req in req_file.requirements:
                yield req

    def get_pull_request_class(self):  # pragma: no cover
        return PullRequest

    def get_requirement_class(self):  # pragma: no cover
        return Requirement

    def get_requirement_file_class(self):  # pragma: no cover
        return RequirementFile

    def get_initial_update_class(self):  # pragma: no cover
        return InitialUpdate

    def get_scheduled_update_class(self):  # pragma: no cover
        return ScheduledUpdate

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
        return "RequirementFile(path='{path}', sha='{sha}', content='{content}')".format(
            path=self.path,
            content=self.content[:30] + "[truncated]" if len(self.content) > 30 else self.content,
            sha=self.sha
        )

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

    @staticmethod
    def parse_index_server(line):
        return parser.Parser.parse_index_server(line)

    def _hash_parser(self, line):
        return parser.Parser.parse_hashes(line)

    def _parse_requirements_txt(self):
        self.parse_dependencies(filetypes.requirements_txt)

    def _parse_conda_yml(self):
        self.parse_dependencies(filetypes.conda_yml)

    def _parse_tox_ini(self):
        self.parse_dependencies(filetypes.tox_ini)

    def _parse(self):
        self._requirements, self._other_files = [], []
        if self.path.endswith('.yml'):
            self._parse_conda_yml()
        elif self.path.endswith('.ini'):
            self._parse_tox_ini()
        else:
            self._parse_requirements_txt()
        self._is_valid = len(self._requirements) > 0 or len(self._other_files) > 0

    def parse_dependencies(self, file_type):

        klass = self.get_requirement_class()
        result = parse(
            self.content,
            path=self.path,
            sha=self.sha,
            file_type=file_type,
            marker=(("pyup: ignore file",), ("pyup: ignore",))
        )
        for dep in result.dependencies:
            req = klass(
                name=dep.name,
                specs=dep.specs,
                line=dep.line,
                lineno=dep.line_numbers[0] if dep.line_numbers else 0,
                extras=dep.extras,
                file_type=file_type,
            )
            if req.package:
                req.hashes = dep.hashes
                req.index_server = dep.index_server
                self._requirements.append(req)
        self._other_files = result.resolved_files

    def iter_lines(self, lineno=0):
        for line in self.content.splitlines()[lineno:]:
            yield line

    @classmethod
    def resolve_file(cls, file_path, line):
        return parser.Parser.resolve_file(file_path, line)

    def get_requirement_class(self):  # pragma: no cover
        return Requirement


class Requirement(object):
    def __init__(self, name, specs, line, lineno, extras, file_type):
        self.name = name
        self.key = name.lower()
        self.specs = specs
        self.line = line
        self.lineno = lineno
        self.index_server = None
        self.extras = extras
        self.pull_request = None
        self.hashes = []
        self._fetched_package = False
        self._package = None
        self.file_type = file_type

        self.hashCmp = (
            self.key,
            self.specs,
            frozenset(self.extras),
        )

    def __eq__(self, other):
        return (
            isinstance(other, Requirement) and
            self.hashCmp == other.hashCmp
        )

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return "Requirement.parse({line}, {lineno})".format(line=self.line, lineno=self.lineno)

    @property
    def is_pinned(self):
        if len(self.specs) == 1 and self.specs[0][0] == "==":
            return True
        return False

    @property
    def is_compatible(self):
        if len(self.specs) == 1 and self.specs[0][0] == "~=":
            return True
        return False

    @property
    def is_open_ranged(self):
        if len(self.specs) == 1 and self.specs[0][0] == ">=":
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
        rqfilter = False
        if "rq.filter:" in self.line:
            rqfilter = self.line.split("rq.filter:")[1].strip().split("#")[0]
        elif "pyup:" in self.line:
            rqfilter = self.line.split("pyup:")[1].strip().split("#")[0]
        if rqfilter:
            try:
                rqfilter, = parse_requirements("filter " + rqfilter)
                if len(rqfilter.specs) > 0:
                    return rqfilter.specs
            except ValueError:
                pass
        return False

    @property
    def version(self):
        if self.is_pinned or self.is_compatible:
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
        # build up a spec set and convert compatible specs to pinned ones
        spec_set = SpecifierSet(
            ",".join(["".join([x.replace("~=", "=="), y]) for x, y in specs])
        )
        candidates = []
        for version in versions:
            if spec_set.contains(version, prereleases=prereleases):
                candidates.append(version)
        candidates = sorted(candidates, key=lambda v: parse_version(v), reverse=True)
        if len(candidates) > 0:
            return candidates[0]
        return None

    @property
    def package(self):
        if not self._fetched_package:
            self._package = fetch_package(self.name, self.index_server)
            self._fetched_package = True
        return self._package

    @property
    def needs_update(self):
        if self.is_pinned or self.is_ranged or self.is_compatible:
            return self.is_outdated
        return True

    @property
    def is_insecure(self):
        # security is not our concern for the moment. However, it'd be nice if we had a central
        # place where we can query for known security vulnerabilites on python packages.
        # There's an open issue here:
        # https://github.com/pypa/warehouse/issues/798
        raise NotImplementedError

    @property
    def is_outdated(self):
        if self.version and self.latest_version_within_specs:
            return parse_version(self.version) < parse_version(self.latest_version_within_specs)
        return False

    @property
    def full_name(self):
        if self.extras:
            return "{}[{}]".format(self.name, ",".join(self.extras))
        return self.name

    def get_hashes(self, version):
        data = hashin.get_package_hashes(
            self.name,
            version=version,
            algorithm="sha256",
            python_versions=PYTHON_VERSIONS,
            verbose=True
        )
        return data["hashes"]

    def update_content(self, content, update_hashes=True):
        if self.file_type == filetypes.tox_ini:
            updater_class = updater.ToxINIUpdater
        elif self.file_type == filetypes.conda_yml:
            updater_class = updater.CondaYMLUpdater
        else:
            updater_class = updater.RequirementsTXTUpdater
        dep = Dependency(
            name=self.name,
            specs=self.specs,
            line=self.line,
            line_numbers=[self.lineno, ] if self.lineno != 0 else None,
            dependency_type=self.file_type,
            hashes=self.hashes,
            extras=self.extras
        )
        hashes = []
        if self.hashes and update_hashes:
            for item in self.get_hashes(self.latest_version_within_specs):
                hashes.append({"method": "sha256", "hash": item["hash"]})

        return updater_class.update(
            content=content,
            dependency=dep,
            version=self.latest_version_within_specs,
            hashes=hashes
        )

    @classmethod
    def parse(cls, s, lineno, file_type=filetypes.requirements_txt):
        # setuptools requires a space before the comment. If this isn't the case, add it.
        if "\t#" in s:
            parsed, = parse_requirements(s.replace("\t#", "\t #"))
        else:
            parsed, = parse_requirements(s)
        return cls(
            name=parsed.project_name,
            specs=parsed.specs,
            line=s,
            lineno=lineno,
            extras=parsed.extras,
            file_type=file_type
        )

    def get_package_class(self):  # pragma: no cover
        return Package
