from __future__ import unicode_literals

from packaging.version import parse as parse_version
from packaging.specifiers import SpecifierSet
import requests

from safety import safety
from safety.errors import InvalidKeyError
from collections import OrderedDict

from .updates import InitialUpdate, SequentialUpdate, ScheduledUpdate
from .pullrequest import PullRequest
import logging
from .package import Package, fetch_package
from pyup import settings
from datetime import datetime
from dparse import parse, parser, updater, filetypes
from dparse.dependencies import Dependency
from dparse.parser import setuptools_parse_requirements_backport as parse_requirements

logger = logging.getLogger(__name__)


class RequirementsBundle(list):

    def __init__(self, *args, **kwargs):
        super(RequirementsBundle, self).__init__(*args, **kwargs)
        self.pull_requests = []

    def resolve_pipfiles(self):
        for req_file in self:
            if req_file.is_pipfile:
                corresponding_path = req_file.get_pipfile_lock_path()
                for _req_file in self:
                    if _req_file.path == corresponding_path:
                        req_file.corresponding_pipfile = _req_file

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
        self.is_pipfile = False
        self.is_pipfile_lock = False
        self.is_setup_cfg = False
        self.corresponding_pipfile = None

    def get_pipfile_lock_path(self):
        return "{}.lock".format(self.path)

    def get_pipfile_path(self):
        return self.path.replace(".lock", "")

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

    def _parse_pipfile(self):
        self.parse_dependencies(filetypes.pipfile)
        self.is_pipfile = True

    def _parse_pipfile_lock(self):
        self.parse_dependencies(filetypes.pipfile_lock)
        self.is_pipfile_lock = True

    def _parse_setup_cfg(self):
        self.parse_dependencies(filetypes.setup_cfg)
        self.is_setup_cfg = True

    def _parse(self):
        self._requirements, self._other_files = [], []
        if self.path.endswith('.yml') or self.path.endswith(".yaml"):
            self._parse_conda_yml()
        elif self.path.endswith('.ini'):
            self._parse_tox_ini()
        elif self.path.endswith("Pipfile"):
            self._parse_pipfile()
        elif self.path.endswith("Pipfile.lock"):
            self._parse_pipfile_lock()
        elif self.path.endswith('setup.cfg'):
            self._parse_setup_cfg()
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
            marker=(
                ("pyup: ignore file", "pyup:ignore file"),  # file marker
                ("pyup: ignore", "pyup:ignore"),  # line marker
            )
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
            req.index_server = dep.index_server
            if self.is_pipfile:
                req.pipfile = self.path
            if req.package:
                req.hashes = dep.hashes
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
        self.pipfile = None

        self.hashCmp = (
            self.key,
            self.specs,
            frozenset(self.extras),
        )

        self._is_insecure = None
        self._changelog = None

        if len(self.specs._specs) == 1 and next(iter(self.specs._specs))._spec[0] == "~=":
            # convert compatible releases to something more easily consumed,
            # e.g. '~=1.2.3' is equivalent to '>=1.2.3,<1.3.0', while '~=1.2'
            # is equivalent to '>=1.2,<2.0'
            min_version = next(iter(self.specs._specs))._spec[1]
            max_version = list(parse_version(min_version).release)
            max_version[-1] = 0
            max_version[-2] = max_version[-2] + 1
            max_version = '.'.join(str(x) for x in max_version)

            self.specs = SpecifierSet('>=%s,<%s' % (min_version, max_version))

    def __eq__(self, other):
        return (
            isinstance(other, Requirement) and
            self.hashCmp == other.hashCmp
        )

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return "Requirement.parse({line}, {lineno})".format(line=self.line, lineno=self.lineno)

    def __repr__(self):
        return self.__str__()

    @property
    def is_pinned(self):
        if len(self.specs._specs) == 1 and next(iter(self.specs._specs))._spec[0] == "==":
            return True
        return False

    @property
    def is_open_ranged(self):
        if len(self.specs._specs) == 1 and next(iter(self.specs._specs))._spec[0] == ">=":
            return True
        return False

    @property
    def is_ranged(self):
        return len(self.specs._specs) >= 1 and not self.is_pinned

    @property
    def is_loose(self):
        return len(self.specs._specs) == 0

    @staticmethod
    def convert_semver(version):
        semver = {'major': 0, "minor": 0, "patch": 0}
        version = version.split(".")
        # don't be overly clever here. repitition makes it more readable and works exactly how
        # it is supposed to
        try:
            semver['major'] = int(version[0])
            semver['minor'] = int(version[1])
            semver['patch'] = int(version[2])
        except (IndexError, ValueError):
            pass
        return semver

    @property
    def can_update_semver(self):
        # return early if there's no update filter set
        if "pyup: update" not in self.line:
            return True
        update = self.line.split("pyup: update")[1].strip().split("#")[0]
        current_version = Requirement.convert_semver(next(iter(self.specs._specs))._spec[1])
        next_version = Requirement.convert_semver(self.latest_version)
        if update == "major":
            if current_version['major'] < next_version['major']:
                return True
        elif update == 'minor':
            if current_version['major'] < next_version['major'] \
                    or current_version['minor'] < next_version['minor']:
                return True
        return False

    @property
    def filter(self):
        rqfilter = False
        if "rq.filter:" in self.line:
            rqfilter = self.line.split("rq.filter:")[1].strip().split("#")[0]
        elif "pyup:" in self.line:
            if "pyup: update" not in self.line:
                rqfilter = self.line.split("pyup:")[1].strip().split("#")[0]
                # unset the filter once the date set in 'until' is reached
                if "until" in rqfilter:
                    rqfilter, until = [l.strip() for l in rqfilter.split("until")]
                    try:
                        until = datetime.strptime(until, "%Y-%m-%d")
                        if until < datetime.now():
                            rqfilter = False
                    except ValueError:
                        # wrong date formatting
                        pass
        if rqfilter:
            try:
                rqfilter, = parse_requirements("filter " + rqfilter)
                if len(rqfilter.specifier._specs) > 0:
                    return rqfilter.specifier
            except ValueError:
                pass
        return False

    @property
    def version(self):
        if self.is_pinned:
            return next(iter(self.specs._specs))._spec[1]

        specs = self.specs
        if self.filter:
            specs = SpecifierSet(
                ",".join(["".join(s._spec) for s in list(specs._specs) + list(self.filter._specs)])
            )
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
        return self.is_pinned and parse_version(
            next(iter(self.specs._specs))._spec[1]).is_prerelease

    @staticmethod
    def get_latest_version_within_specs(specs, versions, prereleases=None):
        # build up a spec set and convert compatible specs to pinned ones
        spec_set = SpecifierSet(
            ",".join(["".join(s._spec).replace("~=", "==") for s in specs])
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
        if self.is_pinned or self.is_ranged:
            return self.can_update_semver and self.is_outdated
        return self.can_update_semver

    @property
    def is_insecure(self):
        if self._is_insecure is None:
            if not settings.api_key:
                self._is_insecure = False
            else:
                self._is_insecure = len(safety.check(
                    packages=(self,),
                    cached=True,
                    key=settings.api_key,
                    db_mirror="",
                    ignore_ids=()
                )) != 0

        return self._is_insecure

    @property
    def changelog(self):
        if self._changelog is None:
            self._changelog = OrderedDict()
            if settings.api_key:
                r = requests.get(
                    "https://pyup.io/api/v1/changelogs/{}/".format(self.key),
                    headers={"X-Api-Key": settings.api_key}
                )
                if r.status_code == 403:
                    raise InvalidKeyError
                if r.status_code == 200:
                    data = r.json()
                    if data:
                        # sort the changelog by release
                        sorted_log = sorted(
                            data.items(), key=lambda v: parse_version(v[0]), reverse=True)
                        # go over each release and add it to the log if it's within the "upgrade
                        # range" e.g. update from 1.2 to 1.3 includes a changelog for 1.2.1 but
                        # not for 0.4.
                        for version, log in sorted_log:
                            parsed_version = parse_version(version)
                            if self.is_pinned and parsed_version > parse_version(
                                self.version) and parsed_version <= parse_version(
                                    self.latest_version_within_specs):
                                self._changelog[version] = log
                            elif not self.is_pinned and parsed_version <= parse_version(
                                    self.latest_version_within_specs):
                                self._changelog[version] = log
        return self._changelog

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
        r = requests.get('https://pypi.org/pypi/{name}/{version}/json'.format(
            name=self.key,
            version=version
        ))
        hashes = []
        data = r.json()
        for item in data.get("releases", {}).get(version, []):
            sha256 = item.get("digests", {}).get("sha256", False)
            if sha256:
                hashes.append({"hash": sha256})
        return data["hashes"]

    def update_content(self, content, update_hashes=True):
        if self.file_type == filetypes.tox_ini:
            updater_class = updater.ToxINIUpdater
        elif self.file_type == filetypes.conda_yml:
            updater_class = updater.CondaYMLUpdater
        elif self.file_type == filetypes.requirements_txt:
            updater_class = updater.RequirementsTXTUpdater
        elif self.file_type == filetypes.pipfile:
            updater_class = updater.PipfileUpdater
        elif self.file_type == filetypes.pipfile_lock:
            updater_class = updater.PipfileLockUpdater
        elif self.file_type == filetypes.setup_cfg:
            updater_class = updater.SetupCFGUpdater
        else:
            raise NotImplementedError

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
            for item in sorted(self.get_hashes(self.latest_version_within_specs), key=lambda x: x["hash"]):
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
            name=parsed.name,
            specs=parsed.specifier,
            line=s,
            lineno=lineno,
            extras=parsed.extras,
            file_type=file_type
        )

    def get_package_class(self):  # pragma: no cover
        return Package
