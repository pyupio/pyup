# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from unittest import TestCase
from pyup.requirements import Requirement
from mock import patch, PropertyMock, Mock
from pyup.requirements import RequirementFile, RequirementsBundle
from .test_package import package_factory
import requests_mock
import os


class RequirementUpdateContent(TestCase):

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    def test_tox_ini(self, _):
        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="2.9.5"):
            content = "[testenv:bandit]\n" \
                      "commands =\n" \
                      "\tbandit --ini setup.cfg -ii -l --recursive project_directory\n" \
                      "deps =\n" \
                      "\tbandit==1.4.0\n" \
                      "\n" \
                      "[testenv:manifest]\n" \
                      "commands =\n" \
                      "\tcheck-manifest --verbose\n"
            req_file = RequirementFile("tox.ini", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("bandit==1.4.0", 1),
                req
            )
            updated = req.update_content(content)
            new_content = "[testenv:bandit]\n" \
                      "commands =\n" \
                      "\tbandit --ini setup.cfg -ii -l --recursive project_directory\n" \
                      "deps =\n" \
                      "\tbandit==2.9.5\n" \
                      "\n" \
                      "[testenv:manifest]\n" \
                      "commands =\n" \
                      "\tcheck-manifest --verbose\n"
            self.assertEqual(updated, new_content)

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    def test_conda_file(self, _):

        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="2.9.5"):
            content = "name: my_env\n" \
                      "dependencies:\n" \
                      "  - gevent=1.2.1\n" \
                      "  - pip:\n" \
                      "    - beautifulsoup4==1.2.3\n"
            req_file = RequirementFile("req.yml", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("beautifulsoup4==1.2.3", 1),
                req
            )
            updated = req.update_content(content)
            new_content = "name: my_env\n" \
                      "dependencies:\n" \
                      "  - gevent=1.2.1\n" \
                      "  - pip:\n" \
                      "    - beautifulsoup4==2.9.5\n"
            self.assertEqual(updated, new_content)

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    def test_multispace(self, _):

        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="2.9.5"):
            content = "                   pass"
            req_file = RequirementFile("req.txt", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("pass", 1),
                req
            )
            updated = req.update_content(content)
            self.assertEqual(updated, "pass==2.9.5")

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    def test_compatible(self, _):

        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="2.9.5"):
            content = "Jinja2~=2.9.4         # via flask"
            req_file = RequirementFile("req.txt", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("Jinja2~=2.9.4         # via flask", 1),
                req
            )

            self.assertEqual(req.update_content(content), "Jinja2==2.9.5         # via flask")

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    def test_compatible_matching_latest(self, _):

        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="2.9.5"):
            content = "Jinja2~=2.9.5         # via flask"
            req_file = RequirementFile("req.txt", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("Jinja2~=2.9.5         # via flask", 1),
                req
            )

            self.assertEqual(req.update_content(content), "Jinja2==2.9.5         # via flask")

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    def test_update_contains_correct_sep_char(self, _):

        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="2.9.5"):
            content = "Jinja2==2.9.4         # via flask"
            req_file = RequirementFile("req.txt", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("Jinja2==2.9.4         # via flask", 1),
                req
            )

            self.assertEqual(req.update_content(content), "Jinja2==2.9.5         # via flask")

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    @patch("pyup.requirements.Requirement.get_hashes")
    def test_update_with_hashes(self, get_hashes_mock, _):
        get_hashes_mock.return_value = [{"hash": "123"}, {"hash": "456"}]
        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "alembic==0.8.9 \\\n" \
                      "        --hash=sha256:abcde"
            req_file = RequirementFile("req.txt", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("alembic==0.8.9", 1),
                req
            )

            self.assertEqual(req.update_content(content), "alembic==1.4.2 \\\n"
                                                          "    --hash=sha256:123 \\\n"
                                                          "    --hash=sha256:456")

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    @patch("pyup.requirements.Requirement.get_hashes")
    def test_update_with_hashes_and_comment(self, get_hashes_mock, _):
        get_hashes_mock.return_value = [{"hash": "123"}, {"hash": "456"}]
        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "alembic==0.8.9 \\\n" \
                      "        --hash=sha256:abcde # yay"
            req_file = RequirementFile("req.txt", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("alembic==0.8.9", 1),
                req
            )

            new_content = req.update_content(content)
            self.assertEqual(new_content, "alembic==1.4.2 \\\n"
                                                          "    --hash=sha256:123 \\\n"
                                                          "    --hash=sha256:456 # yay")

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    @patch("pyup.requirements.Requirement.get_hashes")
    def test_update_with_hashes_and_comment_and_env_markers(self, get_hashes_mock, _):
        get_hashes_mock.return_value = [{"hash": "123"}, {"hash": "456"}]
        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "alembic==0.8.9; sys_platform != 'win32' \\\n" \
                      "        --hash=sha256:abcde # yay"
            req_file = RequirementFile("req.txt", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("alembic==0.8.9; sys_platform != 'win32'", 1),
                req
            )

            new_content = req.update_content(content)
            self.assertEqual(new_content, "alembic==1.4.2; sys_platform != 'win32' \\\n"
                                                          "    --hash=sha256:123 \\\n"
                                                          "    --hash=sha256:456 # yay")

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    @patch("pyup.requirements.Requirement.get_hashes")
    def test_update_with_hashes_and_comment_all_in_one_line(self, get_hashes_mock, _):
        get_hashes_mock.return_value = [{"hash": "123"}, {"hash": "456"}]
        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "alembic==0.8.9 --hash=sha256:abcde # yay"
            req_file = RequirementFile("req.txt", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("alembic==0.8.9", 1),
                req
            )

            new_content = req.update_content(content)
            self.assertEqual(new_content, "alembic==1.4.2 \\\n"
                                          "    --hash=sha256:123 \\\n"
                                          "    --hash=sha256:456 # yay")

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    @patch("pyup.requirements.Requirement.get_hashes")
    def test_taskcluster_215(self, get_hashes_mock, _):
        get_hashes_mock.return_value = [{"hash": "123"}, {"hash": "456"}]
        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "taskcluster==0.3.4 --hash sha256:d4fe5e2a44fe27e195b92830ece0a6eb9eb7ad9dc556a0cb16f6f2a6429f1b65"
            req_file = RequirementFile("req.txt", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("taskcluster==0.3.4", 1),
                req
            )

            new_content = req.update_content(content)
            self.assertEqual(new_content, "taskcluster==1.4.2 \\\n"
                                          "    --hash=sha256:123 \\\n"
                                          "    --hash=sha256:456")

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    @patch("pyup.requirements.Requirement.get_hashes")
    def test_update_with_hashes_and_comment_and_env_markers_all_in_one_line(self, get_hashes_mock, _):
        get_hashes_mock.return_value = [{"hash": "123"}, {"hash": "456"}]
        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "alembic==0.8.9; sys_platform != 'win32' --hash=sha256:abcde # yay"
            req_file = RequirementFile("req.txt", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("alembic==0.8.9; sys_platform != 'win32'", 1),
                req
            )

            new_content = req.update_content(content)
            self.assertEqual(new_content, "alembic==1.4.2; sys_platform != 'win32' \\\n"
                                          "    --hash=sha256:123 \\\n"
                                          "    --hash=sha256:456 # yay")

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    @patch("pyup.requirements.Requirement.get_hashes")
    def test_update_with_hashes_in_one_line(self, get_hashes_mock, _):
        get_hashes_mock.return_value = [{"hash": "123"}, {"hash": "456"}]
        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "alembic==0.8.9 --hash=sha256:abcde"
            req_file = RequirementFile("req.txt", content)
            req = list(req_file.requirements)[0]
            self.assertEqual(
                Requirement.parse("alembic==0.8.9", 1),
                req
            )

            new_content = req.update_content(content)
            self.assertEqual(new_content, "alembic==1.4.2 \\\n"
                                          "    --hash=sha256:123 \\\n"
                                          "    --hash=sha256:456")

    def test_update_with_environment_markers(self):
        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="1.4.2"):

            content = "uvloop==0.6.5; sys_platform != 'win32'"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "uvloop==1.4.2; sys_platform != 'win32'")

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    def test_update_with_environment_markers_and_comment(self, _):
        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock,
                   return_value="1.4.2"):

            content = "uvloop==0.6.5; sys_platform != 'win32' # and here's some comment"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "uvloop==1.4.2; sys_platform != 'win32' # and here's some comment")

    def test_update_content_with_extras(self):
        with patch('pyup.requirements.Requirement.latest_version_within_specs', new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "requests[security]==1.4.1"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "requests[security]==1.4.2")

    def test_update_content_tabbed(self):
        with patch('pyup.requirements.Requirement.latest_version_within_specs', new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "bla==1.4.1\t\t# some foo"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "bla==1.4.2\t\t# some foo")

            content = "bla==1.4.1\t\t# pyup: <1.4.2"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "bla==1.4.2\t\t# pyup: <1.4.2")

    def test_something_else(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="0.13.1"):
            content = "some-package==0.12.2+tmf"
            req = Requirement.parse(content, 0)
            self.assertEqual(req.update_content(content), "some-package==0.13.1")

    def test_line_endings(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="1.2.3"):
            with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                       return_value=package_factory("Foo", [])):
                content = """\r\n\r\nWerkzeug\r\ndjango-template-repl\nbpython\nsome-fooo    \n"""
                r = RequirementFile("foo.txt", content)
                self.assertEqual(r.requirements[0].name, "Werkzeug")
                self.assertEqual(r.requirements[1].name, "django-template-repl")
                self.assertEqual(r.requirements[2].name, "bpython")
                self.assertEqual(r.requirements[3].name, "some-fooo")
                self.assertTrue("Werkzeug==1.2.3\r\n" in r.requirements[0].update_content(content))
                self.assertTrue(
                    "django-template-repl==1.2.3\n" in r.requirements[1].update_content(content))
                self.assertTrue(
                    "bpython==1.2.3" in r.requirements[2].update_content(content))
                self.assertTrue(
                    "some-fooo==1.2.3    \n" in r.requirements[3].update_content(content))

    def test_update_content_simple_pinned(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "Django==1.4.1"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "Django==1.4.2")

        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "django==1.4.1"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "django==1.4.2")

    def test_latest_version_within_specs_called(self):

        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock, return_value="1.4.2") as mocked:
            content = "django==1.4.1"
            req = Requirement.parse(content, 0)
            self.assertEqual(req.update_content(content), "django==1.4.2")
            mocked.assert_called_with()

    def test_update_content_simple_unpinned(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "django"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "django==1.4.2")

        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "Django"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "Django==1.4.2")

    def test_update_content_simple_unpinned_with_comment(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "django # newest django release"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "django==1.4.2 # newest django release")

        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "Django #django"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content), "Django==1.4.2 #django")

        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="1.4.2"):
            content = "Django #django #yay this has really cool comments ######"
            req = Requirement.parse(content, 0)

            self.assertEqual(req.update_content(content),
                             "Django==1.4.2 #django #yay this has really cool comments ######")

    def test_update_content_with_package_in_comments(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="2.58.1.44"):
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

    def test_update_content_with_dubious_package_name(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="2.58.1.44"):
            content = 'raven\n' \
                      'ravenclient'
            req = Requirement.parse("raven", 0)
            updated_content = 'raven==2.58.1.44\n' \
                              'ravenclient'
            self.assertEqual(req.update_content(content), updated_content)

    def test_update_content_ranged(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="1.5.6"):
            content = 'raven>=0.2\n' \
                      'ravenclient'
            req = Requirement.parse("raven>=0.2", 0)
            updated_content = 'raven==1.5.6\n' \
                              'ravenclient'
            self.assertEqual(req.update_content(content), updated_content)

    def test_update_content_unfinished_line(self):
        with patch('pyup.requirements.Requirement.latest_version', new_callable=PropertyMock,
                   return_value="1.5.6"):
            content = 'raven==0.2\n'
            req = Requirement.parse("raven==0.2", 0)
            updated_content = 'raven==1.5.6\n'
            self.assertEqual(req.update_content(content), updated_content)


class RequirementTestCase(TestCase):

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    def test_is_outdated(self, _):
        with patch('pyup.requirements.Requirement.latest_version_within_specs',
                   new_callable=PropertyMock, return_value=None):
            r = Requirement.parse("Django", 0)
            self.assertEqual(r.is_outdated, False)

    def test_equals(self):
        self.assertEqual(
            Requirement.parse("Django==1.5", 0),
            Requirement.parse("Django==1.5", 0)
        )

    def test_not_equals(self):
        self.assertNotEqual(
            Requirement.parse("Django==1.5", 0),
            Requirement.parse("Django==1.6", 0)
        )

    def test_filter(self):
        from packaging.specifiers import SpecifierSet
        r = Requirement.parse("Django==1.7.6", 0)
        self.assertEqual(r.filter, False)

        r = Requirement.parse("Django==1.7.6 # pyup: < 1.7.8", 0)
        self.assertEqual(r.filter, SpecifierSet("<1.7.8"))

        req = Requirement.parse("some-package==1.9.3 # rq.filter: <1.10 #some comment here", 0)
        self.assertEqual(req.filter, SpecifierSet("<1.10"))

        r = Requirement.parse("django==1.7.1  # pyup: <1.7.6", 0)

        r = Requirement.parse("Django==1.7.6 # pyup: < 1.7.8, > 1.7.2", 0)
        self.assertEqual(
            sorted([s._spec for s in r.filter._specs], key=lambda r: r[1]),
            sorted([("<", "1.7.8"), (">", "1.7.2")], key=lambda r: r[1])
        )

        r = Requirement.parse("Django==1.7.6 # pyup:< 1.7.8", 0)
        self.assertEqual(r.filter, SpecifierSet("<1.7.8"))

    def test_until_filter(self):
        from packaging.specifiers import SpecifierSet
        from datetime import datetime, timedelta
        tommorow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        r = Requirement.parse("Django==1.7.6 # pyup: < 1.7.8 until {}".format(yesterday), 0)
        self.assertEqual(r.filter, False)

        r = Requirement.parse("Django==1.7.6 # pyup: < 1.7.8 until {}".format(tommorow), 0)
        self.assertEqual(r.filter, SpecifierSet("<1.7.8"))

        r = Requirement.parse("Django==1.7.6 # pyup: < 1.7.8 until 348-34-1234", 0)
        self.assertEqual(r.filter, SpecifierSet("<1.7.8"))


    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    def test_update_filter(self, _):
        latest_fn = 'pyup.requirements.Requirement.latest_version'

        with patch(latest_fn, new_callable=PropertyMock, return_value='1.8.7'):
            r = Requirement.parse("Django==1.7.6", 0)
            self.assertTrue(r.needs_update)
            self.assertTrue(r.can_update_semver)

            r = Requirement.parse("Django==1.7.6 # pyup: update major", 0)
            self.assertFalse(r.can_update_semver)
            self.assertFalse(r.needs_update)

            r = Requirement.parse("Django==0.2.6 # pyup: update major", 0)
            self.assertTrue(r.can_update_semver)
            self.assertTrue(r.needs_update)

        with patch(latest_fn, new_callable=PropertyMock, return_value='1.8.7'):
            r = Requirement.parse("Django==1.7.6", 0)
            self.assertTrue(r.needs_update)
            self.assertTrue(r.can_update_semver)

            r = Requirement.parse("Django==1.7.6 # pyup: update minor", 0)
            self.assertTrue(r.can_update_semver)
            self.assertTrue(r.needs_update)

            r = Requirement.parse("Django==1.8.6 # pyup: update minor", 0)
            self.assertFalse(r.can_update_semver)
            self.assertFalse(r.needs_update)

            r = Requirement.parse("Django==1.9.6 # pyup: update minor", 0)
            self.assertFalse(r.can_update_semver)
            self.assertFalse(r.needs_update)

        with patch(latest_fn, new_callable=PropertyMock, return_value='1.2.4'):
            r = Requirement.parse("Django==1.2.3", 0)
            self.assertTrue(r.needs_update)
            self.assertTrue(r.can_update_semver)

            r = Requirement.parse("Django==1.2.3 # pyup: update minor", 0)
            self.assertFalse(r.can_update_semver)
            self.assertFalse(r.needs_update)

            r = Requirement.parse("Django==1.2.2 # pyup: update minor", 0)
            self.assertFalse(r.can_update_semver)
            self.assertFalse(r.needs_update)

            r = Requirement.parse("Django==1.2 # pyup: update minor", 0)
            self.assertFalse(r.can_update_semver)
            self.assertFalse(r.needs_update)

    def test_convert_semver(self):
        self.assertEquals({"major": 1, "minor": 2, "patch": 3}, Requirement.convert_semver("1.2.3"))
        self.assertEquals({"major": 1, "minor": 2, "patch": 0}, Requirement.convert_semver("1.2"))
        self.assertEquals({"major": 1, "minor": 0, "patch": 0}, Requirement.convert_semver("1"))

    def test_tabbed(self):
        req = Requirement.parse("Django==1.5\t\t#some-comment", 0)
        self.assertEqual(req.is_pinned, True)
        self.assertEqual(req.version, "1.5")

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

    def test_is_compatible(self):
        req = Requirement.parse("Django~=1.5", 0)
        self.assertEqual(req.is_compatible, True)

        req = Requirement.parse("Django<=1.4,>1.5", 0)
        self.assertEqual(req.is_compatible, False)

        req = Requirement.parse("Django===1.4", 0)
        self.assertEqual(req.is_compatible, False)

        req = Requirement.parse("Django<=1.4,>=1.33", 0)
        self.assertEqual(req.is_compatible, False)

        req = Requirement.parse("Django==1.4", 0)
        self.assertEqual(req.is_compatible, False)

    def test_is_open_ranged(self):
        req = Requirement.parse("Django>=1.5", 0)
        self.assertEqual(req.is_open_ranged, True)

        req = Requirement.parse("Django<=1.4,>1.5", 0)
        self.assertEqual(req.is_open_ranged, False)

        req = Requirement.parse("Django===1.4", 0)
        self.assertEqual(req.is_open_ranged, False)

        req = Requirement.parse("Django<=1.4,>=1.33", 0)
        self.assertEqual(req.is_open_ranged, False)

        req = Requirement.parse("Django==1.4", 0)
        self.assertEqual(req.is_open_ranged, False)

        req = Requirement.parse("Django>=1.4,<=1.7", 0)
        self.assertEqual(req.is_open_ranged, False)

    def test_package_filter_present(self):
        req = Requirement.parse("Django", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("Django #rq.filter:", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("Django #rq.filter: >=1.4,<1.5", 0)
        self.assertEqual(
            sorted([s._spec for s in req.filter._specs], key=lambda i: i[0]),
            sorted([('>=', '1.4'), ('<', '1.5')], key=lambda i: i[0])
        )

        req = Requirement.parse("Django #rq.filter:!=1.2", 0)
        self.assertEqual([s._spec for s in req.filter._specs], [('!=', '1.2')])

        req = Requirement.parse("Django #rq.filter:foo", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("bliss #rq.filter:", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("Django", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("Django #pyup:", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("Django #pyup: >=1.4,<1.5", 0)
        self.assertEqual(
            sorted([s._spec for s in req.filter._specs], key=lambda i: i[0]),
            sorted([('>=', '1.4'), ('<', '1.5')], key=lambda i: i[0])
        )


        req = Requirement.parse("Django #pyup:!=1.2", 0)
        self.assertEqual([s._spec for s in req.filter._specs], [('!=', '1.2')])

        req = Requirement.parse("Django #pyup:foo", 0)
        self.assertEqual(req.filter, False)

        req = Requirement.parse("bliss #pyup:", 0)
        self.assertEqual(req.filter, False)


    def test_get_latest_version_within_specs(self):
        from packaging.specifiers import SpecifierSet
        latest = Requirement.get_latest_version_within_specs(
            SpecifierSet("==1.2,!=1.2"),
            ["1.2", "1.3", "1.4", "1.5"]
        )

        self.assertEqual(latest, None)

        latest = Requirement.get_latest_version_within_specs(
            SpecifierSet("==1.2.1"),
            ["1.2.0", "1.2.1", "1.2.2", "1.3"]
        )

        self.assertEqual(latest, "1.2.1")

    def test_latest_version_within_specs(self):
        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory("bliss",
                                                versions=["1.9rc1", "1.9", "1.8.1", "1.8", "1.7",
                                                          "1.6"])):
            req = Requirement.parse("bliss #rq.filter:", 0)
            self.assertEqual(req.latest_version_within_specs, "1.9")

            req = Requirement.parse("bliss==1.8rc1 #rq.filter:", 0)
            self.assertEqual(req.prereleases, True)
            self.assertEqual(req.latest_version_within_specs, "1.9rc1")

            req = Requirement.parse("bliss #rq.filter: >=1.7,<1.9", 0)
            self.assertEqual(req.latest_version_within_specs, "1.8.1")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory("gevent",
                                                versions=['1.1rc1', '1.1b6', '1.1b5', '1.1b4',
                                                          '1.1b3', '1.1b2', '1.1b1', '1.1a2',
                                                          '1.1a1', '1.0.2', '1.0.1', ])):
            req = Requirement.parse("gevent==1.1b6", 0)
            self.assertEqual(req.latest_version_within_specs, "1.1rc1")
            self.assertEqual(req.latest_version, "1.1rc1")

    def test_version_unpinned(self):
        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.9", "1.8"])):
            r = Requirement.parse("Django", 0)
            self.assertEqual(r.version, "1.9")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.9rc1", "1.9", "1.8"])):
            r = Requirement.parse("Django", 0)
            self.assertEqual(r.version, "1.9")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django",
                                                versions=["1.9.1", "1.8", "1.9rc1"])):
            r = Requirement.parse("django", 0)
            self.assertEqual(r.version, "1.9.1")

        print("FILTER TEST")
        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(
                       name="django",
                       versions=["1.4.3", "1.5", "1.4.2", "1.4.1", ])):
            r = Requirement.parse("Django  # rq.filter: >=1.4,<1.5", 0)
            self.assertEqual(r.version, "1.4.3")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(
                       name="django",
                       versions=["1.4.3", "1.5", "1.4.2", "1.4.1", ])):
            r = Requirement.parse("Django  # pyup: >=1.4,<1.5", 0)
            self.assertEqual(r.version, "1.4.3")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.8.1", "1.8"])):
            r = Requirement.parse("Django  # rq.filter: !=1.8.1", 0)
            self.assertEqual(r.version, "1.8")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.8.1", "1.8"])):
            r = Requirement.parse("Django  # pyup: !=1.8.1", 0)
            self.assertEqual(r.version, "1.8")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django",
                                                versions=["1.9rc1", "1.9.1", "1.8", ])):
            r = Requirement.parse("django  # rq.filter: bogus", 0)
            self.assertEqual(r.version, "1.9.1")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django",
                                                versions=["1.9rc1", "1.9.1", "1.8", ])):
            r = Requirement.parse("django  # pyup: bogus", 0)
            self.assertEqual(r.version, "1.9.1")

    def test_version_pinned(self):
        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django", versions=["1.8", "1.9"])):
            r = Requirement.parse("Django==1.9", 0)
            self.assertEqual(r.version, "1.9")

        with patch('pyup.requirements.Requirement.package', new_callable=PropertyMock,
                   return_value=package_factory(name="django==1.9rc1",
                                                versions=["1.8", "1.9rc1", "1.9rc2"])):
            r = Requirement.parse("Django==1.9.2.rc14 # rq.filter != 1.44", 0)
            self.assertEqual(r.version, "1.9.2.rc14")

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

    @requests_mock.mock()
    def test_package_found(self, requests):
        with open(os.path.dirname(os.path.realpath(__file__)) + "/data/django.json") as f:
            requests.get("https://pypi.org/pypi/Django/json", text=f.read())
        r = Requirement.parse("Django==1.9rc1", 0)
        self.assertEqual(r._fetched_package, False)
        self.assertEqual(r._package, None)

        # this triggers the fetch
        self.assertNotEqual(r.package, None)
        self.assertEqual(r._fetched_package, True)
        self.assertNotEqual(r._package, None)

    @requests_mock.mock()
    def test_package_not_found(self, requests):
        requests.get("https://pypi.org/pypi/Fango/json", text="404", status_code=404)
        r = Requirement.parse("Fango", 0)
        self.assertEqual(r._fetched_package, False)
        self.assertEqual(r._package, None)

        # this triggers the fetch
        self.assertEqual(r.package, None)
        self.assertEqual(r._fetched_package, True)
        self.assertEqual(r._package, None)

    @patch("pyup.requirements.safety")
    @patch("pyup.requirements.settings")
    def test_is_insecure(self, settings, safety):
        """with self.assertRaises(NotImplementedError):
            r = Requirement.parse("Django", 0)
            r.is_insecure"""
        # test safety is not called if the api key not set
        settings.api_key = None
        r = Requirement.parse("Django", 0)
        self.assertFalse(r.is_insecure)
        safety.check.assert_not_called()

        # test safety is called if the api key is set
        settings.api_key = "foo"
        r = Requirement.parse("Django", 0)
        self.assertFalse(r.is_insecure)

        safety.check.return_value = []
        safety.check.assert_called_with(
            cached=True,
            db_mirror='',
            ignore_ids=(),
            key=settings.api_key,
            packages=(r,)
        )

    @requests_mock.mock()
    @patch("pyup.requirements.settings")
    def test_changelogs(self, requests, settings):
        # test that the api is not called if the api key is not set
        settings.api_key = None
        r = Requirement.parse("pyupio", 0)
        self.assertEquals(r.changelog, {})

        # test the api is called if the api key is set
        settings.api_key = "foo"
        r = Requirement.parse("pyupio", 0)
        from pyup.package import Package
        r._package = Package("pyupio", versions=['0.2'])
        r._fetched_package = True
        with open(os.path.dirname(os.path.realpath(__file__)) + "/data/pyup-changelog.json") as f:
            requests.get("https://pyup.io/api/v1/changelogs/pyupio/", text=f.read())
            log = r.changelog
            self.assertEquals(len(log), 6)




    @requests_mock.mock()
    def test_needs_update(self, requests):
        with open(os.path.dirname(os.path.realpath(__file__)) + "/data/django.json") as f:
            requests.get("https://pypi.org/pypi/Django/json", text=f.read())

            # is pinned and on latest
            r = Requirement.parse("Django==1.9rc1", 0)
            self.assertEqual(r.needs_update, False)

            # is ranged and open
            r = Requirement.parse("Django>=1.8", 0)
            self.assertEqual(r.needs_update, False)

            # is pinned but old
            r = Requirement.parse("Django==1.7", 0)
            self.assertEqual(r.needs_update, True)

            # is not pinned
            r = Requirement.parse("Django", 0)
            self.assertEqual(r.needs_update, True)

            # is compatible
            r = Requirement.parse("Django~=1.7", 0)
            self.assertEqual(r.needs_update, True)

    def test_str(self):
        r = Requirement.parse("Django==1.9rc1", 0)
        self.assertEqual(r.__str__(), "Requirement.parse(Django==1.9rc1, 0)")


class RequirementsFileTestCase(TestCase):

    def test_parse_empty_line(self):
        r = RequirementFile("foo.txt", "\n\n\n\n\n")
        self.assertEqual(r.requirements, [])

    @patch("pyup.requirements.Requirement.package", return_value="pkg")
    def test_parse_hashes(self, _):
        with open(os.path.dirname(os.path.realpath(__file__)) + "/data/hashed_reqs.txt") as f:
            content = f.read()
            r = RequirementFile("r.txt", content)
            self.assertEqual(
                [
                    Requirement.parse("alembic==0.8.9", 1),
                    Requirement.parse("amqp==2.1.1", 3),
                    Requirement.parse("argon2-cffi==16.3.0", 6),
                    Requirement.parse("Babel==2.3.4", 8),
                ],
                list(r.requirements)
            )

    def test_parse_index_server(self):
        line = "--index-url https://some.foo/"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

        line = "-i https://some.foo/"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

        line = "--extra-index-url https://some.foo/"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

        line = "--extra-index-url https://some.foo"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

        line = "--extra-index-url https://some.foo # some lousy comment"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

        line = "-i\t\t https://some.foo \t\t    # some lousy comment"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

        line = "--index-url"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            None
        )

        line = "--index-url=https://some.foo/"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

        line = "-i=https://some.foo/"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

        line = "--extra-index-url=https://some.foo/"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

        line = "--extra-index-url=https://some.foo"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

        line = "--extra-index-url=https://some.foo # some lousy comment"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

        line = "-i\t\t =https://some.foo \t\t    # some lousy comment"
        self.assertEqual(
            RequirementFile.parse_index_server(line),
            "https://some.foo/"
        )

    @patch("pyup.requirements.Requirement.package")
    def test_parse_package_with_index_server(self, package):
        content = """-i https://some.foo/\ndjango"""
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(r.requirements[0].index_server, "https://some.foo/")

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

    @patch("pyup.requirements.Requirement.package")
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

    @patch("pyup.requirements.Requirement.package")
    def test_ignore_file(self, package):
        package.return_value = True
        content = """# pyup: ignore file
foo
bar
baz"""
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(r.requirements, [])
        self.assertEqual(r._other_files, [])
        self.assertEqual(r.is_valid, False)

    @patch("pyup.requirements.Requirement.package")
    def test_ignore_requirement(self, package):
        package.return_value = True

        content = """foo
bar # pyup: ignore
baz"""
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(len(r.requirements), 2)
        self.assertEqual(
            r.requirements, [
                Requirement.parse("foo", 0),
                Requirement.parse("baz", 2)
            ]
        )

        content = """foo
        bar # pyup:ignore
        baz"""
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(len(r.requirements), 2)
        self.assertEqual(
            r.requirements, [
                Requirement.parse("foo", 0),
                Requirement.parse("baz", 2)
            ]
        )

    def test_resolve_file(self):
        resolved = RequirementFile.resolve_file(
            "base/requirements.txt",
            "-r requirements/production.txt"
        )
        self.assertEqual(resolved, "base/requirements/production.txt")

        resolved = RequirementFile.resolve_file(
            "base/requirements.txt",
            "-r requirements/production.txt # prod file"
        )
        self.assertEqual(resolved, "base/requirements/production.txt")

        resolved = RequirementFile.resolve_file(
            "requirements.txt",
            "-r production.txt # prod file"
        )
        self.assertEqual(resolved, "production.txt")

    def test_is_invalid(self):
        content = ''
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(r._is_valid, None)

        # this triggers the _parse
        self.assertEqual(r.is_valid, False)
        self.assertEqual(r._is_valid, False)

    def test_is_valid_other_file(self):
        content = '-r other_file.txt'
        r = RequirementFile("r.txt", content=content)
        self.assertEqual(r._is_valid, None)

        # this triggers the _parse
        self.assertEqual(r.is_valid, True)
        self.assertEqual(r._is_valid, True)

    def test_is_valid_requirement(self):
        with patch('pyup.requirements.Requirement.package', return_value=True):
            content = 'some_package'
            r = RequirementFile("r.txt", content=content)
            self.assertEqual(r._is_valid, None)

            # this triggers the _parse
            self.assertEqual(r.is_valid, True)
            self.assertEqual(r._is_valid, True)

    def test_str(self):
        r = RequirementFile("r.txt", "content", "asdfe")
        self.assertEqual(
            r.__str__(),
            "RequirementFile(path='r.txt', sha='asdfe', content='content')"
        )

        content = "more content than 30 characters here"
        r = RequirementFile("r.txt", content, "asdfe")
        self.assertEqual(
            r.__str__(),
            "RequirementFile(path='r.txt', sha='asdfe', "
            "content='more content than 30 character[truncated]')"
        )


class RequirementsBundleTestCase(TestCase):
    def test_has_file(self):
        reqs = RequirementsBundle()
        self.assertEqual(reqs.has_file_in_path("foo.txt"), False)
        self.assertEqual(reqs.has_file_in_path(""), False)
        reqs.append(RequirementFile(path="foo.txt", content=''))
        self.assertEqual(reqs.has_file_in_path("foo.txt"), True)

    def test_add(self):
        reqs = RequirementsBundle()
        self.assertEqual(reqs, [])
        reqs.append(RequirementFile(path="foo.txt", content=''))
        self.assertEqual(reqs[0].path, "foo.txt")

    def test_get_initial_update_class(self):
        req = RequirementsBundle()
        klass = req.get_update_class(
            initial=True,
            scheduled=False,
            config=None
        )
        self.assertEquals(klass, req.get_initial_update_class())

    def test_get_scheduled_update_class(self):
        req = RequirementsBundle()
        config = Mock()
        config.is_valid_schedule.return_value = True
        klass = req.get_update_class(
            initial=False,
            scheduled=True,
            config=config
        )
        self.assertEquals(klass, req.get_scheduled_update_class())

    def test_get_sequential_update_class(self):
        req = RequirementsBundle()
        klass = req.get_update_class(
            initial=False,
            scheduled=False,
            config=None
        )
        self.assertEquals(klass, req.get_sequential_update_class())

    def test_get_updates(self):
        with patch('pyup.requirements.Requirement.package', return_value=Mock()):
            reqs = RequirementsBundle()
            reqs.append(RequirementFile(path="r.txt", content='Bla'))
            updates = [u for u in reqs.get_updates(True, False, Mock())]
            self.assertEqual(len(updates), 1)
            #self.assertEqual(updates[0].__class__, reqs.get_initial_update_class().__class__)

            reqs = RequirementsBundle()
            reqs.append(RequirementFile(path="r.txt", content='Bla'))
            updates = [u for u in reqs.get_updates(False, False, Mock())]
            self.assertEqual(len(updates), 1)
            #self.assertEqual(updates[0].__class__, reqs.get_sequential_update_class().__class__)

    def test_requirements(self):
        with patch('pyup.requirements.Requirement.package', return_value=Mock()):
            reqs = RequirementsBundle()
            reqs.append(RequirementFile(path="r.txt", content='Bla\nFoo'))

            self.assertEqual([
                Requirement.parse("Bla", 1),
                Requirement.parse("Foo", 2)
            ],
                [r for r in reqs.requirements]
            )

