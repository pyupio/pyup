# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
import time
from github import Github, GithubException
from collections import namedtuple
from ..errors import BranchExistsError, NoPermissionError


class Provider(object):
    def __init__(self, bundle):
        self.bundle = bundle

    def _api(self, token):
        return Github(token)

    def get_user(self, token):
        return self._api(token).get_user()

    def get_repo(self, token, name):
        return self._api(token).get_repo(name)

    def get_default_branch(self, repo):
        return repo.default_branch

    def get_pull_request_permissions(self, user, repo):
        try:
            return repo.add_to_collaborators(user.login)
        except GithubException:
            raise NoPermissionError("Unable to add {login} as a collaborator on {repo}.".format(
                login=user.login,
                repo=repo.full_name
            ))

    def iter_git_tree(self, repo, branch):
        for item in repo.get_git_tree(branch, recursive=True).tree:
            yield item.type, item.path

    def get_requirement_file(self, repo, path):
        try:
            contentfile = repo.get_contents(path)
            return self.bundle.get_requirement_file_class()(
                path=path,
                content=contentfile.decoded_content.decode('utf-8'),
                sha=contentfile.sha
            )
        except GithubException:
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
                time.sleep(i)
        raise e

    def get_committer_data(self, committer):
        email = None
        if committer.email is not None:
            email = committer.email
        else:
            for item in committer.get_emails():
                if item["primary"]:
                    email = item["email"]
        if email is None:
            raise NoPermissionError(
                "Unable to get {login}'s email adress. You may have to add the scope user:email"
                .format(login=committer.login)
            )
        return namedtuple("Committer", ["name", "email"])(name=committer.login, email=email)

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
            )
        except GithubException:
            raise NoPermissionError

    def create_issue(self, repo, title, body):
        return repo.create_issue(
            title=title,
            body=body,
        )

    def iter_issues(self, repo, creator):
        for issue in repo.get_issues(creator=creator.login):
            yield self.bundle.get_pull_request_class()(
                state=issue.state,
                title=issue.title,
                url=issue.html_url,
                created_at=issue.created_at,
            )
