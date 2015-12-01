# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
import logging
from .requirements import RequirementsBundle
from .providers.github import Provider as GithubProvider

logger = logging.getLogger(__name__)


class Bot(object):
    REQUIREMENTS_BASE_FILENAMES = [
        "requirements", "local", "base", "stage", "staging", "prod", "production", "dev", "development"
    ]

    REQUIREMENTS_FILE_ENDINGS = [
        None, "txt", "pip"
    ]

    def __init__(self, repo, user_token, bot_token=None,
                 provider=GithubProvider, bundle=RequirementsBundle):
        self.bot_token = bot_token
        self.req_bundle = bundle()
        self.provider = provider(bundle)
        self.user_token = user_token
        self.bot_token = bot_token
        self.fetched_files = []
        self.repo_name = repo

        self._user = None
        self._user_repo = None
        self._bot = None
        self._bot_repo = None

        self._pull_requests = None

    @property
    def user_repo(self):
        if self._user_repo is None:
            self._user_repo = self.provider.get_repo(self.user, self.repo)
        return self._user_repo

    @property
    def user(self):
        if self._user is None:
            self._user = self.provider.get_user(token=self.user_token)
        return self._user

    @property
    def bot(self):
        if self._bot is None:
            self._bot = self.provider.get_user(token=self.bot_token)
        return self._bot

    @property
    def bot_repo(self):
        if self._bot_repo is None:
            self._bot_repo = self.bot.get_repo(self.user_repo.full_name)
        return self._bot_repo

    @property
    def pull_requests(self):
        if self._pull_requests is None:
            self._pull_requests = [pr for pr in self.provider.iter_issues(repo=self.user_repo,
                                                                         creator=self.bot)]
        return self._pull_requests

    def update(self, branch=None, initial=True):

        if branch is None:
            branch = self.provider.get_default_branch(repo=self.user_repo)

        # print(self.gh_user_repo.full_name)

        self.get_all_requirements(branch=branch)

        for title, body, update_branch, updates in self.req_bundle.get_updates(inital=initial):
            pull_request = self.find_pull_request(title)
            if not pull_request:
                pull_request = self.create_pull_request(
                    base_branch=branch,
                    new_branch=update_branch,
                    title=title,
                    body=body,
                    updates=updates
                )

            if pull_request:
                for update in updates:
                    update.requirement.pull_request = pull_request
        return self.req_bundle

    def find_pull_request(self, title):
        for pr in self.pull_requests:
            if pr.title == title:
                return pr
        return False

    def create_pull_request(self, base_branch, new_branch, title, body, updates):

        # create new branch
        self.provider.create_branch(
            base_branch=base_branch,
            new_branch=new_branch,
            repo=self.user_repo
        )

        updated_files = {}
        for update in updates:

            if update.requirement_file.path in updated_files:
                sha = updated_files[update.requirement_file.path]["sha"]
                content = updated_files[update.requirement_file.path]["content"]
            else:
                sha = update.requirement_file.sha
                content = update.requirement_file.content

            content = update.requirement.update_content(content)
            new_sha = self.provider.create_commit(
                repo=self.user_repo,
                path=update.requirement_file.path,
                branch=new_branch,
                content=content,
                commit_message=update.commit_message,
                sha=sha
            )

            updated_files[update.requirement_file.path] = {"sha": new_sha, "content": content}

        return self.provider.create_pull_request(
            repo=self.bot_repo,
            title=title,
            body=body,
            base_branch=base_branch,
            new_branch=new_branch
        )

    def get_all_requirements(self, branch):
        for file_type, path in self.provider.iter_git_tree(branch=branch, repo=self.user_repo):
            if file_type == "blob":
                for candidate in self.requirement_candidates():
                    if path.endswith(candidate):
                        self.add_requirement_file(path)

    def add_requirement_file(self, path):
        if not self.req_bundle.has_file(path):
            req_file = self.provider.get_requirement_file(path=path, repo=self.user_repo)
            self.req_bundle.add(req_file)
            for other_file in req_file.other_files:
                self.add_requirement_file(other_file)

    @staticmethod
    def requirement_candidates():
        for ending in Bot.REQUIREMENTS_FILE_ENDINGS:
            for requirement in Bot.REQUIREMENTS_BASE_FILENAMES:
                yield ".".join([requirement, ending]) if ending else requirement
