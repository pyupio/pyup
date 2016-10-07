# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from unittest import TestCase
from pyup.providers.github import Provider
from pyup.requirements import RequirementsBundle
from pyup import errors
from github import GithubException, UnknownObjectException
from mock import Mock, patch, PropertyMock


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

    @patch("pyup.providers.github.Github")
    def test_api(self, github_mock):
        prov = Provider(bundle=RequirementsBundle())
        prov._api("foo")
        github_mock.assert_called_once_with("foo")

    def test_get_user(self):
        self.provider.get_user("foo")
        self.provider._api().get_user.assert_called_once_with()

    def test_get_repo(self):
        self.provider.get_repo("token", "name")
        self.provider._api().get_repo.assert_called_once_with("name")

    def test_get_default_branch(self):

        self.repo.default_branch = "foo"
        self.assertEqual(
            self.provider.get_default_branch(self.repo),
            "foo"
        )

        p = PropertyMock(side_effect=UnknownObjectException(data="", status=1))
        type(self.repo).default_branch = p
        with self.assertRaises(errors.RepoDoesNotExistError):
            self.provider.get_default_branch(self.repo)

    def test_get_pull_request_permissions(self):
        user = Mock()
        user.login = "some-dude"
        self.provider.get_pull_request_permissions(user, self.repo)
        self.repo.add_to_collaborators.assert_called_once_with("some-dude")

        self.repo.add_to_collaborators.side_effect = GithubException(data="", status=1)
        with self.assertRaises(errors.NoPermissionError):
            self.provider.get_pull_request_permissions(user, self.repo)

    def test_iter_git_tree(self):
        mocked_items = [Mock(type="type", path="path")]
        self.repo.get_git_tree().tree = mocked_items
        items = list(self.provider.iter_git_tree(self.repo, "some branch"))
        self.assertEqual(items, [("type", "path")])

        self.repo.get_git_tree.side_effect = GithubException(data="", status=999)
        with self.assertRaises(GithubException):
            list(self.provider.iter_git_tree(self.repo, "some branch"))

    def test_get_file(self):

        content, obj = self.provider.get_file(self.repo, "path", "branch")
        self.assertIsNotNone(content)
        self.assertIsNotNone(obj)
        self.repo.get_contents.assert_called_with("/path", ref="branch")

        self.repo.get_contents.side_effect = GithubException(data="", status=1)
        content, obj = self.provider.get_file(self.repo, "path", "branch")
        self.assertIsNone(content)
        self.assertIsNone(obj)

    def test_get_requirement_file(self):

        req = self.provider.get_requirement_file(self.repo, "path", "branch")
        self.assertIsNotNone(req)
        self.provider.bundle.get_requirement_file_class.assert_called_once_with()
        self.assertEquals(self.provider.bundle.get_requirement_file_class().call_count, 1)

        self.provider.get_file = Mock(return_value = (None, None))
        req = self.provider.get_requirement_file(self.repo, "path", "branch")
        self.assertIsNone(req)

    def test_create_branch(self):
        self.provider.create_branch(self.repo, "base branch", "new branch")
        self.repo.get_git_ref.assert_called_once_with("heads/base branch")

        self.repo.get_git_ref.side_effect = GithubException(data="", status=1)
        with self.assertRaises(errors.BranchExistsError):
            self.provider.create_branch(self.repo, "base branch", "new branch")

    def test_is_empty_branch(self):
        with self.assertRaises(AssertionError):
            self.provider.is_empty_branch(self.repo, "master", "foo")

        self.repo.compare().total_commits = 0
        self.assertTrue(
            self.provider.is_empty_branch(self.repo, "master", "pyup-foo")
        )

        self.repo.compare().total_commits = 1
        self.assertFalse(
            self.provider.is_empty_branch(self.repo, "master", "pyup-foo")
        )

    def test_delete_branch(self):
        with self.assertRaises(AssertionError):
            self.provider.delete_branch(self.repo, "foo")

        self.provider.delete_branch(self.repo, "pyup-foo")
        self.repo.get_git_ref.assert_called_once_with("heads/pyup-foo")

    @patch("pyup.providers.github.time")
    def test_create_commit(self, time):
        self.repo.update_file.return_value = {"commit": Mock(), "content": Mock()}
        self.provider.get_committer_data = Mock(return_value = "foo@bar.com")
        self.provider.create_commit("path", "branch", "commit", "content", "sha", self.repo, "com")
        self.assertEquals(self.repo.update_file.call_count, 1)

        self.repo.update_file.side_effect = GithubException(data="", status=1)
        with self.assertRaises(GithubException):
            self.provider.create_commit("path", "branch", "commit", "content", "sha", self.repo,
                                        "com")

    def test_get_committer_data(self):
        committer = Mock()
        committer.email = "foo@bar.com"
        committer.login = "foo"
        data = self.provider.get_committer_data(committer)._identity
        self.assertEqual(data["name"], "foo")
        self.assertEqual(data["email"], "foo@bar.com")

        committer = Mock()
        committer.email = None
        committer.login = "foo"
        committer.get_emails.return_value = [{"primary": True, "email": "primary@bar.com"},]
        data = self.provider.get_committer_data(committer)._identity
        self.assertEqual(data["name"], "foo")
        self.assertEqual(data["email"], "primary@bar.com")

        committer = Mock()
        committer.email = None
        committer.login = "foo"
        committer.get_emails.return_value = []
        with self.assertRaises(errors.NoPermissionError):
            data = self.provider.get_committer_data(committer)

    def test_get_pull_request_committer(self):
        committ = Mock()
        committ.committer = "foo"
        pr = Mock()
        self.repo.get_pull().get_commits.return_value = [committ]
        data = self.provider.get_pull_request_committer(self.repo, pr)
        self.assertEqual(data, ["foo"])

        self.repo.get_pull.side_effect = UnknownObjectException(data="", status=1)
        data = self.provider.get_pull_request_committer(self.repo, pr)
        self.assertEqual(data, [])

    def test_close_pull_request(self):

        pr = Mock()
        pr.head.ref = "bla"
        self.repo.get_pull.return_value = pr
        with self.assertRaises(AssertionError):
            self.provider.close_pull_request(self.repo, self.repo, pr, "comment")

        pr.head.ref = "pyup-bla"
        self.provider.close_pull_request(self.repo, self.repo, pr, "comment")
        self.assertEquals(self.repo.get_git_ref().delete.call_count, 1)

        self.repo.get_pull.side_effect = UnknownObjectException(data="", status=1)
        data = self.provider.close_pull_request(self.repo, self.repo, Mock(), "comment")
        self.assertEqual(data, False)


    def test_create_pull_request(self):
        self.provider.create_pull_request(self.repo, "title", "body", "master", "new", False, [])
        self.assertEquals(self.provider.bundle.get_pull_request_class.call_count, 1)
        self.assertEquals(self.provider.bundle.get_pull_request_class().call_count, 1)

        self.repo.create_pull.side_effect = GithubException(data="", status=1)
        with self.assertRaises(errors.NoPermissionError):
            self.provider.create_pull_request(self.repo, "title", "body", "master", "new", False, [])

    def test_create_pull_request_with_label(self):
        self.provider.create_pull_request(self.repo, "title", "body", "master", "new", "some-label", [])
        self.assertEquals(self.provider.bundle.get_pull_request_class.call_count, 1)
        self.assertEquals(self.provider.bundle.get_pull_request_class().call_count, 1)

    def test_create_pull_request_with_assignees(self):
        self.provider.create_pull_request(self.repo, "title", "body", "master", "new",
                                          None, ["some-assignee"])
        self.assertEquals(self.provider.bundle.get_pull_request_class.call_count, 1)
        self.assertEquals(self.provider.bundle.get_pull_request_class().call_count, 1)
        self.assertEquals(self.repo.get_issue.call_count, 1)
        self.assertEquals(self.repo.get_issue().edit.call_count, 1)

    def test_create_issue(self):
        self.assertIsNot(self.provider.create_issue(self.repo, "title", "body"), False)

        self.repo.create_issue.side_effect = GithubException(data="", status=404)
        self.assertEqual(self.provider.create_issue(self.repo, "title", "body"), False)

        self.repo.create_issue.side_effect = GithubException(data="", status=999)
        with self.assertRaises(GithubException):
            self.assertEqual(self.provider.create_issue(self.repo, "title", "body"), False)

    def test_iter_issues(self):
        self.repo.get_issues.return_value = [Mock(), Mock()]
        issues = list(self.provider.iter_issues(self.repo, Mock()))
        self.assertEqual(len(issues), 2)

    def test_get_or_create_label(self):
        self.provider.get_or_create_label(self.repo, "foo-label")
        self.repo.get_label.assert_called_once_with(name="foo-label")
        self.repo.create_label.assert_not_called()

    def test_create_label(self):
        # label does not exist, need to create it
        self.repo.get_label.side_effect = UnknownObjectException(None, None)
        self.provider.get_or_create_label(self.repo, "another-label")
        self.repo.get_label.assert_called_once_with(name="another-label")
        self.repo.create_label.assert_called_once_with(name="another-label", color="1BB0CE")

    def test_create_label_fails(self):
        # label does not exist, need to create it
        self.repo.get_label.side_effect = UnknownObjectException(None, None)
        self.repo.create_label.side_effect = GithubException(None, None)
        label = self.provider.get_or_create_label(self.repo, "another-label")
        self.assertIsNone(label)
        self.repo.get_label.assert_called_once_with(name="another-label")
        self.repo.create_label.assert_called_once_with(name="another-label", color="1BB0CE")

