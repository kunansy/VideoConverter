class FileEvenExistsError(FileExistsError):
    pass


class WrongExtensionError(ValueError):
    pass


class HandlerNotFoundError(ValueError):
    pass


class HandlerEvenExistsError(ValueError):
    pass
