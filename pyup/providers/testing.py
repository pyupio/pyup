# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from github import Github, GithubException
from collections import namedtuple
from ..errors import BranchExistsError, NoPermissionError
import time
import string
import random
from datetime import datetime

def random_string(n):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))

class Provider(object):
    def __init__(self, bundle):
        self.bundle = bundle

    def _api(self, token):
        pass

    def get_user(self, token):
        time.sleep(1)

    def get_repo(self, token, name):
        time.sleep(1)

    def get_default_branch(self, repo):
        time.sleep(1)

    def get_pull_request_permissions(self, user, repo):
        time.sleep(1.4)
        # maybe raise once in a while?

        #    raise NoPermissionError("Unable to add {login} as a collaborator on {repo}.".format(
        #        login=user.login,
        #        repo=repo.full_name
        #    ))

    def iter_git_tree(self, repo, branch):
        for _ in range(0, 300):
            yield "blob" if random.randint(0, 100) > 30 else "path", \
                  "requirements/" + random_string(12) + ".txt" if random.randint(0, 100) > 99 else random_string(12)

    def get_requirement_file(self, repo, path):
        time.sleep(1.3)
        # maybe return None once in a while?
        return self.bundle.get_requirement_file_class()(
                path=path,
                content=random_string(1500),
                sha=random_string(12)
        )

    def create_branch(self, repo, base_branch, new_branch):
        time.sleep(1)

    def create_commit(self, path, branch, commit_message, content, sha, repo, committer):
        time.sleep(2)
        return random_string(12)

    def get_committer_data(self, committer):
        time.sleep(0.5)
        return namedtuple("Committer", ["name", "email"])(name="Joanna", email="foo@bar.com")

    def create_pull_request(self, repo, title, body, base_branch, new_branch):
        time.sleep(1.7)
        return self.bundle.get_pull_request_class()(
                state="open",
                title=title,
                url="https://example.com/" + title,
                created_at=datetime.now()
            )

    def create_issue(self, repo, title, body):
        time.sleep(1.2)

    def iter_issues(self, repo, creator):
        time.sleep(0.7)
        for i in range(0, 30):
            yield self.bundle.get_pull_request_class()(
                state='open',
                title=random_string(12),
                url=random_string(12),
                created_at=datetime.now()
            )

