# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from django.test import TestCase
from pyup.requirements import Requirement
from pyupio.packages.models import Package
from unittest.mock import patch, MagicMock, NonCallableMagicMock, PropertyMock
from pyup.requirements import RequirementFile, RequirementsBundle
from pyup.pullrequest import PullRequest
import os
from pyupio.packages.tests.test_models import package_factory
from datetime import datetime


class RequirementUpdateContent(TestCase):
    def test_update_content_simple_pinned(self):
        with patch('pyupio.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "Django==1.4.1"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "Django==1.4.2")

        with patch('pyupio.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "django==1.4.1"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "django==1.4.2")

    def test_update_content_simple_unpinned(self):
        with patch('pyupio.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "django"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "django==1.4.2")

        with patch('pyupio.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "Django"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "Django==1.4.2")

    def test_update_content_simple_unpinned_with_comment(self):
        with patch('pyupio.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "django # newest django release"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "django==1.4.2 # newest django release")

        with patch('pyupio.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "Django #django"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "Django==1.4.2 #django")

        with patch('pyupio.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="1.4.2"):
            content = "Django #django #yay this has really cool comments ######"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content),
                             "Django==1.4.2 #django #yay this has really cool comments ######")

    def test_update_content_with_package_in_comments(self):
        with patch('pyupio.requirements.Requirement.latest_version', new_callable=PropertyMock, return_value="2.58.1.44"):
            content = 'raven==5.8.1\n' \
                      '{%- endif %}\n\n' \
                      '{% if cookiecutter.use_newrelic == "y" -%}\n' \
                      '# Newrelic agent for performance monitoring\n' \
                      '# -----------------------------------------\n' \
                      'newrelic\n' \
                      '{%- endif %}\n\n'
            req = Requirement.parse("newrelic", 0)
            updated_content = 'raven==5.8.1\n' \
                              '{%- endif %}\n\n' \
                              '{% if cookiecutter.use_newrelic == "y" -%}\n' \
                              '# Newrelic agent for performance monitoring\n' \
                              '# -----------------------------------------\n' \
                              'newrelic==2.58.1.44\n' \
                              '{%- endif %}\n\n'
            self.assertEqual(req.update_content(content), updated_content)


class RequirementTestCase(TestCase):
    def test_is_pinned(self):
        req = Requirement.parse("Django", 0)
        self.assertEqual(req.is_pinned, False)

        req = Requirement.parse("Django==1.4,>1.5", 0)
        self.assertEqual(req.is_pinned, False)

        req = Requirement.parse("Django===1.4", 0)
        self.assertEqual(req.is_pinned, False)

        req = Requirement.parse("Django<=1.4,>=1.33", 0)
        self.assertEqual(req.is_pinned, False)

        req = Requirement.parse("Django==1.4", 0)
        self.assertEqual(req.is_pinned, True)

    def test_is_loose(self):
        req = Requirement.parse("Django", 0)
        self.assertEqual(req.is_loose, True)

        req = Requirement.parse("Django==1.4,>1.5", 0)
        self.assertEqual(req.is_loose, False)

        req = Requirement.parse("Django===1.4", 0)
        self.assertEqual(req.is_loose, False)

        req = Requirement.parse("Django<=1.4,>=1.33", 0)
        self.assertEqual(req.is_loose, False)

        req = Requirement.parse("Django==1.4", 0)
        self.assertEqual(req.is_loose, False)

    def test_filter(self):
        req = Requirement.parse("Django", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("Django #rq.filter:", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("Django #rq.filter: >=1.4,<1.5", 0)
        self.assertEqual(req.filter, [('>=', '1.4'), ('<', '1.5')])

        req = Requirement.parse("Django #rq.filter:!=1.2", 0)
        self.assertEqual(req.filter, [('!=', '1.2')])

        req = Requirement.parse("Django #rq.filter:foo", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("bliss #rq.filter:", 0)
        self.assertEqual(req.filter, False)

    def test_get_latest_version_within_specs(self):
        latest = Requirement.get_latest_version_within_specs(
            (("==", "1.2"), ("!=", "1.2")),
            ["1.2", "1.3", "1.4", "1.5"]
        )

        self.assertEqual(latest, None)

        latest = Requirement.get_latest_version_within_specs(
            (("==", "1.2.1"),),
            ["1.2.0", "1.2.1", "1.2.2", "1.3"]
        )

        self.assertEqual(latest, "1.2.1")

    def test_latest_version_within_specs(self):
        pkg = package_factory("bliss", versions=["1.9rc1", "1.9", "1.8.1", "1.8", "1.7", "1.6"])
        req = Requirement.parse("bliss #rq.filter:", 0)
        self.assertEqual(req.latest_version_within_specs, "1.9")

        req = Requirement.parse("bliss==1.8rc1 #rq.filter:", 0)
        self.assertEqual(req.prereleases, True)
        self.assertEqual(req.latest_version_within_specs, "1.9rc1")

        req = Requirement.parse("bliss #rq.filter: >=1.7,<1.9", 0)
        self.assertEqual(req.latest_version_within_specs, "1.8.1")

        pkg.delete()

        pkg = package_factory("gevent",
                              versions=['1.1rc1', '1.1b6', '1.1b5', '1.1b4', '1.1b3', '1.1b2', '1.1b1', '1.1a2',
                                        '1.1a1', '1.0.2', '1.0.1', ])
        req = Requirement.parse("gevent==1.1b6", 0)
        self.assertEqual(req.latest_version_within_specs, "1.1rc1")
        self.assertEqual(req.latest_version, "1.1rc1")

    def test_version_unpinned(self):
        p = package_factory(name="django", versions=["1.9", "1.8"])
        r = Requirement.parse("Django", 0)
        self.assertEqual(r.version, "1.9")
        p.delete()

        p = package_factory(name="django", versions=["1.9rc1", "1.9", "1.8"])
        r = Requirement.parse("Django", 0)
        self.assertEqual(r.version, "1.9")
        p.delete()

        p = package_factory(name="django", versions=["1.9.1", "1.8", "1.9rc1"])
        r = Requirement.parse("django", 0)
        self.assertEqual(r.version, "1.9.1")
        p.delete()

        p = package_factory(name="django", versions=["1.4.3", "1.5", "1.4.2", "1.4.1", ])
        r = Requirement.parse("Django  # rq.filter: >=1.4,<1.5", 0)
        self.assertEqual(r.version, "1.4.3")
        p.delete()

        p = package_factory(name="django", versions=["1.8.1", "1.8"])
        r = Requirement.parse("Django  # rq.filter: != 1.8.1", 0)
        self.assertEqual(r.version, "1.8")
        p.delete()

        p = package_factory(name="django", versions=["1.9rc1", "1.9.1", "1.8", ])
        r = Requirement.parse("django  # rq.filter: bogus", 0)
        self.assertEqual(r.version, "1.9.1")
        p.delete()

    def test_version_pinned(self):
        p = package_factory(name="django", versions=["1.8", "1.9"])
        r = Requirement.parse("Django==1.9", 0)
        self.assertEqual(r.version, "1.9")
        p.delete()

        p = package_factory(name="django==1.9rc1", versions=["1.8", "1.9rc1", "1.9rc2"])
        r = Requirement.parse("Django==1.9.2.rc14 # rq.filter != 1.44", 0)
        self.assertEqual(r.version, "1.9.2.rc14")
        p.delete()

    def test_prereleases(self):
        r = Requirement.parse("Django==1.9rc1", 0)
        self.assertEqual(r.prereleases, True)

        r = Requirement.parse("Django==1.9-b1", 0)
        self.assertEqual(r.prereleases, True)

        r = Requirement.parse("Django==1.9-alpha1", 0)
        self.assertEqual(r.prereleases, True)

        r = Requirement.parse("Django", 0)
        self.assertEqual(r.prereleases, False)

        r = Requirement.parse("Django>=1.5,<=1.6", 0)
        self.assertEqual(r.prereleases, False)

        r = Requirement.parse("Django!=1.9", 0)
        self.assertEqual(r.prereleases, False)

    def test_name(self):
        r = Requirement.parse("Django==1.9rc1", 0)
        self.assertEqual(r.name, "Django")

        r = Requirement.parse("django==1.9-b1", 0)
        self.assertEqual(r.name, "django")

    def test_serialize(self):
        r = Requirement.parse("Django==1.9", 0)

        data = {'line': 'Django==1.9', 'pull_request': None, 'lineno': 0}
        self.assertEqual(r.serialize(), data)
        r.pull_request = PullRequest(None, None, None, datetime.fromtimestamp(1448023411.173526))
        data["pull_request"] = {"state": None, "title": None, "url": None, "created_at": 1448023411.173526}
        self.assertEqual(r.serialize(), data)

        r = Requirement.parse("DETAILS", 0)
        r.pull_request = PullRequest(state="closed", title="the foo", url="foo.bar", created_at=datetime.fromtimestamp(1448023411.173526))
        data = {'line': 'DETAILS', 'pull_request': r.pull_request.serialize(), 'lineno': 0}
        self.assertEqual(r.serialize(), data)

    def test_deserialize(self):
        data = {'line': 'Django==1.9', 'pull_request': None, 'lineno': 0}
        r = Requirement.deserialize(data)
        self.assertEqual(r.line, "Django==1.9")
        self.assertEqual(r.lineno, 0)
        self.assertEqual(r.specs, [("==", "1.9")])
        self.assertEqual(r.name, "Django")
        self.assertEqual(r.pull_request, None)

        data["pull_request"] = {"state": None, "title": None, "url": None, "created_at": 1448023411.173526}
        r = Requirement.deserialize(data)
        self.assertNotEqual(r.pull_request, None)


class RequirementsFileTestCase(TestCase):
    def test_parse_empty_line(self):
        content = """
        """
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(r.requirements, [])
        self.assertEqual(r._other_files, [])

    def test_parse_comment_line(self):
        content = """
# the comment is here
        """
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(r.requirements, [])
        self.assertEqual(r._other_files, [])

    def test_unsupported_line_start(self):
        content = """
-f foo
--find-links bla
-i bla
--index-url bla
--extra-index-url bla
--no-index bla
--allow-external
--allow-unverified
-Z
--always-unzip
        """
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(r.requirements, [])
        self.assertEqual(r._other_files, [])

    @patch("pyupio.requirements.requirement.Requirement.package")
    def test_parse_requirement(self, package):
        package.return_value = True
        content = """
-e common/lib/calc
South==1.0.1
pycrypto>=2.6
git+https://github.com/pmitros/pyfs.git@96e1922348bfe6d99201b9512a9ed946c87b7e0b
distribute>=0.6.28, <0.7
# bogus comment
-e .
pdfminer==20140328
-r production/requirements.txt
--requirement test.txt
        """
        r = RequirementFile("r.txt", content=content)

        self.assertEqual(
            r.other_files, [
                "production/requirements.txt",
                "test.txt"
            ]
        )

        self.assertEqual(
            r.requirements, [
                Requirement.parse("South==1.0.1", 3),
                Requirement.parse("pycrypto>=2.6", 4),
                Requirement.parse("distribute>=0.6.28, <0.7", 6),
                Requirement.parse("pdfminer==20140328", 3),
            ]
        )

    def test_resolve_file(self):
        resolved = RequirementFile.resolve_file("base/requirements.txt", "-r requirements/production.txt")
        self.assertEqual(resolved, "base/requirements/production.txt")

        resolved = RequirementFile.resolve_file("base/requirements.txt", "-r requirements/production.txt # prod file")
        self.assertEqual(resolved, "base/requirements/production.txt")

        resolved = RequirementFile.resolve_file("requirements.txt", "-r production.txt # prod file")
        self.assertEqual(resolved, "production.txt")

    def test_serialize(self):
        content = """
Django
-r foo.txt
        """
        data = {"content": content, "path": "req.txt", "sha": None, "_other_files": None, "_requirements": None,
                "_is_valid": None}
        r = RequirementFile(content=content, path="req.txt")
        self.assertEqual(r.serialize(), data)

        # data["_requirements"] = [r.serialize() for r in r.requirements]
        # data["_other_files"] = r.other_files
        self.assertEqual(r.serialize(), data)

    @patch("pyupio.requirements.requirement.Requirement.package")
    def test_deserialize(self, package):
        package.return_value = True
        data = {'_other_files': None, '_requirements': None, 'path': 'req.txt',
                'content': '\nDjango\n-r foo.txt\n        ',
                'sha': None, "_is_valid": None}
        r = RequirementFile.deserialize(data)
        self.assertEqual(r._other_files, None)
        self.assertEqual(r._requirements, None)
        self.assertEqual(r.path, "req.txt")
        self.assertEqual(r.content, data["content"])
        self.assertEqual(r.sha, None)
        self.assertEqual(r.requirements, [Requirement.parse("Django", 2)])
        self.assertEqual(r.other_files, ["foo.txt", ])

        data = {'_is_valid': True, '_other_files': ['foo.txt'],
                '_requirements': [{'pull_request': None, 'line': 'Django', 'lineno': 2}],
                'path': 'req.txt', 'content': '\nDjango\n-r foo.txt\n        ', 'sha': None}
        r = RequirementFile.deserialize(data)
        self.assertEqual(r.path, "req.txt")
        self.assertEqual(r.content, data["content"])
        self.assertEqual(r.sha, None)
        self.assertEqual(r._requirements, [Requirement.parse("Django", 2)])
        self.assertEqual(r._other_files, ["foo.txt", ])


class RequirementsTestCase(TestCase):
    def test_has_file(self):
        reqs = RequirementsBundle()
        self.assertEqual(reqs.has_file("foo.txt"), False)
        self.assertEqual(reqs.has_file(""), False)
        reqs.add(RequirementFile(path="foo.txt", content=''))
        self.assertEqual(reqs.has_file("foo.txt"), True)

    def test_add(self):
        reqs = RequirementsBundle()
        self.assertEqual(reqs.requirement_files, [])
        reqs.add(RequirementFile(path="foo.txt", content=''))
        self.assertEqual(reqs.requirement_files[0].path, "foo.txt")

    def test_serialize(self):
        reqs = RequirementsBundle()
        reqs.add(RequirementFile(path="foo.txt", content='Django'))
        data = {'requirement_files': [
            {'content': 'Django', 'sha': None, '_other_files': None, 'path': 'foo.txt', '_requirements': None,
             "_is_valid": None}]}
        self.assertEqual(data, reqs.serialize())

    @patch("pyupio.requirements.requirement.Requirement.package")
    def test_deserialize(self, package):
        package.return_value = True
        data = {'requirement_files': [
            {'content': 'Django', 'sha': None, '_other_files': None, 'path': 'foo.txt', '_requirements': None,
             "_is_valid": None}]}
        reqs = Requirements.deserialize(data)
        self.assertEqual(reqs.requirement_files[0].path, "foo.txt")
        self.assertEqual(reqs.requirement_files[0].requirements[0].name, "Django")
