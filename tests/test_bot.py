# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from unittest import TestCase
from pyup.bot import Bot
from .test_pullrequest import pullrequest_factory
from pyup.updates import RequirementUpdate, InitialUpdate
from pyup.requirements import RequirementFile
from pyup.errors import NoPermissionError
from pyup.config import RequirementConfig
from mock import Mock, patch


def bot_factory(repo="foo/foo", user_token="foo", bot_token=None, bot_class=Bot, prs=list()):
    bot = bot_class(
        repo=repo,
        user_token=user_token,
        bot_token=bot_token,
    )
    bot._fetched_prs = True
    bot.req_bundle.pull_requests = prs
    bot.provider = Mock()
    bot.config.update({
        "close_prs": True,
        "pin": True,
        "branch": "master",
        "search": True
    })
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

    def test_iter_issues_called(self):
        bot = bot_factory()
        bot._fetched_prs = False
        bot.provider.iter_issues = Mock(return_value=[])
        bot.pull_requests
        self.assertEquals(bot.provider.iter_issues.call_count, 1)


class BotRepoConfigTest(TestCase):

    def test_fetches_file_success(self):
        bot = bot_factory()
        bot.provider.get_file.return_value = "foo: bar", None
        self.assertEqual(bot.get_repo_config(bot.user_repo), {"foo": "bar"})

    def test_yaml_error(self):
        bot = bot_factory()
        bot.provider.get_file.return_value = "foo: bar: baz: fii:", None
        self.assertEqual(bot.get_repo_config(bot.user_repo), None)

    def test_fetches_file_error(self):
        bot = bot_factory()
        bot.provider.get_file.return_value = None, None
        self.assertEqual(bot.get_repo_config(bot.user_repo), None)


class BotConfigureTest(TestCase):

    def test_kwargs(self):
        bot = bot_factory()
        bot.provider.get_file.return_value = None, None
        bot.configure(branch="bogus-branch", pin="bogus-pin", close_prs="bogus-close")
        self.assertEqual(bot.config.branch, "bogus-branch")
        self.assertEqual(bot.config.pin, "bogus-pin")
        self.assertEqual(bot.config.close_prs, "bogus-close")

    def test_file(self):
        bot = bot_factory()
        bot.provider.get_file.return_value = "close_prs: bogus-close\nbranch: bogus-branch", None
        bot.configure()
        self.assertEqual(bot.config.branch, "bogus-branch")
        self.assertEqual(bot.config.close_prs, "bogus-close")

    def test_numeric_branch(self):
        bot = bot_factory()
        bot.provider.get_file.return_value = "branch: 2.0\n", None
        bot.configure()
        self.assertEqual(bot.config.branch, "2.0")


class BotUpdateTest(TestCase):
    def test_branch_is_none(self):
        bot = bot_factory()
        bot.provider.get_default_branch.return_value = "the foo"
        bot.provider.get_file.return_value = None, None
        bot.get_all_requirements = Mock()
        bot.apply_updates = Mock()
        bot.update()
        self.assertEqual(bot.config.branch, "the foo")

    def test_branch_is_set(self):
        bot = bot_factory()
        bot.get_all_requirements = Mock()
        bot.apply_updates = Mock()
        bot.provider.get_file.return_value = None, None
        bot.update(branch="the branch")
        self.assertEqual(bot.config.branch, "the branch")


class BotApplyUpdateTest(TestCase):
    def test_apply_update_pull_request_exists(self):
        the_requirement = Mock()
        the_pull = pullrequest_factory("The PR")

        bot = bot_factory(prs=[the_pull])
        bot.req_bundle.get_updates = Mock()
        update = RequirementUpdate(
            requirement_file="foo", requirement=the_requirement, commit_message="foo"
        )
        bot.req_bundle.get_updates.return_value = [
            ("The PR", "", "", [update])]
        bot.apply_updates(initial=True, scheduled=False)

        self.assertEqual(the_requirement.pull_request, the_pull)

    def test_updates_empty(self):
        bot = bot_factory()
        bot.create_issue = Mock()
        bot.req_bundle.get_updates = Mock(side_effect=IndexError)
        bot.apply_updates(initial=True, scheduled=False)
        bot.create_issue.assert_called_once_with(
            title=InitialUpdate.get_title(),
            body=InitialUpdate.get_empty_update_body()
        )

    def test_apply_update_pull_request_new(self):
        the_requirement = Mock()
        the_pull = pullrequest_factory("The PR")

        bot = bot_factory(prs=[the_pull])
        bot.req_bundle.get_updates = Mock()
        update = RequirementUpdate(
            requirement_file="foo", requirement=the_requirement, commit_message="foo"
        )
        bot.req_bundle.get_updates.return_value = [("The PR", "", "", [update])]
        bot.commit_and_pull = Mock()
        bot.commit_and_pull.return_value = the_pull
        bot.apply_updates(initial=True, scheduled=False)

        self.assertEqual(the_requirement.pull_request, the_pull)

    def test_close_stall_prs_called(self):
        the_requirement = Mock()
        the_pull = pullrequest_factory("The PR")
        bot = bot_factory(prs=[])
        bot.close_stale_prs = Mock()
        bot.req_bundle.get_updates = Mock()
        update = RequirementUpdate(
            requirement_file="foo", requirement=the_requirement, commit_message="foo"
        )
        bot.req_bundle.get_updates.return_value = [("The PR", "", "", [update])]
        bot.commit_and_pull = Mock()
        bot.commit_and_pull.return_value = the_pull
        bot.apply_updates(initial=False, scheduled=False)

        self.assertEqual(the_requirement.pull_request, the_pull)
        bot.close_stale_prs.assert_called_once_with(update=update, pull_request=the_pull,
                                                    scheduled=False)

    def test_close_stall_prs_called_only_once_on_scheduled_run(self):
        the_requirement = Mock()
        the_pull = pullrequest_factory("Scheduled")
        bot = bot_factory(prs=[])
        bot.close_stale_prs = Mock()
        bot.req_bundle.get_updates = Mock()
        update = RequirementUpdate(
            requirement_file="foo", requirement=the_requirement, commit_message="foo"
        )
        bot.req_bundle.get_updates.return_value = [("The PR", "", "", [update, update])]
        bot.commit_and_pull = Mock()
        bot.commit_and_pull.return_value = the_pull
        bot.apply_updates(initial=False, scheduled=True)

        self.assertEqual(the_requirement.pull_request, the_pull)
        bot.close_stale_prs.assert_called_once_with(update=update, pull_request=the_pull,
                                                    scheduled=True)

    def test_apply_update_initial_empty(self):
        bot = bot_factory()
        bot.req_bundle.get_updates = Mock()
        bot.req_bundle.get_updates.return_value = [("", "", "", [])]
        bot.provider.create_issue.return_value = None
        bot.apply_updates(initial=True, scheduled=False)

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
        bot = bot_factory(prs=[initial_pr])
        the_requirement = Mock()
        update = RequirementUpdate(
            requirement_file="foo", requirement=the_requirement, commit_message="foo"
        )
        bot.req_bundle.get_updates = Mock()
        bot.req_bundle.get_updates.return_value = [("The PR", "", "", [update])]

        bot.apply_updates(initial=True, scheduled=False)

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

        bot.commit_and_pull(True, "branch", "new branch", "repo", "", updates, False, [])

        self.assertEqual(bot.provider.create_commit.called, True)
        self.assertEqual(bot.provider.create_commit.call_count, 2)
        create_commit_calls = bot.provider.create_commit.call_args_list
        # we're looking for the sha here. Make sure that the sha got updated with the new content
        self.assertEqual(create_commit_calls[0][1]["sha"], "abcd")
        self.assertEqual(create_commit_calls[1][1]["sha"], "xyz")

    def test_create_branch_fails(self):
        bot = bot_factory()
        bot.create_branch = Mock(return_value=False)
        self.assertEqual(bot.commit_and_pull(None, None, None, None, None, None, None, None), None)


class CreateBranchTest(TestCase):

    def test_success(self):
        bot = bot_factory()
        self.assertEqual(bot.create_branch("master", "new-branch", delete_empty=False), True)
        bot.provider.create_branch.assert_called_once_with(
            base_branch="master", new_branch="new-branch", repo=bot.user_repo)

    def test_error_dont_delete(self):
        from pyup.errors import BranchExistsError
        bot = bot_factory()
        bot.provider.create_branch.side_effect = BranchExistsError
        self.assertEqual(bot.create_branch("master", "new-branch", delete_empty=False), False)
        bot.provider.is_empty_branch.assert_not_called()
        bot.provider.delete_branch.assert_not_called()

    def test_error_delete(self):
        from pyup.errors import BranchExistsError
        bot = bot_factory()
        bot.provider.create_branch.side_effect = BranchExistsError
        bot.provider.is_empty_branch.return_value = True
        bot.create_branch("master", "new-branch", delete_empty=True)

        self.assertEquals(bot.provider.is_empty_branch.call_count, 1)
        self.assertEquals(bot.provider.delete_branch.call_count, 1)
        self.assertEqual(len(bot.provider.create_branch.mock_calls), 2)

    def test_branch_not_empty(self):
        from pyup.errors import BranchExistsError
        bot = bot_factory()
        bot.provider.create_branch.side_effect = BranchExistsError
        bot.provider.is_empty_branch.return_value = False
        bot.create_branch("master", "new-branch", delete_empty=True)

        self.assertEquals(bot.provider.is_empty_branch.call_count, 1)
        bot.provider.delete_branch.assert_not_called()
        self.assertEqual(len(bot.provider.create_branch.mock_calls), 1)



class BotGetAllRequirementsTest(TestCase):
    def test_non_matching_file_not_added(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "foo.py"),  # not added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements()
        self.assertEqual(bot.add_requirement_file.called, False)

    def test_requirement_not_in_path(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "this/that/bla/dev.pip"),  # not added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements()
        self.assertEqual(bot.add_requirement_file.called, False)

    def test_file_not_ending_with_txt_or_pip(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "requirements/dev"),  # not added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements()
        self.assertEqual(bot.add_requirement_file.called, False)

    def test_matching_file_deep(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "requirements/dev.txt"),  # added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements()
        self.assertEqual(bot.add_requirement_file.called, True)

    def test_matching_file(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "requirements.txt"),  # added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements()
        self.assertEqual(bot.add_requirement_file.called, True)

    def test_matching_file_pip(self):
        bot = bot_factory()
        bot.provider.iter_git_tree.return_value = ("blob", "requirements.pip"),  # added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements()
        self.assertEqual(bot.add_requirement_file.called, True)

    def test_no_search(self):
        bot = bot_factory()
        bot.config.search = False
        bot.provider.iter_git_tree.return_value = ("blob", "requirements.pip"),  # added
        bot.add_requirement_file = Mock()
        bot.get_all_requirements()
        self.assertEqual(bot.add_requirement_file.called, False)

    def test_requirement_in_config(self):
        bot = bot_factory()
        bot.config.search = False
        bot.config.requirements = [
            RequirementConfig(path="foo.txt")
        ]
        bot.add_requirement_file = Mock()
        bot.get_all_requirements()
        self.assertEqual(bot.add_requirement_file.called, True)
        bot.add_requirement_file.assert_called_once_with("foo.txt")


class BotAddRequirementFileTest(TestCase):
    def test_file_is_in_path(self):
        bot = bot_factory()
        bot.req_bundle.has_file_in_path = Mock()
        bot.req_bundle.append = Mock()
        bot.req_bundle.has_file_in_path.return_value = True

        bot.add_requirement_file("path",)

        self.assertEqual(bot.provider.get_requirement_file.called, False)
        self.assertEqual(bot.req_bundle.append.called, False)

    def test_file_not_found(self):
        bot = bot_factory()
        bot.req_bundle.has_file_in_path = Mock()
        bot.req_bundle.append = Mock()
        bot.provider.get_requirement_file.return_value = None
        bot.req_bundle.has_file_in_path.return_value = False

        bot.add_requirement_file("path",)

        self.assertEqual(bot.provider.get_requirement_file.called, True)
        self.assertEqual(bot.req_bundle.append.called, False)

    def test_file_found_single(self):
        bot = bot_factory()
        bot.req_bundle.has_file_in_path = Mock()
        bot.req_bundle.append = Mock()
        req_file = RequirementFile("path", "")
        bot.provider.get_requirement_file.return_value = req_file

        bot.req_bundle.has_file_in_path.return_value = False

        bot.add_requirement_file("path",)

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


class BotCanPullTest(TestCase):

    def test_valid_schedule_but_unscheduled_run(self):
        bot = bot_factory(bot_token=None)
        bot.config.is_valid_schedule = Mock()
        bot.config.is_valid_schedule.return_value = True
        self.assertFalse(bot.can_pull(False))

    def test_valid_schedule_and_scheduled_run(self):
        bot = bot_factory(bot_token=None)
        bot.config.is_valid_schedule = Mock()
        bot.config.is_valid_schedule.return_value = True
        self.assertTrue(bot.can_pull(True))

    def test_no_schedule(self):
        bot = bot_factory(bot_token=None)
        bot.config.is_valid_schedule = Mock()
        bot.config.is_valid_schedule.return_value = False
        self.assertTrue(bot.can_pull(False))
        self.assertTrue(bot.can_pull(True))


class BotCreatePullRequestTest(TestCase):

    def test_plain(self):
        bot = bot_factory(bot_token=None)
        bot._bot_repo = "BOT REPO"
        bot._user_repo = "USER REPO"
        bot.create_pull_request("title", "body", "base_branch", "new_branch", False, [])
        self.assertEqual(bot.provider.create_pull_request.called, True)
        self.assertEqual(bot.provider.create_pull_request.call_args_list[0][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "USER REPO",
            "body": "body",
            "title": "title",
            "pr_label": False,
            "assignees": []
        })

    def test_bot_no_errors(self):
        bot = bot_factory(bot_token="foo")
        bot._bot_repo = "BOT REPO"
        bot._user_repo = "USER REPO"
        bot.create_pull_request("title", "body", "base_branch", "new_branch", False, [])
        self.assertEqual(bot.provider.create_pull_request.called, True)
        self.assertEqual(bot.provider.create_pull_request.call_args_list[0][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "BOT REPO",
            "body": "body",
            "title": "title",
            "pr_label": False,
            "assignees": []
        })
        self.assertEqual(bot.provider.get_pull_request_permissions.called, False)

    def test_bot_permission_error_resolved(self):
        bot = bot_factory(bot_token="foo")
        bot.provider.create_pull_request.side_effect = [NoPermissionError, "the foo"]
        bot._bot_repo = "BOT REPO"
        bot._user_repo = "USER REPO"
        bot.create_pull_request("title", "body", "base_branch", "new_branch", False, [])
        self.assertEqual(bot.provider.create_pull_request.called, True)
        self.assertEqual(bot.provider.create_pull_request.call_args_list[0][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "BOT REPO",
            "body": "body",
            "title": "title",
            "pr_label": False,
            "assignees": []
        })
        self.assertEqual(bot.provider.create_pull_request.call_args_list[1][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "BOT REPO",
            "body": "body",
            "title": "title",
            "pr_label": False,
            "assignees": []
        })

    def test_bot_permission_error_not_resolved(self):
        bot = bot_factory(bot_token="foo")
        bot.provider.create_pull_request.side_effect = [NoPermissionError, NoPermissionError]
        bot._bot_repo = "BOT REPO"
        bot._user_repo = "USER REPO"
        with self.assertRaises(NoPermissionError):
            bot.create_pull_request("title", "body", "base_branch", "new_branch", False, [])
        self.assertEqual(bot.provider.create_pull_request.called, True)
        self.assertEqual(bot.provider.create_pull_request.call_args_list[0][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "BOT REPO",
            "body": "body",
            "title": "title",
            "pr_label": False,
            "assignees": []
        })
        self.assertEqual(bot.provider.create_pull_request.call_args_list[1][1], {
            "base_branch": "base_branch",
            "new_branch": "new_branch",
            "repo": "BOT REPO",
            "body": "body",
            "title": "title",
            "pr_label": False,
            "assignees": []
        })


class CloseStalePRsTestCase(TestCase):

    def setUp(self):

        self.pr = Mock()
        self.pr.title = "First PR"
        self.pr.number = 100
        self.pr.type = "update"
        self.pr.is_update = True
        self.pr.is_initial = False

        self.update = Mock()
        self.update.requirement.key = "some-req"

        self.other_pr = Mock()
        self.other_pr.type = "update"
        self.other_pr.is_open = True
        self.other_pr.title = "Second PR"
        self.other_pr.requirement = "some-req"
        self.other_pr.is_update = True
        self.other_pr.is_initial = False

    def test_scheduled_closing_scheduled(self):
        self.pr.is_scheduled = True
        self.other_pr.is_scheduled = True
        bot = bot_factory(bot_token="foo", prs=[self.other_pr])
        commiter = Mock()
        bot.provider.get_pull_request_committer.return_value = [commiter]

        bot.close_stale_prs(self.update, self.pr, True)

        bot.provider.get_pull_request_committer.assert_called_once_with(bot.user_repo,
                                                                        self.other_pr)

    def test_scheduled_closing_update(self):
        self.pr.is_scheduled = True
        bot = bot_factory(bot_token="foo", prs=[self.other_pr])
        commiter = Mock()
        bot.provider.get_pull_request_committer.return_value = [commiter]

        bot.close_stale_prs(self.update, self.pr, True)

        bot.provider.get_pull_request_committer.assert_called_once_with(bot.user_repo,
                                                                        self.other_pr)


    def test_no_bot_token(self):
        bot = bot_factory()
        self.pr.type = Mock()
        bot.close_stale_prs(self.update, self.pr, False)

        self.assertEquals(self.pr.type.call_count, 0)

    def test_no_pull_requests(self):
        bot = bot_factory(bot_token="foo")

        bot.close_stale_prs(self.update, self.pr, False)

        bot.provider.get_pull_request_committer.assert_not_called()

    def test_close_success(self):
        bot = bot_factory(bot_token="foo", prs=[self.other_pr])
        commiter = Mock()
        bot.provider.get_pull_request_committer.return_value = [commiter]

        bot.close_stale_prs(self.update, self.pr, False)

        bot.provider.get_pull_request_committer.assert_called_once_with(bot.user_repo, self.other_pr)
        bot.provider.close_pull_request.assert_called_once_with(
            bot_repo=bot.bot_repo,
            user_repo=bot.user_repo,
            pull_request=self.other_pr,
            comment="Closing this in favor of #100"
        )

    def test_wrong_pr_type(self):
        bot = bot_factory(bot_token="foo", prs=[self.other_pr])
        self.other_pr.is_update = False
        commiter = Mock()
        bot.provider.get_pull_request_committer.return_value = [commiter]

        bot.close_stale_prs(self.update, self.pr, False)

        bot.provider.get_pull_request_committer.assert_not_called()
        bot.provider.close_pull_request.assert_not_called()

    def test_pr_closed(self):
        bot = bot_factory(bot_token="foo", prs=[self.other_pr])
        self.other_pr.is_open = False
        commiter = Mock()
        bot.provider.get_pull_request_committer.return_value = [commiter]

        bot.close_stale_prs(self.update, self.pr, False)

        bot.provider.get_pull_request_committer.assert_not_called()
        bot.provider.close_pull_request.assert_not_called()

    def test_same_title(self):
        bot = bot_factory(bot_token="foo", prs=[self.other_pr])
        self.other_pr.title = "First PR"
        commiter = Mock()
        bot.provider.get_pull_request_committer.return_value = [commiter]

        bot.close_stale_prs(self.update, self.pr, False)

        bot.provider.get_pull_request_committer.assert_not_called()
        bot.provider.close_pull_request.assert_not_called()

    def test_requirement_doesnt_match(self):
        bot = bot_factory(bot_token="foo", prs=[self.other_pr])
        self.other_pr.requirement = "other-req"
        commiter = Mock()
        bot.provider.get_pull_request_committer.return_value = [commiter]

        bot.close_stale_prs(self.update, self.pr, False)

        bot.provider.get_pull_request_committer.assert_not_called()
        bot.provider.close_pull_request.assert_not_called()

    def test_more_than_one_committer(self):
        bot = bot_factory(bot_token="foo", prs=[self.other_pr])
        commiter, commiter1 = Mock(), Mock()
        bot.provider.get_pull_request_committer.return_value = [commiter, commiter1]

        bot.close_stale_prs(self.update, self.pr, False)

        bot.provider.get_pull_request_committer.assert_called_once_with(bot.user_repo, self.other_pr)
        bot.provider.close_pull_request.assert_not_called()

    def test_committer_is_not_bot_user(self):
        bot = bot_factory(bot_token="foo", prs=[self.other_pr])
        commiter = Mock()
        bot.provider.get_pull_request_committer.return_value = [commiter]
        bot.provider.is_same_user.return_value = False

        bot.close_stale_prs(self.update, self.pr, False)

        bot.provider.get_pull_request_committer.assert_called_once_with(bot.user_repo, self.other_pr)
        bot.provider.close_pull_request.assert_not_called()


class ConflictingUpdateTest(TestCase):

    def test_no_conflict(self):
        bot = bot_factory()
        update1 = Mock()
        update1.requirement.key = "pkg"
        update1.requirement.latest_version_within_specs = "1.0"

        update2 = Mock()
        update2.requirement.key = "other-pkg"
        update1.requirement.latest_version_within_specs = "1.0"

        bot.iter_updates = Mock(return_value=[
            [None, None, None, [update1]],
            [None, None, None, [update2]]
        ])

        self.assertFalse(
            bot.has_conflicting_update(update1)
        )

    def test_has_conflict(self):
        bot = bot_factory()
        update1 = Mock()
        update1.requirement.key = "pkg"
        update1.requirement.latest_version_within_specs = "1.0"

        update2 = Mock()
        update2.requirement.key = "pkg"
        update1.requirement.latest_version_within_specs = "1.4"

        bot.iter_updates = Mock(return_value=[
            [None, None, None, [update1]],
            [None, None, None, [update2]]
        ])

        self.assertTrue(
            bot.has_conflicting_update(update1)
        )

    def test_fool_loop(self):
        bot = bot_factory()
        update1 = Mock()
        update1.requirement.key = "google-api-python-client"
        update1.requirement.latest_version_within_specs = "1.5.3"
        update1.commit_message = "Update google-api-python-client from 1.5.1 to 1.5.3"

        update2 = Mock()
        update2.requirement.key = "google-api-python-client"
        update2.requirement.latest_version_within_specs = "1.5.3"
        update2.commit_message = "Pin google-api-python-client to latest version 1.5.3"

        bot.iter_updates = Mock(return_value=[
            [None, None, None, [update1]],
            [None, None, None, [update2]]
        ])

        self.assertTrue(
            bot.has_conflicting_update(update1)
        )
