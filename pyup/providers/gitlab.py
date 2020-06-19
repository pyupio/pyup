# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
import logging
from gitlab import Gitlab
from gitlab.exceptions import GitlabGetError, GitlabCreateError
from ..errors import BranchExistsError, RepoDoesNotExistError
from base64 import b64encode

logger = logging.getLogger(__name__)


class BadTokenError(Exception):
    pass


class Provider(object):
    name = 'gitlab'

    class Committer(object):
        def __init__(self, login):
            self.login = login

    def __init__(self, bundle, intergration=False, url=None, ignore_ssl=False):
        self.bundle = bundle
        self.url = url
        self.ignore_ssl = ignore_ssl
        if intergration:
            raise NotImplementedError(
                'Gitlab provider does not support integration mode')

    @classmethod
    def is_same_user(cls, this, that):
        return this.login == that.login

    def _api(self, token):
        parts = token.split('@')
        if len(parts) == 1:
            host = self.url or 'https://gitlab.com'
            auth = parts[0]
        elif len(parts) == 2:
            auth, host = parts
        else:
            raise BadTokenError(
                'Got token "{}": format should be wither "apikey" for '
                'gitlab.com, or "apikey@https://yourgitlab.local"'.format(
                    token))
        return Gitlab(host, auth, ssl_verify=(not self.ignore_ssl))

    def get_user(self, token):
        gl = self._api(token)
        gl.auth()
        return gl.user

    def get_repo(self, token, name):
        try:
            return self._api(token).projects.get(name)
        except GitlabGetError as e:
            if e.response_code == 404:
                raise RepoDoesNotExistError()
            raise e

    def get_default_branch(self, repo):
        return repo.default_branch

    def get_pull_request_permissions(self, user, repo):
        # TODO: IDK how this works on gitlab
        return True

    def iter_git_tree(self, repo, branch):
        for item in repo.repository_tree(ref=branch, recursive=True, all=True):
            yield item['type'], item['path']

    def get_file(self, repo, path, branch):
        logger.info("Getting file at {} for branch {}".format(path, branch))
        # remove unnecessary leading slash to avoid gitlab errors. See #375
        path = path.lstrip('/')
        try:
            contentfile = repo.files.get(file_path=path, ref=branch)
        except GitlabGetError as e:
            if e.response_code == 404:
                logger.warning("Unable to get {path}".format(
                    path=path,
                ))
                return None, None
        else:
            return contentfile.decode().decode("utf-8"), contentfile

    def create_and_commit_file(self, repo, path, branch, content, commit_message, committer):

        # TODO: committer
        return repo.files.create({
            'file_path': path,
            'branch': branch,
            'content': content,
            'commit_message': commit_message
        })

    def get_requirement_file(self, repo, path, branch):
        content, file_obj = self.get_file(repo, path, branch)
        if content is not None and file_obj is not None:
            return self.bundle.get_requirement_file_class()(
                path=path,
                content=content,
            )
        return None

    def create_branch(self, repo, base_branch, new_branch):
        try:
            repo.branches.create({"branch": new_branch,
                                  "ref": base_branch})
        except GitlabCreateError as e:
            if e.error_message == 'Branch already exists':
                raise BranchExistsError(new_branch)

    def is_empty_branch(self, repo, base_branch, new_branch, prefix):
        """
        Compares the top commits of two branches.
        Please note: This function isn't checking if `base_branch` is a direct
        parent of `new_branch`, see
        http://stackoverflow.com/questions/3161204/find-the-parent-branch-of-a-git-branch
        :param repo: github.Repository
        :param base_branch: string name of the base branch
        :param new_branch: string name of the new branch
        :param prefix: string branch prefix, default 'pyup-'
        :return: bool -- True if empty
        """
        # extra safeguard to make sure we are handling a bot branch here
        assert new_branch.startswith(prefix)
        comp = repo.repository_compare(base_branch, new_branch)
        n = len(comp.commits)
        logger.info("Got a total of {} commits in {}".format(n, new_branch))
        return n == 0

    def delete_branch(self, repo, branch, prefix):
        """
        Deletes a branch.
        :param repo: github.Repository
        :param branch: string name of the branch to delete
        """
        # make sure that the name of the branch begins with pyup.
        assert branch.startswith(prefix)
        obj = repo.branches.get(branch)
        obj.delete()

    def create_commit(self, path, branch, commit_message, content, sha, repo, committer):
        # TODO: committer

        f = repo.files.get(file_path=path, ref=branch)
        # Gitlab supports a plaintext encoding, which is when the encoding
        # value is unset.  Python-Gitlab seems to set it to b64, so we can't
        # unset it unfortunately
        f.content = b64encode(content.encode()).decode()
        f.encoding = 'base64'
        # TODO: committer
        f.save(branch=branch, commit_message=commit_message)

    def get_pull_request_committer(self, repo, pull_request):
        return [
            self.Committer(participant['username'])
            for participant in repo.mergerequests.get(pull_request.number).participants()
        ]

    def close_pull_request(self, bot_repo, user_repo, pull_request, comment, prefix):
        mr = user_repo.mergerequests.get(pull_request.number)
        mr.state_event = 'close'
        mr.save()
        mr.notes.create({'body': comment})

        source_branch = mr.changes()['source_branch']
        logger.info("Deleting source branch {}".format(source_branch))
        self.delete_branch(user_repo, source_branch, prefix)

    def _merge_merge_request(self, mr, config):
        mr.merge(should_remove_source_branch=config.gitlab.should_remove_source_branch,
                 merge_when_pipeline_succeeds=True)

    def create_pull_request(self, repo, title, body, base_branch, new_branch, pr_label, assignees, config):
        # TODO: Check permissions
        try:
            if len(body) >= 65536:
                logger.warning("PR body exceeds maximum length of 65536 chars, reducing")
                body = body[:65536 - 1]

            mr = repo.mergerequests.create({
                'source_branch': new_branch,
                'target_branch': base_branch,
                'title': title,
                'description': body,
                'pr_label': pr_label,
                'remove_source_branch': config.gitlab.should_remove_source_branch
            })

            if config.gitlab.merge_when_pipeline_succeeds:
                self._merge_merge_request(mr, config)

            return self.bundle.get_pull_request_class()(
                state=mr.state,
                title=mr.title,
                url=mr.web_url,
                created_at=mr.created_at,
                number=mr.iid,
                issue=False
            )
        except GitlabCreateError as e:
            if e.response_code == 409:
                logger.warning(
                    "PR {title} from {base_branch}->{new_branch} is already "
                    "exists and is open, resorting to a comment "
                    "instead".format(
                        title=title, new_branch=new_branch,
                        base_branch=base_branch))

                comment = '# {title}\n{body}'.format(title=title, body=body)
                # the exception doesn't say *which* MR is open, so we have to
                # find it :(
                for mr in repo.mergerequests.list(state='opened', all=True):
                    if (mr.source_branch == new_branch and mr.target_branch == base_branch):
                        mr.notes.create({'body': comment})
                        return self.bundle.get_pull_request_class()(
                            state=mr.state,
                            title=mr.title,
                            url=mr.web_url,
                            created_at=mr.created_at,
                            number=mr.iid,
                            issue=False
                        )

    def create_issue(self, repo, title, body):
        return repo.issues.create({
            'title': title,
            'description': body
        })

    def iter_issues(self, repo, creator):
        # TODO: handle creator
        for issue in repo.mergerequests.list(state='opened', all=True):
            yield self.bundle.get_pull_request_class()(
                state=issue.state,
                title=issue.title,
                url=issue.web_url,
                created_at=issue.created_at,
                number=issue.iid,
                issue=True,
            )
