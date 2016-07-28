# -*- coding: utf-8 -*-
from pyup import __version__
from pyup.bot import DryBot, Bot
from pyup.requirements import RequirementFile, RequirementsBundle
from pyup.providers.github import Provider as GithubProvider
import click
from tqdm import tqdm
import logging


@click.command()
@click.version_option(__version__, '-v', '--version')
@click.option('--repo', prompt='repository', help='')
@click.option('--user-token', prompt='user token', help='')
@click.option('--bot-token', help='', default=None)
@click.option('--provider', help='', default="github")
@click.option('--dry', help='Run the bot without committing', default=False)
@click.option('--branch', help='Set the branch the bot should use', default='master')
@click.option('--initial', help='Set this to bundle all PRs into a large one',
              default=False, is_flag=True)
@click.option('--pin', help='', default=True)
@click.option('--close-prs', help='Tell the bot to close stale pull requests', default=True)
@click.option('--log', help='Set the log level', default="ERROR")
def main(repo, user_token, bot_token, provider, dry, branch, initial, pin, close_prs, log):
    logging.basicConfig(level=getattr(logging, log.upper(), None))

    if provider == 'github':
        ProviderClass = GithubProvider
    else:
        raise NotImplementedError

    if dry:
        BotClass = DryBot
    else:
        BotClass = CLIBot

    bot = BotClass(
        repo=repo,
        user_token=user_token,
        bot_token=bot_token,
        provider=ProviderClass
    )

    bot.update(branch=branch, initial=initial, pin=pin, close_prs=close_prs)

if __name__ == '__main__':
    main()


class CLIBot(Bot):

    def __init__(self, repo, user_token, bot_token=None,
                 provider=GithubProvider, bundle=RequirementsBundle):
        bundle = CLIBundle
        super(CLIBot, self).__init__(repo, user_token, bot_token, provider, bundle)

    def iter_updates(self, initial):

        ls = list(super(CLIBot, self).iter_updates(initial))

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
    def iter_lines(self):
        bar = tqdm(self.content.splitlines(), desc="Processing {}".format(self.path))
        for item in bar:
            yield item
