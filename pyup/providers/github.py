# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from github import Github
from django.core.urlresolvers import reverse
from django.conf import settings
from collections import namedtuple
from pyup.requirements import RequirementsBundle


class Provider(object):

    def __init__(self, bundle):
        self.bundle = bundle

    def get_user(self, token):
        return Github(token).get_user()

    def get_repo(self, user, name):
        return user.get_repo(name)

    def get_default_branch(self, repo):
        return repo.default_branch

    def iter_git_tree(self, repo, branch):
        for item in repo.get_git_tree(branch, recursive=True).tree:
            yield item.type, item.path

    def get_requirement_file(self, repo, path):
        contentfile = repo.get_contents(path)
        return self.bundle.get_requirement_class()(
            path=path,
            content=contentfile.decoded_content.decode('utf-8'),
            sha=contentfile.sha
        )

    def create_branch(self, repo, base_branch, new_branch):
        ref = repo.get_git_ref("/".join(["heads", base_branch]))
        repo.create_git_ref(ref="refs/heads/" + new_branch, sha=ref.object.sha)

    def create_commit(self, path, branch, commit_message, content, sha, repo):
        Committer = namedtuple("Committer", ["name", "email"])
        commit, new_file = repo.update_content(
            path=path,
            message=commit_message,
            content=content,
            branch=branch,
            sha=sha,
            committer=Committer(name="djangoupdater-bot", email="admin@djangoupdater.com"),
        )
        return new_file.sha

    def create_pull_request(self, repo, title, body, base_branch, new_branch):
        pr = repo.create_pull(
            title=title,
            body=body,
            base=base_branch,
            head=new_branch
        )
        return self.bundle.get_pull_request_class()(
            state=pr.state,
            title=pr.title,
            url=pr.url,
            created_at=pr.created_at,
        )

    def iter_issues(self, repo, creator):
        for issue in repo.get_issues(creator=creator.login):
            yield self.bundle.get_pull_request_class()(
                state=issue.state,
                title=issue.title,
                url=issue.url,
                created_at=issue.created_at,
            )
