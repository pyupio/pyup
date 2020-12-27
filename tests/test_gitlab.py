# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from unittest import TestCase
from unittest import skip
from pyup.providers.gitlab import Provider
from pyup.requirements import RequirementsBundle
from pyup.config import Config
from pyup import errors
from mock import Mock, MagicMock, patch, PropertyMock, ANY
from base64 import b64encode

from gitlab.exceptions import GitlabGetError


class ProviderTest(TestCase):

    def setUp(self):
        self.provider = Provider(bundle=Mock())
        self.provider._api = Mock()
        self.repo = Mock()

    def test_is_same_user(self):
        this = Mock()
        this.login = "this"

        that = Mock()
        that.login = "that"

        self.assertFalse(Provider.is_same_user(this, that))

        that.login = "this"

        self.assertTrue(Provider.is_same_user(this, that))

    @patch("pyup.providers.gitlab.Gitlab")
    def test_api(self, gitlab_mock):
        prov = Provider(bundle=RequirementsBundle())
        prov._api("foo")
        gitlab_mock.assert_called_once_with("https://gitlab.com", "foo", ssl_verify=True)

    @patch("pyup.providers.gitlab.Gitlab")
    def test_api_different_host_in_provider_url(self, gitlab_mock):
        url = 'localhost'
        token = 'foo'

        prov = Provider(bundle=RequirementsBundle(), url=url)
        prov._api(token)
        gitlab_mock.assert_called_once_with(url, token, ssl_verify=True)

    @patch("pyup.providers.gitlab.Gitlab")
    def test_api_different_host_in_token(self, gitlab_mock):
        prov = Provider(bundle=RequirementsBundle())
        prov._api("foo@localhost")
        gitlab_mock.assert_called_once_with("localhost", "foo", ssl_verify=True)

    def test_get_user(self):
        self.provider.get_user("foo")
        self.provider._api().auth.assert_called_once_with()

    def test_get_repo(self):
        self.provider.get_repo("token", "name")
        self.provider._api().projects.get.assert_called_once_with("name")

    def test_get_repo_404(self):
        self.provider._api().projects.get.side_effect = \
            GitlabGetError(response_code=404)
        with self.assertRaises(errors.RepoDoesNotExistError):
            self.provider.get_repo("token", "name")

    def test_get_default_branch(self):
        self.repo.default_branch = "foo"
        self.assertEqual(
            self.provider.get_default_branch(self.repo),
            "foo"
        )

    def test_get_pull_request_permissions(self):
        # TODO: PORT
        user = Mock()
        user.login = "some-dude"
        self.provider.get_pull_request_permissions(user, self.repo)

    def test_iter_git_tree(self):
        mocked_items = [{"type": "type", "path": "path"}]
        self.repo.repository_tree.return_value = mocked_items
        items = list(self.provider.iter_git_tree(self.repo, "some branch"))
        self.repo.repository_tree.assert_called_with(ref="some branch",
                                                     all=True,
                                                     recursive=True)
        self.assertEqual(items, [("type", "path")])

    def test_get_file(self):
        content, obj = self.provider.get_file(self.repo, "path", "branch")
        self.assertIsNotNone(content)
        self.assertIsNotNone(obj)
        self.repo.files.get.assert_called_with(file_path="path", ref="branch")

    def test_get_requirement_file(self):
        req = self.provider.get_requirement_file(self.repo, "path", "branch")
        self.assertIsNotNone(req)
        self.provider.bundle.get_requirement_file_class.assert_called_once_with()
        self.assertEqual(self.provider.bundle.get_requirement_file_class().call_count, 1)

        self.provider.get_file = Mock(return_value = (None, None))
        req = self.provider.get_requirement_file(self.repo, "path", "branch")
        self.assertIsNone(req)

    def test_create_branch(self):
        self.provider.create_branch(self.repo, "base branch", "new branch")
        self.repo.branches.create.assert_called_with(
            {"branch": "new branch", "ref": "base branch"})

    def test_is_empty_branch(self):
        with self.assertRaises(AssertionError):
            self.provider.is_empty_branch(self.repo, "master", "foo", prefix="bar")

        self.repo.repository_compare().commits = []
        self.assertTrue(
            self.provider.is_empty_branch(self.repo, "master", "pyup-foo", prefix="pyup-")
        )

        self.repo.repository_compare().commits = []
        self.assertTrue(
            self.provider.is_empty_branch(self.repo, "master", "pyup/foo", prefix="pyup/")
        )

        self.repo.repository_compare().commits = [Mock()]
        self.assertFalse(
            self.provider.is_empty_branch(self.repo, "master", "pyup-foo", prefix="pyup-")
        )

    def test_delete_branch(self):
        with self.assertRaises(AssertionError):
            self.provider.delete_branch(self.repo, "foo", prefix="bar")

        self.provider.delete_branch(self.repo, "pyup-foo", prefix="pyup-")
        self.repo.branches.get.assert_called_with("pyup-foo")
        self.repo.branches.get().delete.assert_called_with()

        self.provider.delete_branch(self.repo, "pyup/foo", prefix="pyup/")
        self.repo.branches.get.assert_called_with("pyup/foo")
        self.repo.branches.get().delete.assert_called_with()

    @patch("pyup.providers.github.time")
    def test_create_commit(self, time):
        file = Mock()
        self.repo.files.get.return_value = file
        self.provider.create_commit("path", "branch", "commit", "content", "sha", self.repo, "com")
        self.assertEqual(self.repo.files.get.call_count, 1)
        self.assertEqual(file.content, b64encode(b"content").decode())
        self.assertEqual(file.encoding, "base64")
        file.save.assert_called_with(branch="branch", commit_message="commit")

    def test_create_and_commit_file(self):
        repo = Mock()
        path, branch, content, commit_message, committer = (
            '/foo.txt',
            'some-branch',
            'content',
            'some-message',
            'johnny'
        )
        data = self.provider.create_and_commit_file(
            repo=repo,
            path=path,
            commit_message=commit_message,
            branch=branch,
            content=content,
            committer=committer
        )
        repo.files.create.assert_called_once_with({
            'file_path': path,
            'branch': branch,
            'content': content,
            'commit_message': commit_message
        })

    def test_get_pull_request_committer(self):
        mr = MagicMock()
        mr.changes = MagicMock()
        mr.source_branch = "pyup-bla"
        d = {'source_branch': mr.source_branch}
        p = [{'username': 'alpha'}, {'username': 'beta'}]
        mr.changes.return_value = d
        self.repo.mergerequests.get.return_value = mr
        self.repo.mergerequests.list.return_value = [Mock()]
        mr.participants = Mock()
        mr.participants.return_value = p
        committers = self.provider.get_pull_request_committer(self.repo, mr)
        actual = [a.login for a in committers]
        expected = [a['username'] for a in p]
        self.assertEquals(actual, expected)

    def test_close_pull_request(self):
        mr = MagicMock()
        mr.changes = MagicMock()
        mr.source_branch = "pyup-bla"
        d = {'source_branch': mr.source_branch}
        mr.changes.return_value = d
        self.repo.mergerequests.get.return_value = mr
        self.repo.mergerequests.list.return_value = [Mock()]
        mr.changes.__getitem__.side_effect = d.__getitem__
        mr.changes.__iter__.side_effect = d.__iter__
        mr.changes.__contains__.side_effect = d.__contains__
        self.provider.close_pull_request(self.repo, self.repo, mr, "comment", prefix="pyup-")
        self.assertEqual(self.repo.branches.get().delete.call_count, 1)

    def test_merge_pull_request(self):
        mr = Mock()
        mr.merge.return_value = True
        config = Config()
        self.provider._merge_merge_request(mr, config)
        mr.merge.assert_called_once_with(merge_when_pipeline_succeeds=True,
                                         should_remove_source_branch=False)

    def test_merge_pull_request_with_remove(self):
        mr = Mock()
        mr.merge.return_value = True
        config = Config()
        config.update_config({'gitlab': {'should_remove_source_branch': True}})
        self.provider._merge_merge_request(mr, config)
        mr.merge.assert_called_once_with(merge_when_pipeline_succeeds=True,
                                         should_remove_source_branch=True)

    def test_create_pull_request_with_exceeding_body(self):
        body = ''.join(["a" for i in range(0, 65536 + 1)])
        self.provider.create_pull_request(self.repo, "title", body, "master", "new", False, [], Config())
        self.assertEqual(self.provider.bundle.get_pull_request_class.call_count, 1)
        self.assertEqual(self.provider.bundle.get_pull_request_class().call_count, 1)

    @patch("pyup.providers.gitlab.Provider._merge_merge_request")
    def test_create_pull_request_merge_when_pipeline_succeeds(self, merge_mock):
        config = Config()
        self.provider.create_pull_request(self.repo, "title", "body", "master", "new", False, [], config)
        self.assertEqual(merge_mock.call_count, 0)

        config.update_config({'gitlab': {'merge_when_pipeline_succeeds': True}})
        self.provider.create_pull_request(self.repo, "title", "body", "master", "new", False, [], config)
        self.assertEqual(merge_mock.call_count, 1)
        merge_mock.assert_called_once_with(ANY, config)

    def test_create_pull_request(self):
        self.provider.create_pull_request(self.repo, "title", "body", "master", "new", False, [], Config())
        self.assertEqual(self.provider.bundle.get_pull_request_class.call_count, 1)
        self.assertEqual(self.provider.bundle.get_pull_request_class().call_count, 1)

    def test_create_pull_request_with_label(self):
        self.provider.create_pull_request(self.repo, "title", "body", "master", "new", "some-label", [], Config())
        self.assertEqual(self.provider.bundle.get_pull_request_class.call_count, 1)
        self.assertEqual(self.provider.bundle.get_pull_request_class().call_count, 1)

    def test_create_issue(self):
        self.assertIsNot(self.provider.create_issue(self.repo, "title", "body"), False)

    def test_iter_issues(self):
        self.repo.mergerequests.list.return_value = [Mock(), Mock()]
        issues = list(self.provider.iter_issues(self.repo, Mock()))
        self.assertEqual(len(issues), 2)

    @patch("pyup.providers.gitlab.Gitlab")
    def test_ignore_ssl_should_be_default_false(self, gitlab_mock):
        provider = Provider(bundle=Mock())
        provider._api("foo")

        self.assertFalse(provider.ignore_ssl)
        gitlab_mock.assert_called_once_with(
            "https://gitlab.com", "foo", ssl_verify=True)

    @patch("pyup.providers.gitlab.Gitlab")
    def test_ignore_ssl(self, gitlab_mock):
        ignore_ssl = True
        provider = Provider(bundle=RequirementsBundle(), ignore_ssl=ignore_ssl)
        provider._api("foo")

        self.assertTrue(provider.ignore_ssl)
        gitlab_mock.assert_called_once_with(
            "https://gitlab.com", "foo", ssl_verify=(not ignore_ssl))
