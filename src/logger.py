import logging
import logging.handlers
import os
from pathlib import Path
from typing import Union, List

import exceptions as ex

LEVEL = Union[str, int]


class Logger(logging.Logger):
    MSG_FMT = "[{asctime},{msecs:3.0f}] [{levelname}] " \
              "[{process}:{module}:{funcName}] {message}"
    DATE_FMT = "%d.%m.%Y %H:%M:%S"

    LOG_FOLDER = Path('logs')
    LOG_FILE_NAME = 'converter.log'

    def __init__(self,
                 name: str,
                 level: str or int,
                 *,
                 fmt: str = None,
                 date_fmt: str = None,
                 log_folder: str or Path = None,
                 log_file_name: str or Path = None) -> None:
        super().__init__(name, level)

        self.MSG_FMT = fmt or self.MSG_FMT
        self.DATE_FMT = date_fmt or self.DATE_FMT
        self.LOG_FOLDER = log_folder or self.LOG_FOLDER
        self.LOG_FILE_NAME = log_file_name or self.LOG_FILE_NAME

        os.makedirs(self.LOG_FOLDER, exist_ok=True)

        self.__log_path = self.LOG_FOLDER / self.LOG_FILE_NAME
        self.__formatter = logging.Formatter(
            fmt=self.MSG_FMT, datefmt=self.DATE_FMT, style='{'
        )

        # don't forget to add the logger the global loggers storage
        logging.Logger.manager.loggerDict[name] = self

    @property
    def log_file_path(self) -> Path:
        return self.__log_path

    @property
    def formatter(self) -> logging.Formatter:
        return self.__formatter

    @property
    def stream_handler(self) -> logging.StreamHandler:
        return self._get_handler(logging.StreamHandler)

    @property
    def file_handler(self) -> logging.handlers.RotatingFileHandler:
        return self._get_handler(logging.handlers.RotatingFileHandler)

    def add_stream_handler(self,
                           level: LEVEL) -> None:
        if logging.StreamHandler in self:
            self.warning(f"Stream handler even exists")

        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(self.formatter)

        self.addHandler(handler)

    def add_file_handler(self,
                         level: LEVEL) -> None:
        try:
            self.file_handler
        except ValueError:
            pass
        else:
            self.error(f"File handler even exists")
            raise ex.HandlerEvenExistsError("File handler even exists")

        handler = logging.handlers.RotatingFileHandler(
            self.log_file_path, delay=True, encoding='utf-8',
            maxBytes=10240, backupCount=3
        )
        handler.setLevel(level)
        handler.setFormatter(self.formatter)

        self.addHandler(handler)

    def _get_handler(self,
                     handler_type: type) -> logging.Handler:
        for handler in self.handlers:
            if isinstance(handler, handler_type):
                return handler

        raise ex.HandlerNotFoundError(
            f"There's no '{handler_type.__class__.__name__}'")

    def _set_handler_level(self,
                           handler_type: type,
                           level: LEVEL):
        if handler_type not in self:
            raise exceptions.HandlerNotFoundError(
                f"handler '{handler_type.__class__.__name__}' not found")

        try:
            level = level.upper()
        except AttributeError:
            pass

        for handler in self:
            if isinstance(handler, handler_type):
                handler.setLevel(level)

    def set_stream_handler_level(self,
                                 level: LEVEL) -> None:
        self._set_handler_level(type(self.stream_handler), level)

    def set_file_handler_level(self,
                               level: LEVEL) -> None:
        self._set_handler_level(type(self.file_handler), level)

    def __iter__(self) -> iter:
        return iter(self.handlers)

    def __contains__(self, item: type) -> bool:
        try:
            self._get_handler(item)
        except ValueError:
            return False
        return True
