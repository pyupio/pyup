# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import logging

import requests_toolbelt
import stashy
from stashy.errors import NotFoundException, GenericException
from stashy.pullrequests import PullRequests
from stashy.repos import Repository

from pyup.errors import BranchExistsError, RepoDoesNotExistError

logger = logging.getLogger(__name__)


class BadTokenError(Exception):
    pass


class BadRepoNameError(Exception):
    pass


class Provider(object):
    name = "bitbucket_server"

    def __init__(self, bundle, intergration=False, url=None):
        self.bundle = bundle
        self.url = url
        if intergration:
            raise NotImplementedError(
                "BitbucketServer provider does not support integration mode yet."
            )

    @classmethod
    def is_same_user(cls, this, that):
        return this.login == that.login

    def _api(self, token):
        """
        Create a stashy connection object with the given token.
        :param token: should be in format: "user@token@base_url"
        :return: Stash object
        """
        parts = token.split("@")
        if len(parts) == 3:
            user = parts[0]
            token = parts[1]
            base_url = parts[2]
        else:
            raise BadTokenError(
                'Got token "{}": format should be "user@token@base_url" when using bitbucket_server'.format(
                    token
                )
            )
        return stashy.connect(base_url, user, token)

    def get_user(self, token):
        # TODO: Return some kind of Bitbucket Server User object
        return token.split("@")[0]

    def get_repo(self, token, name):
        """
        Returns stashy.repos Repository object when a repo was found.
        :param token: user token to perform API request to get additional information to build Repository object
        :param name: combined identifier of a repository with format: '<project>/<repo_slug>'
        """
        parts = name.split("/")
        if len(parts) == 2:
            project = parts[0]
            repo = parts[1]
            return Repository(
                slug=name,
                url="/projects/{}/repos/{}".format(project, repo),
                client=self._api(token)._client,
                parent=self._api(token).repos._parent,
            )
        else:
            logger.warning(
                "Please provide the repo in this format: <project>/<repo_slug>"
            )
            raise RepoDoesNotExistError()

    def get_default_branch(self, repo):
        """
        Get the default branch of a given repo
        :param repo: stashy.repo Repository object
        :return: the repository's default branch
        """
        return repo.default_branch

    def get_pull_request_permissions(self, user, repo):
        # TODO: IDK how this works on bitbucket
        return True

    def iter_git_tree(self, repo, branch):
        file_list = list(repo.files(at="refs/heads/" + branch))
        for file in file_list:
            yield "blob", file

    def get_file(self, repo, path, branch):
        """
        Returns tuple of file content and None.
        :param branch: name of the branch from which the contents of the file should be read
        :param path: path of the file
        :param repo: stashy.repo Repository object which will be browsed for the file
        """
        logger.info("Getting file at {} for branch {}".format(path, branch))
        try:
            # TODO: switch branch when not default list(repo.branches())
            file = list(repo.browse(path, at="refs/heads/" + branch))
            contentfile = ""
            for line in file:
                contentfile += line["text"] + "\n"

        except NotFoundException:
            logger.warning("Unable to get {}".format(path))
            return None, None
        else:
            return contentfile, None

    def create_and_commit_file(
        self, repo, path, branch, content, commit_message, committer
    ):
        """
        Workaround to commit a new or changed content to a path on a given branch in a given repository.
        :param branch: name of the branch
        :param commit_message: commit message
        :param content: content of the file
        :param path: path to the file
        :param repo:  stashy.repo Repository object
        :return: return code of the performed request
        """
        branches = list(repo.branches())
        latest_commit_id = ""
        for branch_dict in branches:
            if branch_dict.get("id").endswith(branch):
                latest_commit_id = branch_dict.get("latestCommit")

        data = requests_toolbelt.MultipartEncoder(
            fields={
                "content": content,
                "message": commit_message,
                "branch": branch,
                "sourceCommitId": latest_commit_id,
            }
        )
        # If we do not want to use a commit_id we need to delete the file we want to change
        # Workaround since StashClient put parses data into json which is not what we want here
        r = repo._client._session.put(
            repo._client._api_base + "/" + repo._url + "/browse/" + path,
            data=data,
            headers={"Content-type": data.content_type},
        )
        return r.status_code

    def get_requirement_file(self, repo, path, branch):
        """
        Retrieve the the contents of the file in given path in a given repository on a given branch.
        :param repo: stashy.repo Repository object
        :param path: path to file
        :param branch: name of the branch
        :return: requirements file object when found, None if not found
        """
        content, file_obj = self.get_file(repo, path, branch)
        if content is not None:
            return self.bundle.get_requirement_file_class()(path=path, content=content)
        return None

    def create_branch(self, repo, base_branch, new_branch):
        """
        Creates a new branch from a given base branch in a given repository.
        :param repo: stashy.repo Repository object
        :param base_branch: name of the branch from which the new branch will be created
        :param new_branch: name of the new branch
        """
        try:
            repo.create_branch(new_branch, base_branch)
        except GenericException:
            raise BranchExistsError(
                "The branch {} already exists on {}".format(new_branch, repo._slug)
            )

    def is_empty_branch(self, repo, base_branch, new_branch, prefix):
        """
        Compares the latest commits of two branches.
        :param repo:
        :param base_branch: string name of the base branch
        :param new_branch: string name of the new branch
        :param prefix: string branch prefix, default 'pyup-'
        :return: bool -- True if empty
        """
        # extra safeguard to make sure we are handling a bot branch here
        assert new_branch.startswith(prefix)
        branches = list(repo.branches())
        for branch in branches:
            if branch["displayID"] == base_branch:
                for newbranch in branches:
                    if newbranch["displayID"] == new_branch:
                        if branch["latestCommit"] == newbranch["latestCommit"]:
                            return True
        return False

    def delete_branch(self, repo, branch, prefix):
        """
        Deletes a given branch in a given repo when the name of the branch equals the given prefix.
        :param repo: stashy.repo Repository object
        :param branch: branch name
        :param prefix: string should be matched by the branch. Used to distinguish between pyup and user branches
        """
        # make sure that the name of the branch begins with pyup.
        assert branch.startswith(prefix)
        repo.delete_branch(branch)

    def create_commit(
        self, path, branch, commit_message, content, sha, repo, committer
    ):
        """
        Commit the contents of a file to a branch. Here we treat creating and updating the same way.
        :param path: path to the file
        :param branch: branch name where the commit is performed
        :param commit_message: message that is passed with the commit
        :param content: content of the file for the given path
        :param sha: unused parameter
        :param repo: stashy.repo Repository object
        :param committer: unused parameter
        :return: Return code of request
        """
        try:
            return self.create_and_commit_file(
                repo, path, branch, content, commit_message, committer
            )
        except GenericException as e:
            logger.warning("Unable to create commit.")
            logger.warning(e.args)

    def get_pull_request_committer(self, repo, pull_request):
        """
        Retrieve all participants from a given PR.
        :param repo: stashy.repo Repository object
        :param pull_request: stashy PullRequest object
        :return: list of participants
        """
        participant_names = []
        for i in range(len(repo.pull_requests.list())):
            number = repo.pull_requests.list()[i].get("id")
            if number == pull_request.number:
                participants = repo.pull_requests.list()[number].get("participants")
                for participant in participants:
                    participant_names.append(participant.get("user").get("name"))
        return participant_names

    def close_pull_request(self, bot_repo, user_repo, pull_request, comment, prefix):
        """
        Closes an open pull request and deletes the branch from which the PR was initiated.
        :param bot_repo: stashy.repo Repository object
        :param user_repo: stashy.repo Repository object
        :param pull_request: stashy PullRequest object
        :param comment: comment with which the PR is closed
        :param prefix: prefix in the source branch to distinguish between pyup PR's and user PR's
        """
        try:
            number = pull_request.number
            pull_request = bot_repo.pull_requests["{}".format(pull_request.number)]
            pull_request.comment(comment)
            source_branch = ""
            version = -1
            for pr in bot_repo.pull_requests.list():
                if pr.get("id") == number:
                    source_branch = pr.get("fromRef").get("displayId")
                    version = pr.get("version")
            pull_request.decline(version=version)
            # make sure that the name of the branch begins with pyup.
            assert source_branch.startswith(prefix)
            # Delete source branch
            self.delete_branch(user_repo, source_branch, prefix)
        except GenericException as e:
            logger.warning("Unable to close pull request.")
            logger.warning(e.args)

    def create_pull_request(
        self, repo, title, body, base_branch, new_branch, pr_label, assignees, **kwargs
    ):
        """
        Create a pull request from a given onto a given other branch.
        :param repo: stashy.repo Repository object
        :param title: title of the PR
        :param body: description of the PR
        :param base_branch: branch name
        :param new_branch: branch name
        :param pr_label: unused parameter
        :param assignees: user assigned to the PR
        :param kwargs: unused parameter
        :return: stashy PullRequest object
        """
        try:
            if len(body) >= 65536:
                logger.warning(
                    "PR body exceeds maximum length of 65536 chars, reducing"
                )
                body = body[: 65536 - 1]

            pr_object = PullRequests(repo._url + "/pull-requests", repo._client, repo)
            pr = pr_object.create(
                title, new_branch, base_branch, body, reviewers=assignees
            )

            return self.bundle.get_pull_request_class()(
                state=pr.get("state"),
                title=pr.get("title"),
                url=pr.get("links").get("self")[0].get("href"),
                created_at=pr.get("createdDate"),
                number=pr.get("id"),
                issue=False,
            )

        except GenericException as e:
            if e.args[0].startswith("409"):
                logger.warning(
                    "PR {title} from {base_branch}->{new_branch} already exists and is open.".format(
                        title=title, new_branch=new_branch, base_branch=base_branch
                    )
                )
                # Get the id from the exception:
                id_from_exception = (
                    e.data.get("errors")[0].get("existingPullRequest").get("id")
                )
                for pr in repo.pull_requests.list():
                    if pr.get("id") == id_from_exception:
                        return self.bundle.get_pull_request_class()(
                            state=pr.get("state"),
                            title=pr.get("title"),
                            url=pr.get("links").get("self")[0].get("href"),
                            created_at=pr.get("createdDate"),
                            number=pr.get("id"),
                            issue=False,
                        )

    def create_issue(self, repo, title, body):
        # TODO: Clarify if needed, since there are no issues for Bitbucket Server
        return iter([])

    def iter_issues(self, repo, creator):
        # TODO: Clarify if needed, since there are no issues for Bitbucket Server
        return iter([])
