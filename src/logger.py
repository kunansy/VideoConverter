import logging
import os
from pathlib import Path
from typing import Union, List

import exceptions

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
    def msg_format(self) -> str:
        return self.MSG_FMT

    @property
    def date_format(self) -> str:
        return self.DATE_FMT

    @property
    def log_file_path(self) -> Path:
        return self.__log_path

    @property
    def formatter(self) -> logging.Formatter:
        return self.__formatter

    @formatter.setter
    def formatter(self,
                  msg_format: str = None,
                  date_format: str = None) -> None:
        if msg_format is date_format is None:
            raise TypeError("No args found")

        self.__formatter = logging.Formatter(
            fmt=msg_format, datefmt=date_format, style='{'
        )

        for handler in self:
            handler.formatter = self.formatter

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
        if logging.FileHandler in self:
            self.warning(f"Stream handler even exists")

        handler = logging.FileHandler(
            self.log_file_path, delay=True, encoding='utf-8'
        )
        handler.setLevel(level)
        handler.setFormatter(self.formatter)

        self.addHandler(handler)

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
        self._set_handler_level(logging.StreamHandler, level)

    def set_file_handler_level(self,
                               level: LEVEL) -> None:
        self._set_handler_level(logging.FileHandler, level)

    def __iter__(self) -> iter:
        return iter(self.handlers)

    def __getitem__(self,
                    item: int or slice
                    ) -> logging.Handler or List[logging.Handler]:
        return self.handlers[item]

    def __setitem__(self,
                    index: int,
                    value: logging.Handler) -> None:
        self.handlers[index] = value

    def __contains__(self, item: type) -> bool:
        return any(
            isinstance(handler, item)
            for handler in self
        )
