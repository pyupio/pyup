# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from unittest import TestCase
from pyup.bot import Bot
from .test_pullrequest import pullrequest_factory
from pyup.updates import RequirementUpdate, InitialUpdate
from pyup.requirements import RequirementFile
from pyup.errors import NoPermissionError
from mock import Mock


def bot_factory(repo="foo/foo", user_token="foo", bot_token=None, bot_class=Bot):
    bot = bot_class(
        repo=repo,
        user_token=user_token,
        bot_token=bot_token,
    )

    bot.provider = Mock()
    return bot


class BotUserRepoTest(TestCase):
    def test_user_repo(self):
        bot = bot_factory()
        bot.provider.get_repo.return_value = "THE REPO"

        self.assertEqual(bot.user_repo, "THE REPO")


class BotUserTest(TestCase):
    def test_user(self):
        bot = bot_factory()
        bot.provider.get_user.return_value = "THE USER"

        self.assertEqual(bot.user, "THE USER")


class BotBotTest(TestCase):
    def test_bot_without_token(self):
        bot = bot_factory()
        bot.provider.get_user.return_value = "THE BOT"
        self.assertEqual(bot.bot, "THE BOT")

    def test_bot_with_token(self):
        bot = bot_factory(bot_token="the foo")
        bot.provider.get_user.return_value = "THE BOT"
        self.assertEqual(bot.bot, "THE BOT")


class BotBotRepoTest(TestCase):
    def test_bot_repo(self):
        bot = bot_factory()
        bot.provider.get_repo.return_value = "THE BOT REPO"
        self.assertEqual(bot.bot_repo, "THE BOT REPO")


class BotPullRequestsTest(TestCase):
    def test_empty(self):
        bot = bot_factory()
        bot.provider.iter_issues.return_value = []
        self.assertEqual(bot.pull_requests, [])

    def test_some_values(self):
        bot = bot_factory()
        bot.provider.iter_issues.return_value = ["foo", "bar"]
        self.assertEqual(bot.pull_requests, ["foo", "bar"])


class BotUpdateTest(TestCase):
    def test_branch_is_none(self):
        bot = bot_factory()
        bot.provider.get_default_branch.return_value = "the foo"
        bot.get_all_requirements = Mock()
        bot.apply_updates = Mock()
        self.assertEqual(bot.update(), [])

    def test_branch_is_set(self):
        bot = bot_factory()
        bot.get_all_requirements = Mock()
        bot.apply_updates = Mock()
        self.assertEqual(bot.update("the branch"), [])


class BotApplyUpdateTest(TestCase):
    def test_apply_update_pull_request_exists(self):
        the_requirement = Mock()
        the_pull = pullrequest_factory("The PR")

        bot = bot_factory()
        bot.provider.iter_issues.return_value = [the_pull]
        bot.req_bundle = Mock()
        update = RequirementUpdate(
            requirement_file="foo", requirement=the_requirement, commit_message="foo"
        )
        bot.req_bundle.get_updates.return_value = [
            ("The PR", "", "", [update])]
        bot.apply_updates("branch", True, True)

        self.assertEqual(the_requirement.pull_request, the_pull)

    def test_apply_update_pull_request_new(self):
        the_requirement = Mock()
        the_pull = pullrequest_factory("The PR")

        bot = bot_factory()
        bot.provider.iter_issues.return_value = []
        bot.req_bundle = Mock()
        update = RequirementUpdate(
            requirement_file="foo", requirement=the_requirement, commit_message="foo"
        )
        bot.req_bundle.get_updates.return_value = [("The PR", "", "", [update])]
        bot.commit_and_pull = Mock()
        bot.commit_and_pull.return_value = the_pull
        bot.apply_updates("branch", True, True)

        self.assertEqual(the_requirement.pull_request, the_pull)

    def test_apply_update_initial_empty(self):
        bot = bot_factory()
        bot.req_bundle.get_updates = Mock()
        bot.req_bundle.get_updates.return_value = []
        bot.provider.create_issue.return_value = None
        bot.apply_updates("branch", initial=True, pin_unpinned=False)

        create_issue_args_list = bot.provider.create_issue.call_args_list
        self.assertEqual(len(create_issue_args_list), 1)
        self.assertEqual(
            create_issue_args_list[0][1]["body"],
            InitialUpdate.get_empty_update_body()
        )
        self.assertEqual(
            create_issue_args_list[0][1]["title"],
            InitialUpdate.get_title()
        )

    def test_apply_update_initial_pr_still_open(self):
        initial_pr = pullrequest_factory(
            title=InitialUpdate.get_title(),
            state="open",
        )
        bot = bot_factory()
        bot.provider.iter_issues.return_value = [initial_pr]
        the_requirement = Mock()
        update = RequirementUpdate(
            requirement_file="foo", requirement=the_requirement, commit_message="foo"
        )
        bot.req_bundle.get_updates = Mock()
        bot.req_bundle.get_updates.return_value = [("The PR", "", "", [update])]

        bot.apply_updates("branch", initial=True, pin_unpinned=False)

        self.assertEqual(bot.provider.create_pull_request.called, False)


class BotCommitAndPullTest(TestCase):
    def test_multiple_updates_in_file(self):
        bot = bot_factory()
        bot.provider.create_branch = Mock()
        bot.provider.create_commit.side_effect = [
            "sha1", "sha2", "sha3"
        ]
        bot.create_pull_request = Mock()
        requirement = Mock()
        requirement.update_content.return_value = "new content"
        updates = [
            RequirementUpdate(
                requirement_file=RequirementFile(
                    path="foo.txt",
                    content='',
                    sha='abcd'
                ),
                requirement=requirement,
                commit_message="foo"
            ),
            RequirementUpdate(
                requirement_file=RequirementFile(
                    path="foo.txt",
                    content='',
                    sha='abcd'
                ),
                requirement=requirement,
                commit_message="foo"
            ),
            RequirementUpdate(
                requirement_file=RequirementFile(
                    path="baz.txt",
                    content='',
                    sha='xyz'
                ),
                requirement=requirement,
                commit_message="foo"
            )
        ]

        bot.commit_and_pull(True, "branch", "new branch", "repo", "", updates)

        self.assertEqual(bot.provider.create_commit.called, True)
        self.assertEqual(bot.provider.create_commit.call_count, 3)
        create_commit_calls = bot.provider.create_commit.call_args_list
        # we're looking for the sha here. Make sure that the sha got updated with the new content
        self.assertEqual(create_commit_calls[0][1]["sha"], "abcd")
        self.assertEqual(create_commit_calls[1][1]["sha"], "sha1")
        self.assertEqual(create_commit_calls[2][1]["sha"], "xyz")


class BotGetAllRequirementsTest(TestCase):
    def test_non_matching_file_not_added(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "foo.py"),  # not added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements("branch")
        self.assertEqual(bot.add_requirement_file.called, False)

    def test_requirement_not_in_path(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "this/that/bla/dev.pip"),  # not added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements("branch")
        self.assertEqual(bot.add_requirement_file.called, False)

    def test_file_not_ending_with_txt_or_pip(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "requirements/dev"),  # not added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements("branch")
        self.assertEqual(bot.add_requirement_file.called, False)

    def test_matching_file_deep(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "requirements/dev.txt"),  # added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements("branch")
        self.assertEqual(bot.add_requirement_file.called, True)

    def test_matching_file(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "requirements.txt"),  # added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements("branch")
        self.assertEqual(bot.add_requirement_file.called, True)

    def test_matching_file_pip(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "requirements.pip"),  # added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements("branch")
        self.assertEqual(bot.add_requirement_file.called, True)


class BotAddRequirementFileTest(TestCase):
    def test_file_is_in_path(self):
        bot = bot_factory()
        bot.req_bundle.has_file_in_path = Mock()
        bot.req_bundle.append = Mock()
        bot.req_bundle.has_file_in_path.return_value = True

        bot.add_requirement_file("path")

        self.assertEqual(bot.provider.get_requirement_file.called, False)
        self.assertEqual(bot.req_bundle.append.called, False)

    def test_file_not_found(self):
        bot = bot_factory()
        bot.req_bundle.has_file_in_path = Mock()
        bot.req_bundle.append = Mock()
        bot.provider.get_requirement_file.return_value = None
        bot.req_bundle.has_file_in_path.return_value = False

        bot.add_requirement_file("path")

        self.assertEqual(bot.provider.get_requirement_file.called, True)
        self.assertEqual(bot.req_bundle.append.called, False)

    def test_file_found_single(self):
        bot = bot_factory()
        bot.req_bundle.has_file_in_path = Mock()
        bot.req_bundle.append = Mock()
        req_file = RequirementFile("path", "")
        bot.provider.get_requirement_file.return_value = req_file

        bot.req_bundle.has_file_in_path.return_value = False

        bot.add_requirement_file("path")

        self.assertEqual(bot.provider.get_requirement_file.called, True)
        self.assertEqual(bot.req_bundle.append.called, True)

    def test_file_found_with_reference(self):
        bot = bot_factory()
        bot.req_bundle.has_file_in_path = Mock()
        bot.req_bundle.append = Mock()
        req_file = RequirementFile("path", "-r foo.txt")
        bot.provider.get_requirement_file.side_effect = [req_file, None]

        bot.req_bundle.has_file_in_path.return_value = False

        bot.add_requirement_file("path")

        self.assertEqual(bot.provider.get_requirement_file.called, True)
        self.assertEqual(bot.req_bundle.append.called, True)


class BotCreatePullRequestTest(TestCase):

    def test_plain(self):
        bot = bot_factory(bot_token=None)
        bot._bot_repo = "BOT REPO"
        bot._user_repo = "USER REPO"
        bot.create_pull_request("title", "body", "base_branch", "new_branch")
        self.assertEqual(bot.provider.create_pull_request.called, True)
        self.assertEqual(bot.provider.create_pull_request.call_args_list[0][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "USER REPO",
            "body": "body",
            "title": "title",
        })

    def test_bot_no_errors(self):
        bot = bot_factory(bot_token="foo")
        bot._bot_repo = "BOT REPO"
        bot._user_repo = "USER REPO"
        bot.create_pull_request("title", "body", "base_branch", "new_branch")
        self.assertEqual(bot.provider.create_pull_request.called, True)
        self.assertEqual(bot.provider.create_pull_request.call_args_list[0][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "BOT REPO",
            "body": "body",
            "title": "title",
        })
        self.assertEqual(bot.provider.get_pull_request_permissions.called, False)

    def test_bot_permission_error_resolved(self):
        bot = bot_factory(bot_token="foo")
        bot.provider.create_pull_request.side_effect = [NoPermissionError, "the foo"]
        bot._bot_repo = "BOT REPO"
        bot._user_repo = "USER REPO"
        bot.create_pull_request("title", "body", "base_branch", "new_branch")
        self.assertEqual(bot.provider.create_pull_request.called, True)
        self.assertEqual(bot.provider.create_pull_request.call_args_list[0][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "BOT REPO",
            "body": "body",
            "title": "title",
        })
        self.assertEqual(bot.provider.create_pull_request.call_args_list[1][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "BOT REPO",
            "body": "body",
            "title": "title",
        })

    def test_bot_permission_error_not_resolved(self):
        bot = bot_factory(bot_token="foo")
        bot.provider.create_pull_request.side_effect = [NoPermissionError, NoPermissionError]
        bot._bot_repo = "BOT REPO"
        bot._user_repo = "USER REPO"
        with self.assertRaises(NoPermissionError):
            bot.create_pull_request("title", "body", "base_branch", "new_branch")
        self.assertEqual(bot.provider.create_pull_request.called, True)
        self.assertEqual(bot.provider.create_pull_request.call_args_list[0][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "BOT REPO",
            "body": "body",
            "title": "title",
        })
        self.assertEqual(bot.provider.create_pull_request.call_args_list[1][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "BOT REPO",
            "body": "body",
            "title": "title",
        })
