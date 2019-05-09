# -*- coding: utf-8 -*-
from pyup import __version__, settings
from pyup.bot import Bot
from pyup.requirements import RequirementFile, RequirementsBundle
from pyup.providers.github import Provider as GithubProvider
from pyup.providers.gitlab import Provider as GitlabProvider
from pyup.providers.bitbucket_server import Provider as BitbucketServerProvider

import click
from tqdm import tqdm
import logging


@click.command()
@click.version_option(__version__, '-v', '--version')
@click.option('--repo', prompt='repository', help='')
@click.option('--user-token', prompt='user token', help='When using bitbucket_server, use this format: user@token@base_url')
@click.option('--bot-token', help='', default=None)
@click.option("--key", default="",
              help="API Key for pyup.io's vulnerability database. Can be set as SAFETY_API_KEY "
                   "environment variable. Default: empty")
@click.option('--provider', help='API to use; either github, gitlab or bitbucket_server', default="github")
@click.option('--provider_url', help='Optional custom URL to your provider', default=None)
@click.option('--branch', help='Set the branch the bot should use', default='master')
@click.option('--initial', help='Set this to bundle all PRs into a large one',
              default=False, is_flag=True)
@click.option('--log', help='Set the log level', default="ERROR")
def main(repo, user_token, bot_token, key, provider, provider_url, branch, initial, log):
    logging.basicConfig(level=getattr(logging, log.upper(), None))

    settings.configure(key=key)

    if provider == 'github':
        ProviderClass = GithubProvider
    elif provider == 'gitlab':
        ProviderClass = GitlabProvider
    elif provider == 'bitbucket_server':
        ProviderClass = BitbucketServerProvider
    else:
        raise NotImplementedError

    bot = CLIBot(
        repo=repo,
        user_token=user_token,
        bot_token=bot_token,
        provider=ProviderClass,
        provider_url=provider_url,
    )

    bot.update(branch=branch, initial=initial)


if __name__ == '__main__':
    main()


class CLIBot(Bot):

    def __init__(self, repo, user_token, bot_token=None,
                 provider=GithubProvider, bundle=RequirementsBundle, provider_url=None):
        bundle = CLIBundle
        super(CLIBot, self).__init__(repo, user_token, bot_token, provider, bundle, provider_url=provider_url)

    def iter_updates(self, initial, scheduled):

        ls = list(super(CLIBot, self).iter_updates(initial, scheduled))

        if not initial:
            ls = tqdm(ls, desc="Updating ...")
        for title, body, update_branch, updates in ls:
            if not initial:
                ls.set_description(title)
            yield title, body, update_branch, updates

    def iter_changes(self, initial, updates):
        # we don't display the progress bar if this is a sequential update, just return the list
        if initial:
            updates = tqdm(updates, desc="Updating ...")
        for update in updates:
            if initial:
                updates.set_description(update.commit_message)
            yield update


class CLIBundle(RequirementsBundle):

    def get_requirement_file_class(self):
        return CLIRequirementFile


class CLIRequirementFile(RequirementFile):
    def iter_lines(self, lineno=0):
        bar = tqdm(self.content.splitlines()[lineno:], desc="Processing {}".format(self.path))
        for item in bar:
            yield item
