class BranchExistsError(Exception):  # pragma: no cover
    pass


class NoPermissionError(Exception):  # pragma: no cover
    pass


class RepoDoesNotExistError(Exception):  # pragma: no cover
    pass


class UnsupportedScheduleError(Exception):  # pragma: no cover
    pass


class ConfigError(Exception):
    def __init__(self, content, error):
        self.error = error
        self.content = content
