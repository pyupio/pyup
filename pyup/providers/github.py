# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
import time
import logging
from github import Github, GithubException, UnknownObjectException
from collections import namedtuple
from ..errors import BranchExistsError, NoPermissionError, RepoDoesNotExistError

logger = logging.getLogger(__name__)


class Provider(object):
    def __init__(self, bundle):
        self.bundle = bundle

    @classmethod
    def is_same_user(cls, this, that):
        return this.login == that.login

    def _api(self, token):
        return Github(token)

    def get_user(self, token):
        return self._api(token).get_user()

    def get_repo(self, token, name):
        return self._api(token).get_repo(name)

    def get_default_branch(self, repo):
        try:
            return repo.default_branch
        except UnknownObjectException:
            # we can't use repo.name here because the repo object is lazy!
            # If we try to access one of the properties that is not completed,
            # we'll run into the next exception.
            logger.error("Repo does not exist", exc_info=True)
            raise RepoDoesNotExistError()

    def get_pull_request_permissions(self, user, repo):
        try:
            return repo.add_to_collaborators(user.login)
        except GithubException:
            msg = "Unable to add {login} as a collaborator on {repo}.".format(
                login=user.login,
                repo=repo.full_name
            )
            logger.error(msg, exc_info=True)
            raise NoPermissionError(msg)

    def iter_git_tree(self, repo, branch):
        try:
            for item in repo.get_git_tree(branch, recursive=True).tree:
                yield item.type, item.path
        except GithubException as e:
            # a 409 status code means the repo is empty. In this case we just
            # do nothing because this function shouldn't fail with an exception
            # just because there are no files to iterate over.
            if e.status != 409:
                raise

    def get_requirement_file(self, repo, path):
        try:
            contentfile = repo.get_contents(path)
            return self.bundle.get_requirement_file_class()(
                path=path,
                content=contentfile.decoded_content.decode('utf-8'),
                sha=contentfile.sha
            )
        except GithubException:
            msg = "Unable to get {path} on {repo}".format(
                path=path,
                repo=repo,
            )
            logger.error(msg, exc_info=True)
            return None

    def create_branch(self, repo, base_branch, new_branch):
        try:
            ref = repo.get_git_ref("/".join(["heads", base_branch]))
            repo.create_git_ref(ref="refs/heads/" + new_branch, sha=ref.object.sha)
        except GithubException:
            raise BranchExistsError("The branch {} already exists on {}".format(
                new_branch, repo.full_name
            ))

    def create_commit(self, path, branch, commit_message, content, sha, repo, committer):
        # there's a rare bug in the github API when committing too fast on really beefy
        # hardware with Gigabit NICs (probably because they do some async stuff).
        # If we encounter an error, the loop waits for 1/2/3 seconds before trying again.
        # If the loop reaches the 4th iteration, we give up and raise the error.
        for i in range(1, 4):
            try:
                commit, new_file = repo.update_content(
                    path=path,
                    message=commit_message,
                    content=content,
                    branch=branch,
                    sha=sha,
                    committer=self.get_committer_data(committer),
                )
                return new_file.sha
            except GithubException as e:
                if i == 3:
                    logger.error("Unable to create commit on {repo} for path {path}".format(
                        repo=repo,
                        path=path
                    ), exc_info=True)
                    raise e
                time.sleep(i)

    def get_committer_data(self, committer):
        email = None
        if committer.email is not None:
            email = committer.email
        else:
            for item in committer.get_emails():
                if item["primary"]:
                    email = item["email"]
        if email is None:
            msg = "Unable to get {login}'s email adress. " \
                  "You may have to add the scope user:email".format(login=committer.login)
            raise NoPermissionError(msg)
        return namedtuple("Committer", ["name", "email"])(name=committer.login, email=email)

    def get_pull_request_committer(self, repo, pull_request):
        try:
            return [
                commit.committer
                for commit in repo.get_pull(pull_request.number).get_commits()
            ]
        except UnknownObjectException:
            return []

    def close_pull_request(self, bot_repo, user_repo, pull_request, comment):
        try:
            pull_request = bot_repo.get_pull(pull_request.number)
            pull_request.create_issue_comment(comment)
            pull_request.edit(state="closed")
            # make sure that the name of the branch begins with pyup.
            assert pull_request.head.ref.startswith("pyup-")
            ref = user_repo.get_git_ref("/".join(["heads", pull_request.head.ref]))
            ref.delete()
        except UnknownObjectException:
            return False

    def create_pull_request(self, repo, title, body, base_branch, new_branch):
        try:
            pr = repo.create_pull(
                title=title,
                body=body,
                base=base_branch,
                head=new_branch
            )
            return self.bundle.get_pull_request_class()(
                state=pr.state,
                title=pr.title,
                url=pr.html_url,
                created_at=pr.created_at,
                number=pr.number,
                issue=False
            )
        except GithubException:
            msg = "Unable to create pull request on {repo}".format(repo=repo)
            logger.error(msg, exc_info=True)
            raise NoPermissionError(msg)

    def create_issue(self, repo, title, body):
        try:
            return repo.create_issue(
                title=title,
                body=body,
            )
        except GithubException as e:
            # a 404/410 status code means the repo has issues disabled, return
            # false instead of raising an exception for that
            if e.status in [404, 410]:
                return False
            raise

    def iter_issues(self, repo, creator):
        for issue in repo.get_issues(creator=creator.login):
            yield self.bundle.get_pull_request_class()(
                state=issue.state,
                title=issue.title,
                url=issue.html_url,
                created_at=issue.created_at,
                number=issue.number,
                issue=issue.pull_request is not None,
            )
