class EAKISBaseError(Exception):
    pass


class TaskNotFoundError(EAKISBaseError):
    pass


class AssetNotFoundError(EAKISBaseError):
    pass


class LLMError(EAKISBaseError):
    pass


class CrawlerError(EAKISBaseError):
    pass
