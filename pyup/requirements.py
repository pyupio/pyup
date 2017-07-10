from __future__ import unicode_literals
from pkg_resources import parse_requirements
from pkg_resources import parse_version
from pkg_resources._vendor.packaging.specifiers import SpecifierSet
import hashin
from .updates import InitialUpdate, SequentialUpdate, ScheduledUpdate
from .pullrequest import PullRequest
import logging
from .package import Package, fetch_package
import re
import yaml
import StringIO
from ConfigParser import SafeConfigParser, NoOptionError

# see https://gist.github.com/dperini/729294
URL_REGEX = re.compile(
    # protocol identifier
    u"(?:(?:https?|ftp)://)"
    # user:pass authentication
    u"(?:\S+(?::\S*)?@)?"
    u"(?:"
    # IP address exclusion
    # private & local networks
    u"(?!(?:10|127)(?:\.\d{1,3}){3})"
    u"(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})"
    u"(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})"
    # IP address dotted notation octets
    # excludes loopback network 0.0.0.0
    # excludes reserved space >= 224.0.0.0
    # excludes network & broadcast addresses
    # (first & last IP address of each class)
    u"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
    u"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}"
    u"(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))"
    u"|"
    # host name
    u"(?:(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)"
    # domain name
    u"(?:\.(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)*"
    # TLD identifier
    u"(?:\.(?:[a-z\u00a1-\uffff]{2,}))"
    u")"
    # port number
    u"(?::\d{2,5})?"
    # resource path
    u"(?:/\S*)?",
    re.UNICODE)

PYTHON_VERSIONS = [
    "2.7", "3.0", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6"
]
logger = logging.getLogger(__name__)


class FILE_TYPES(object):

    REQUIREMENTS_TXT = "REQUIREMENTS_TXT"
    CONDA_FILE = "CONDA_FILE"
    TOX_INI = "TOX_INI"


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
        matches = URL_REGEX.findall(line)
        if matches:
            url = matches[0]
            return url if url.endswith("/") else url + "/"
        return None

    def _hash_parser(self, line):
        """

        :param line:
        :return:
        """
        regex = r"--hash[=| ][\w]+:[\w]+"
        hashes = []
        for match in re.finditer(regex, line):
            hashes.append(line[match.start():match.end()])
        return re.sub(regex, "", line).strip(), hashes

    def _parse_requirements_txt(self):
        index_server = None
        for num, line in enumerate(self.iter_lines()):
            line = line.rstrip()
            if not line:
                continue
            elif "pyup: ignore file" in line and num in [0, 1]:
                # don't process this file, filter rule match to completely ignore it
                self._is_valid = False
                return
            if line.startswith('#'):
                # comments are lines that start with # only
                continue
            if line.startswith('-i') or \
                line.startswith('--index-url') or \
                line.startswith('--extra-index-url'):
                # this file is using a private index server, try to parse it
                index_server = self.parse_index_server(line)
                continue
            elif line.startswith('-r') or line.startswith('--requirement'):
                self._other_files.append(self.resolve_file(self.path, line))
            elif line.startswith('-f') or line.startswith('--find-links') or \
                line.startswith('--no-index') or line.startswith('--allow-external') or \
                line.startswith('--allow-unverified') or line.startswith('-Z') or \
                line.startswith('--always-unzip'):
                continue
            else:
                try:
                    if "pyup: ignore" in line:
                        # filter rule match to completely ignore this requirement
                        continue
                    parseable_line = line

                    # multiline requirements are not parseable
                    if "\\" in line:
                        parseable_line = line.replace("\\", "")
                        for next_line in self.iter_lines(num + 1):
                            parseable_line += next_line.strip().replace("\\", "")
                            line += "\n" + next_line
                            if "\\" in next_line:
                                continue
                            break

                    hashes = []
                    if "--hash" in parseable_line:
                        parseable_line, hashes = self._hash_parser(parseable_line)

                    klass = self.get_requirement_class()
                    req = klass.parse(parseable_line, num + 1)
                    req.hashes = hashes
                    req.index_server = index_server
                    # replace the requirements line with the 'real' line
                    req.line = line
                    if req.package is not None:
                        self._requirements.append(req)
                except ValueError:
                    continue

    def _parse_conda_yml(self):
        try:
            data = yaml.safe_load(self.content)
            if 'dependencies' in data and isinstance(data['dependencies'], list):
                for dep in data['dependencies']:
                    if isinstance(dep, dict) and 'pip' in dep:
                        for n, item in enumerate(dep['pip']):
                            klass = self.get_requirement_class()
                            req = klass.parse(item, n, file_type=FILE_TYPES.CONDA_FILE)
                            if req.package is not None:
                                self._requirements.append(req)
        except yaml.YAMLError:
            pass

    def _parse_tox_ini(self):
        klass = self.get_requirement_class()
        parser = SafeConfigParser()
        parser.readfp(StringIO.StringIO(self.content))
        for section in parser.sections():
            try:
                content = parser.get(section=section, option="deps")
                for n, line in enumerate(content.splitlines()):
                    if line:
                        req = klass.parse(line, n, file_type=FILE_TYPES.TOX_INI)
                        print(req)
                        if req.package is not None:
                            self._requirements.append(req)
            except NoOptionError:
                pass

    def _parse(self):
        self._requirements, self._other_files = [], []
        if self.path.endswith('.yml'):
            self._parse_conda_yml()
        elif self.path.endswith('.ini'):
            self._parse_tox_ini()
        else:
            self._parse_requirements_txt()
        self._is_valid = len(self._requirements) > 0 or len(self._other_files) > 0

    def iter_lines(self, lineno=0):
        for line in self.content.splitlines()[lineno:]:
            yield line

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


class Requirement(object):
    def __init__(self, name, specs, hashCmp, line, lineno, extras, file_type):
        self.name = name
        self.key = name.lower()
        self.specs = specs
        self.hashCmp = hashCmp
        self.line = line
        self.lineno = lineno
        self.index_server = None
        self.extras = extras
        self.pull_request = None
        self.hashes = []
        self._fetched_package = False
        self._package = None
        self.file_type = file_type

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
        """
        Updates the requirement to the latest version for the given content and adds hashes
        if neccessary.
        :param content: str, content
        :return: str, updated content
        """
        new_line = "{}=={}".format(self.full_name, self.latest_version_within_specs)
        appendix = ''
        # leave environment markers intact
        if ";" in self.line:
            # condense multiline, split out the env marker, strip comments and --hashes
            new_line += ";" + self.line.splitlines()[0].split(";", 1)[1] \
                .split("#")[0].split("--hash")[0].rstrip()
        # add the comment
        if "#" in self.line:
            # split the line into parts: requirement and comment
            parts = self.line.split("#")
            requirement, comment = parts[0], "#".join(parts[1:])
            # find all whitespaces between the requirement and the comment
            whitespaces = (hex(ord('\t')), hex(ord(' ')))
            trailing_whitespace = ''
            for c in requirement[::-1]:
                if hex(ord(c)) in whitespaces:
                    trailing_whitespace += c
                else:
                    break
            appendix += trailing_whitespace + "#" + comment
        # if this is a hashed requirement, add a multiline break before the comment
        if self.hashes and not new_line.endswith("\\"):
            new_line += " \\"
        # if this is a hashed requirement, add the hashes
        if update_hashes and self.hashes:
            new_hashes = self.get_hashes(self.latest_version_within_specs)
            for n, new_hash in enumerate(new_hashes):
                new_line += "\n    --hash=sha256:{}".format(new_hash["hash"])
                # append a new multiline break if this is not the last line
                if len(new_hashes) > n + 1:
                    new_line += " \\"
        new_line += appendix
        if self.file_type == FILE_TYPES.REQUIREMENTS_TXT:
            regex = r"^{}(?=\s*\r?\n?$)".format(re.escape(self.line))
        elif self.file_type in [FILE_TYPES.CONDA_FILE, FILE_TYPES.TOX_INI]:
            regex = r"{}(?=\s*\r?\n?$)".format(re.escape(self.line))
        return re.sub(regex, new_line, content, flags=re.MULTILINE)

    @classmethod
    def parse(cls, s, lineno, file_type=FILE_TYPES.REQUIREMENTS_TXT):
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
            hashCmp=parsed.hashCmp,
            extras=parsed.extras,
            file_type=file_type
        )

    def get_package_class(self):  # pragma: no cover
        return Package
