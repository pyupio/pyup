# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
import logging
import yaml
from .requirements import RequirementsBundle
from .providers.github import Provider as GithubProvider
from .errors import NoPermissionError, BranchExistsError, ConfigError
from .config import Config

logger = logging.getLogger(__name__)


class Bot(object):
    def __init__(self, repo, user_token, bot_token=None,
                 provider=GithubProvider, bundle=RequirementsBundle, config=Config,
                 integration=False, provider_url=None, ignore_ssl=False):
        self.req_bundle = bundle()
        self.provider = provider(self.req_bundle, integration, provider_url, ignore_ssl)
        self.user_token = user_token
        self.bot_token = bot_token
        self.fetched_files = []
        self.repo_name = repo

        self._user = None
        self._user_repo = None
        self._bot = None
        self._bot_repo = None
        self.config = config()
        self.write_config = {}

        self._fetched_prs = False

        self.integration = integration

    @property
    def user_repo(self):
        if self._user_repo is None:
            self._user_repo = self.provider.get_repo(token=self.user_token, name=self.repo_name)
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
            self._bot_repo = self.provider.get_repo(token=self.bot_token, name=self.repo_name)
        return self._bot_repo

    @property
    def pull_requests(self):
        if not self._fetched_prs:
            self.req_bundle.pull_requests = [
                pr for pr in self.provider.iter_issues(
                    repo=self.user_repo,
                    creator=self.bot if self.bot_token else self.user
                )
                if pr.is_valid
            ]
            self._fetched_prs = True
        return self.req_bundle.pull_requests

    def get_repo_config(self, repo, branch=None, create_error_issue=True):
        branch = self.config.branch if branch is None else branch
        content, _ = self.provider.get_file(repo, ".pyup.yml", branch)
        if content is not None:
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError as e:
                err = ConfigError(content=content, error=e.__str__())
                if create_error_issue:
                    issue_title = "Invalid .pyup.yml detected"
                    # check that there's not an open issue already
                    if issue_title not in [pr.title for pr in self.pull_requests if pr.is_open]:
                        self.create_issue(
                            title=issue_title,
                            body="The bot encountered an error in your `.pyup.yml` config file:\n\n"
                                 "```{error}\n```\n\n"
                                 "You can validate it with this "
                                 "[online YAML parser](http://yaml-online-parser.appspot.com/) or "
                                 "by taking a look at the "
                                 "[Documentation](https://pyup.io/docs/bot/config/).".format(
                                    error=err.error)
                        )
                raise err
        return None

    def configure(self, create_error_issue=True, **kwargs):
        if kwargs.get("write_config", False):
            self.write_config = kwargs.get("write_config")
        # if the branch is not set, get the default branch
        if kwargs.get("branch", False) in [None, False]:
            self.config.branch = self.provider.get_default_branch(repo=self.user_repo)
        # set the config for this update run
        self.config.update_config(kwargs)
        repo_config = self.get_repo_config(
            repo=self.user_repo,
            create_error_issue=create_error_issue
        )
        if repo_config:
            self.config.update_config(repo_config)
        if self.write_config:
            self.config.update_config(self.write_config)
        logger.info("Runtime config is: {}".format(self.config))

    def update(self, **kwargs):
        """
        Main entrypoint to kick off an update run.
        :param kwargs:
        :return: RequirementsBundle
        """
        self.configure(**kwargs)
        self.get_all_requirements()
        self.apply_updates(
            initial=kwargs.get("initial", False),
            scheduled=kwargs.get("scheduled", False)
        )

        return self.req_bundle

    def can_pull(self, initial, scheduled):
        """
        Determines if pull requests should be created
        :return: bool
        """
        if not initial and self.config.is_valid_schedule():
            # if the config has a valid schedule, return True if this is a scheduled run
            return scheduled
        return True

    def apply_updates(self, initial, scheduled):

        InitialUpdateClass = self.req_bundle.get_initial_update_class()

        if initial:
            # get the list of pending updates
            try:
                _, _, _, updates = list(
                    self.iter_updates(initial, scheduled)
                )[0]
            except IndexError:
                # need to catch the index error here in case the intial update is completely
                # empty
                updates = False
            # if this is the initial run and the update list is empty, the repo is already
            # up to date. In this case, we create an issue letting the user know that the bot is
            # now set up for this repo and return early.
            if not updates:
                title = InitialUpdateClass.get_title()
                if self.config.pr_prefix:
                    title = "{prefix} {title}".format(prefix=self.config.pr_prefix, title=title)
                self.create_issue(
                    title=title,
                    body=InitialUpdateClass.get_empty_update_body()
                )
                if self.write_config:
                    self.pull_config(self.write_config)
                return

        # check if we have an initial PR open. If this is the case, we attach the initial PR
        # to all updates and are done. The `Initial Update` has to be merged (or at least closed)
        # before we continue to do anything here.
        initial_pr = next(
            (pr for pr in self.pull_requests if
             pr.canonical_title(self.config.pr_prefix) ==
             InitialUpdateClass.get_title() and pr.is_open),
            False
        )

        if initial and self.write_config:
            self.pull_config(self.write_config)

        # todo: This block needs to be refactored
        for title, body, update_branch, updates in self.iter_updates(initial, scheduled):
            # some scheduled updates don't have commits in them. This happens if a package is
            # outdated, but the config file is blocking the update (insecure, no updates).
            # check if this is the case here.
            if not updates:
                continue

            if self.config.pr_prefix:
                title = "{prefix} {title}".format(prefix=self.config.pr_prefix, title=title)
            if initial_pr:
                pull_request = initial_pr
            elif self.can_pull(initial, scheduled) and \
                    title not in [pr.title for pr in self.pull_requests]:
                update_branch = self.config.branch_prefix + update_branch
                pull_request = self.commit_and_pull(
                    initial=initial,
                    new_branch=update_branch,
                    title=title,
                    body=body,
                    updates=updates,
                )
            else:
                pull_request = next((pr for pr in self.pull_requests if pr.title == title), None)

            logger.info("Have updates {} and pr {}".format(updates, pull_request))
            for update in updates:
                update.requirement.pull_request = pull_request
                if self.config.close_prs and pull_request and not initial:
                    self.close_stale_prs(
                        update=update,
                        pull_request=pull_request,
                        scheduled=scheduled
                    )
                    # if this is a scheduled update, break since it's bundled
                    if pull_request.is_scheduled:
                        break

    def close_stale_prs(self, update, pull_request, scheduled):
        """
        Closes stale pull requests for the given update, links to the new pull request and deletes
        the stale branch.
        A stale PR is a PR that:
         - Is not merged
         - Is not closed
         - Has no commits (except the bot commit)
        :param update:
        :param pull_request:
        """
        closed = []
        if self.bot_token and not pull_request.is_initial:
            for pr in self.pull_requests:
                close_pr = False
                same_title = \
                    pr.canonical_title(self.config.pr_prefix) == \
                    pull_request.canonical_title(self.config.pr_prefix)

                if scheduled and pull_request.is_scheduled:
                    # check that the PR is open and the title does not match
                    if pr.is_open and not same_title:
                        # we want to close the previous scheduled PR if it is not merged yet
                        # and we want to close all previous updates if the user choose to
                        # switch to a scheduled update
                        if pr.is_scheduled or pr.is_update:
                            close_pr = True
                elif pull_request.is_update:
                    # check that, the pr is an update, is open, the titles are not equal and that
                    # the requirement matches
                    if pr.is_update and \
                        pr.is_open and \
                            not same_title and \
                            pr.get_requirement(self.config.pr_prefix) == update.requirement.key:
                        # there's a possible race condition where multiple updates with more than
                        # one target version conflict with each other (closing each others PRs).
                        # Check that's not the case here
                        if not self.has_conflicting_update(update):
                            close_pr = True

                if close_pr and self.is_bot_the_only_committer(pr=pr):
                    logger.info("Closing stale PR {} for {}".format(pr.title, pull_request.title))
                    self.provider.close_pull_request(
                        bot_repo=self.bot_repo,
                        user_repo=self.user_repo,
                        pull_request=pr,
                        comment="Closing this in favor of #{}".format(
                            pull_request.number),
                        prefix=self.config.branch_prefix
                    )
                    pr.state = "closed"
                    closed.append(pr)
        for closed_pr in closed:
            self.pull_requests.remove(closed_pr)

    def is_bot_the_only_committer(self, pr):
        """
        Checks if the bot is the only committer for the given pull request.
        :param update: Update to check
        :return: bool - True if conflict found
        """
        committer = self.provider.get_pull_request_committer(
            self.user_repo,
            pr)
        # flatten the list and remove duplicates
        committer_set = set([c.login for c in committer])

        # it's impossible to get the bots login if this is an integration, just check that
        # there's only one commit in the commit history.
        if self.integration or getattr(self.provider, 'name', '') == 'gitlab':
            return len(committer_set) == 1

        # check that there's exactly one committer in this PRs commit history and
        # that the committer is the bot
        return len(committer_set) == 1 and self.provider.is_same_user(self.bot, committer[0])

    def has_conflicting_update(self, update):
        """
        Checks if there are conflicting updates. Conflicting updates are updates that have the
        same requirement but different target versions to update to.
        :param update: Update to check
        :return: bool - True if conflict found
        """
        # we explicitly want a flat list of updates here, that's why we call iter_updates
        # with both `initial` and `scheduled` == False
        for _, _, _, updates in self.iter_updates(initial=False, scheduled=False):
            for _update in updates:
                if (
                        update.requirement.key == _update.requirement.key and
                        (
                                update.commit_message != _update.commit_message or
                                update.requirement.latest_version_within_specs !=
                                _update.requirement.latest_version_within_specs
                        )
                ):
                    logger.info("{} conflicting with {}/{}".format(
                        update.requirement.key,
                        update.requirement.latest_version_within_specs,
                        _update.requirement.latest_version_within_specs)
                    )
                    return True
        return False

    def create_branch(self, new_branch, delete_empty=False):
        """
        Creates a new branch.
        :param new_branch: string name of the new branch
        :param delete_empty: bool -- delete the branch if it is empty
        :return: bool -- True if successfull
        """
        logger.info("Preparing to create branch {} from {}".format(new_branch, self.config.branch))
        try:
            # create new branch
            self.provider.create_branch(
                base_branch=self.config.branch,
                new_branch=new_branch,
                repo=self.user_repo
            )
            logger.info("Created branch {} from {}".format(new_branch, self.config.branch))
            return True
        except BranchExistsError:
            logger.info("Branch {} exists.".format(new_branch))
            # if the branch exists, is empty and delete_empty is set, delete it and call
            # this function again
            if delete_empty:
                if self.provider.is_empty_branch(self.user_repo, self.config.branch, new_branch,
                                                 self.config.branch_prefix):
                    self.provider.delete_branch(self.user_repo, new_branch,
                                                self.config.branch_prefix)
                    logger.info("Branch {} was empty and has been deleted".format(new_branch))
                    return self.create_branch(new_branch, delete_empty=False)
                logger.info("Branch {} is not empty".format(new_branch))
        return False

    def pull_config(self, new_config):  # pragma: no cover
        """

        :param new_config:
        :return:
        """
        logger.info("Creating new config file with {}".format(new_config))
        branch = 'pyup-config'
        if self.create_branch(branch, delete_empty=True):
            content = self.config.generate_config_file(new_config)
            _, content_file = self.provider.get_file(self.user_repo, '.pyup.yml', branch)
            if content_file:
                # a config file exists, update and commit it
                logger.info(
                    "Config file exists, updating config for sha {}".format(content_file.sha))
                self.provider.create_commit(
                    repo=self.user_repo,
                    path=".pyup.yml",
                    branch=branch,
                    content=content,
                    commit_message="update pyup.io config file",
                    committer=self.bot if self.bot_token else self.user,
                    sha=content_file.sha
                )
            logger.info("No config file found, writing new config file")
            # there's no config file present, write a new config file and commit it
            self.provider.create_and_commit_file(
                repo=self.user_repo,
                path=".pyup.yml",
                branch=branch,
                content=content,
                commit_message="create pyup.io config file",
                committer=self.bot if self.bot_token else self.user,
            )

            title = 'Config file for pyup.io'
            if self.config.pr_prefix:
                title = "{prefix} {title}".format(prefix=self.config.pr_prefix, title=title)
            body = 'Hi there and thanks for using pyup.io!\n' \
                   '\n' \
                   "Since you are using a non-default config I've created one for you.\n\n" \
                   "There are a lot of things you can configure on top of " \
                   "that, so make sure to check out the " \
                   "[docs](https://pyup.io/docs/configuration/) to see what I can do for you."

            pr = self.create_pull_request(
                title=title,
                body=body,
                new_branch=branch,
            )
            return pr

    def commit_and_pull(self, initial, new_branch, title, body, updates):
        logger.info("Preparing commit {}".format(title))
        if self.create_branch(new_branch, delete_empty=False):
            updated_files = {}
            for update in self.iter_changes(initial, updates):
                if update.requirement_file.path in updated_files:
                    sha = updated_files[update.requirement_file.path]["sha"]
                    content = updated_files[update.requirement_file.path]["content"]
                else:
                    sha = update.requirement_file.sha
                    content = update.requirement_file.content
                old_content = content
                content = update.requirement.update_content(content, self.config.update_hashes)
                if content != old_content:
                    new_sha = self.provider.create_commit(
                        repo=self.user_repo,
                        path=update.requirement_file.path,
                        branch=new_branch,
                        content=content,
                        commit_message=update.commit_message,
                        sha=sha,
                        committer=self.bot if self.bot_token else self.user,
                    )
                    updated_files[update.requirement_file.path] = {"sha": new_sha,
                                                                   "content": content}
                else:
                    if hasattr(self.user_repo, 'path_with_namespace'):
                        repo_name = self.user_repo.path_with_namespace
                    elif hasattr(self.user_repo, 'full_name'):
                        repo_name = self.user_repo.full_name
                    else:
                        repo_name = str(self.user_repo)
                    logger.error("Empty commit at {repo}, unable to update {title}.".format(
                        repo=repo_name, title=title)
                    )

            if updated_files:
                pr = self.create_pull_request(
                    title=title,
                    body=body,
                    new_branch=new_branch,
                )
                self.pull_requests.append(pr)
                return pr
        return None

    def create_issue(self, title, body):
        return self.provider.create_issue(
            repo=self.bot_repo if self.bot_token else self.user_repo,
            title=title,
            body=body,
        )

    def create_pull_request(self, title, body, new_branch):

        # if we have a bot user that creates the PR, we might run into problems on private
        # repos because the bot has to be a collaborator. We try to submit the PR before checking
        # the permissions because that saves us API calls in most cases
        kwargs = dict(title=title,body=body, new_branch=new_branch,
                      base_branch=self.config.branch, pr_label=self.config.label_prs, assignees=self.config.assignees,
                      config=self.config)
        if self.bot_token:
            try:
                return self.provider.create_pull_request(repo=self.bot_repo, **kwargs)
            except NoPermissionError:
                self.provider.get_pull_request_permissions(self.bot, self.user_repo)

        return self.provider.create_pull_request(
            repo=self.bot_repo if self.bot_token else self.user_repo,
            **kwargs
        )

    def iter_git_tree(self, sha=None):
        branch = sha if sha is not None else self.config.branch
        return self.provider.iter_git_tree(branch=branch, repo=self.user_repo)

    def iter_updates(self, initial, scheduled):
        return self.req_bundle.get_updates(
            initial=initial,
            scheduled=scheduled,
            config=self.config
        )

    def iter_changes(self, initial, updates):
        return iter(updates)

    # if this function gets updated, the gist at https://gist.github.com/jayfk/45862b05836701b49b01
    # needs to be updated too
    def get_all_requirements(self, sha=None):
        if self.config.search:
            logger.info("Searching requirement files")
            for file_type, path in self.iter_git_tree(sha=sha):
                if file_type == "blob":
                    if "requirements" in path:
                        if path.endswith("txt") or path.endswith("pip"):
                            self.add_requirement_file(path, sha)
                    if "setup.cfg" in path:
                        self.add_requirement_file(path, sha)
        for req_file in self.config.requirements:
            self.add_requirement_file(req_file.path, sha=sha)
        self.req_bundle.resolve_pipfiles()

    # if this function gets updated, the gist at https://gist.github.com/jayfk/c6509bbaf4429052ca3f
    # needs to be updated too
    def add_requirement_file(self, path, sha=None):
        logger.info("Adding requirement file at {}".format(path))
        branch = sha if sha is not None else self.config.branch
        if not self.req_bundle.has_file_in_path(path):
            req_file = self.provider.get_requirement_file(
                path=path, repo=self.user_repo, branch=branch)
            if req_file is not None:
                self.req_bundle.append(req_file)
                for other_file in req_file.other_files:
                    self.add_requirement_file(other_file, sha=sha)


class DryBot(Bot):
    def commit_and_pull(self, initial, new_branch, title, body, updates):  # pragma: no cover
        return None
