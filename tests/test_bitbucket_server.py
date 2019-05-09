from unittest import TestCase

from mock import patch, Mock, MagicMock
from stashy.errors import NotFoundException, GenericException

from pyup.errors import BranchExistsError, RepoDoesNotExistError
from pyup.providers.bitbucket_server import Provider, BadTokenError, BadRepoNameError
from pyup.requirements import RequirementsBundle


class ProviderTest(TestCase):
    def setUp(self):
        self.provider = Provider(bundle=Mock())
        self.provider._api = Mock()
        self.repo = Mock()
        self.token = "foo@foo@http://example.com/stash"

    def test_not_implemented_error(self):
        with self.assertRaises(NotImplementedError):
            self.provider = Provider(bundle=Mock(), intergration=True)

    def test_is_same_user(self):
        this = Mock()
        this.login = "this"

        that = Mock()
        that.login = "that"

        self.assertFalse(Provider.is_same_user(this, that))

        that.login = "this"

        self.assertTrue(Provider.is_same_user(this, that))

    @patch("stashy.Stash")
    def test__api(self, bitbucket_server_mock):
        prov = Provider(bundle=RequirementsBundle())
        prov._api(self.token)
        bitbucket_server_mock.assert_called_once_with(
            "http://example.com/stash", "foo", "foo", verify=True
        )
        token = "foo"
        with self.assertRaises(BadTokenError):
            prov._api(token)

    def test_get_user(self):
        self.assertEqual(self.provider.get_user(self.token), "foo")

    def test_get_repo(self):
        self.provider._api(
            self.token
        )._client.core_api_path = "http://example.com/stash"
        self.assertIsNotNone(self.provider.get_repo(self.token, "project/slug"))

        with self.assertRaises(RepoDoesNotExistError):
            self.provider.get_repo(self.token, "slug")

    def test_get_default_branch(self):
        self.repo.default_branch = "foo"
        self.assertEqual(self.provider.get_default_branch(self.repo), "foo")

    def test_get_pull_request_permissions(self):
        # TODO: IDK how this works with bitbucket server
        self.assertEqual(
            True, self.provider.get_pull_request_permissions(Mock(), Mock())
        )

    def test_iter_git_tree(self):
        mocked_items = [{"type": "type", "path": "path"}]
        self.repo.files.return_value = mocked_items
        items = list(self.provider.iter_git_tree(self.repo, "some branch"))
        self.repo.files.assert_called_with(at="refs/heads/some branch")
        self.assertEqual([("blob", {"type": "type", "path": "path"})], items)

    def test_get_file(self):
        self.repo.browse.return_value = [{"text": ""}]
        content, obj = self.provider.get_file(self.repo, "path", "branch")
        self.assertIsNotNone(content)
        self.assertIsNone(obj)
        self.repo.browse.assert_called_with("path", at="refs/heads/branch")
        self.repo.browse.side_effect = NotFoundException(MagicMock())
        self.assertEqual(
            self.provider.get_file(self.repo, "path", "branch"), (None, None)
        )

    def test_create_and_commit_file(self):
        repo = Mock()
        repo.branches.return_value = [{"id": "pyup-branch"}]
        repo._client._api_base = ""
        repo._url = ""
        self.provider.create_and_commit_file(
            repo, "/foo.txt", "some-branch", "content", "some-message", None
        )
        repo._client._session.put.assert_called_once()

    def test_get_requirement_file(self):
        self.repo.browse.return_value = [{"text": ""}]
        req = self.provider.get_requirement_file(self.repo, "path", "branch")
        self.assertIsNotNone(req)
        self.provider.bundle.get_requirement_file_class.assert_called_once_with()
        self.assertEqual(
            self.provider.bundle.get_requirement_file_class().call_count, 1
        )

        self.provider.get_file = Mock(return_value=(None, None))
        req = self.provider.get_requirement_file(self.repo, "path", "branch")
        self.assertIsNone(req)

    def test_create_branch(self):
        self.provider.create_branch(self.repo, "base branch", "new branch")
        self.repo.create_branch.assert_called_with("new branch", "base branch")
        self.repo.create_branch.side_effect = GenericException(MagicMock())
        with self.assertRaises(BranchExistsError):
            self.provider.create_branch(self.repo, "base branch", "new branch")

    def test_is_empty_branch(self):
        with self.assertRaises(AssertionError):
            self.provider.is_empty_branch(self.repo, "master", "foo", prefix="bar")

        self.repo.branches.return_value = [
            {"displayID": "master", "latestCommit": "h4sh"},
            {"displayID": "pyup-foo", "latestCommit": "h4sh"},
        ]
        self.assertTrue(
            self.provider.is_empty_branch(
                self.repo, "master", "pyup-foo", prefix="pyup-"
            )
        )

        self.repo.branches.return_value = [
            {"displayID": "master", "latestCommit": "h4sh"},
            {"displayID": "pyup/foo", "latestCommit": "h4sh"},
        ]
        self.assertTrue(
            self.provider.is_empty_branch(
                self.repo, "master", "pyup/foo", prefix="pyup/"
            )
        )

        self.repo.branches.return_value = [
            {"displayID": "master", "latestCommit": "h4sh"},
            {"displayID": "pyup-foo", "latestCommit": "h4sh2"},
        ]
        self.assertFalse(
            self.provider.is_empty_branch(
                self.repo, "master", "pyup-foo", prefix="pyup-"
            )
        )

    def test_delete_branch(self):
        with self.assertRaises(AssertionError):
            self.provider.delete_branch(self.repo, "foo", prefix="bar")

        self.provider.delete_branch(self.repo, "pyup-foo", prefix="pyup-")
        self.repo.delete_branch.assert_called_with("pyup-foo")

        self.provider.delete_branch(self.repo, "pyup/foo", prefix="pyup/")
        self.repo.delete_branch.assert_called_with("pyup/foo")

    def test_create_commit(self):
        self.repo.branches.return_value = [{"id": "branch", "latestCommit": "h4sh"}]
        self.repo.browse.return_value = [{"text": ""}]
        self.repo._client._api_base = ""
        self.repo._url = ""
        self.provider.create_commit(
            "path", "branch", "commit", "content", "sha", self.repo, "com"
        )
        self.assertEqual(self.repo._client._session.put.call_count, 1)
        self.repo._client._session.put.side_effect = GenericException(MagicMock())
        self.assertEqual(
            None,
            self.provider.create_commit(
                "path", "branch", "commit", "content", "sha", self.repo, "com"
            ),
        )

    def test_get_pull_request_committer(self):
        mr = MagicMock()
        mr.changes = MagicMock()
        mr.source_branch = "pyup-bla"
        d = {"source_branch": mr.source_branch}
        p = [{"id": 0, "participants": [{"user": {"name": "alpha"}}]}]
        mr.changes.return_value = d
        mr.number = 0
        self.repo.pull_requests.list.return_value = p
        self.repo.pull_requests.list.get("id").return_value = p
        mr.participants = Mock()
        mr.participants.return_value = p
        committers = self.provider.get_pull_request_committer(self.repo, mr)
        self.assertEqual(committers, ["alpha"])

    def test_close_pull_request(self):
        pr = MagicMock()
        pr.number = 0
        # List of PR dictionaries
        prs = [{"id": 0, "version": "", "fromRef": {"displayId": "branch"}}]
        self.repo.pull_requests = MagicMock()
        self.repo.pull_requests.list.return_value = prs
        with self.assertRaises(AssertionError):
            self.provider.close_pull_request(
                self.repo, self.repo, pr, "comment", prefix="pyup-"
            )
        # List of PR dictionaries
        prs = [{"id": 0, "version": "", "fromRef": {"displayId": "pyup-branch"}}]
        self.repo.pull_requests.list.return_value = prs
        self.provider.close_pull_request(
            self.repo, self.repo, pr, "comment", prefix="pyup-"
        )
        self.assertEqual(self.repo.delete_branch.call_count, 1)
        # Test unable to close pull request
        self.repo.delete_branch.side_effect = GenericException(MagicMock())
        self.provider.close_pull_request(
            self.repo, self.repo, pr, "comment", prefix="pyup-"
        )

    def test_create_pull_request(self):
        self.repo._client = MagicMock()
        self.repo._client.core_api_path = "http://example.com/stash"
        self.repo._client.branches_api_path = "http://example.com/stash/rest/api/1.0/"
        self.repo._url = "http://example.com/stash"
        self.repo.get.return_value = MagicMock()
        body = "body" * 50000
        self.provider.create_pull_request(
            self.repo, "title", body, "master", "new", False, []
        )
        self.assertEqual(self.provider.bundle.get_pull_request_class.call_count, 1)
        self.assertEqual(self.provider.bundle.get_pull_request_class().call_count, 1)

        self.repo._client.side_effect = GenericException(MagicMock())
        self.provider.create_pull_request(
            self.repo, "title", "body", "master", "new", False, []
        )
        self.assertEqual(self.provider.bundle.get_pull_request_class.call_count, 3)
        self.assertEqual(self.provider.bundle.get_pull_request_class().call_count, 2)

    def test_create_issue(self):
        # TODO: Clarify if needed, since there are no issues for Bitbucket Server
        self.assertTrue(
            any(True for _ in iter([]))
            is any(True for _ in self.provider.create_issue(Mock(), "title", "body"))
        )

    def test_iter_issues(self):
        # TODO: Clarify if needed, since there are no issues for Bitbucket Server
        self.assertTrue(
            any(True for _ in iter([]))
            is any(True for _ in self.provider.iter_issues(Mock(), "creator"))
        )
