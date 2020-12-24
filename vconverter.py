#!/usr/bin/env python3.8
import argparse
import logging
import multiprocessing as mp
import os
from pathlib import Path
from typing import Tuple, Iterator

import colorama
import moviepy.editor as editor

VIDEO = (
    '.mp4', '.m4v', '.mkv', '.flv',
    '.webm', '.avi', '.wmv', '.mpg', '.mov'
)

DEST_FOLDER = Path('result/')
# videos have been converted (original files)
CONVERTED_VIDEOS_FOLDER = Path('processed/')


class FileEvenExistsError(Exception):
    pass


class WrongExtensionError(Exception):
    pass


MSG_FMT = "[{name}:{process}:{module}:{levelname}:" \
          "{funcName}:{asctime}] {message}"
DATE_FMT = "%d.%m.%Y %H:%M:%S"

LOG_FOLDER = Path('logs')
os.makedirs(LOG_FOLDER, exist_ok=True)

log_path = LOG_FOLDER / 'converter.log'


formatter = logging.Formatter(
    fmt=MSG_FMT,
    datefmt=DATE_FMT,
    style='{'
)

# creating stream handler
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)

# creating file handler
file_handler = logging.FileHandler(
    log_path,
    delay=True,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# creating logger
logger = logging.getLogger('converter')
logger.setLevel(logging.DEBUG)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def is_video(path: Path) -> bool:
    """
    :param path: Path to file.
    :return: bool, whether the file conversion is supported.
    """
    return path.suffix in VIDEO


def convert(from_: Path,
            to_: Path,
            force: bool = False,
            **kwargs) -> None:
    """
    Convert a video to another video format.

    :param from_: Path to video to convert.
    :param to_: Path to result file.
    :param force: bool, rewrite existing to_ file if True.
     False by default.
    :param kwargs: key words to writing a new video file.
    :return: None.

    :exception FileNotFoundError: if the source file doesn't exist.
    :exception FileEvenExistsError: if the result file even
     exists and force = False.
    :exception WrongExtensionError: if a path has an
     unsupported extension.
    """
    if not from_.exists():
        raise FileNotFoundError(f"'{from_}' doesn't exist")
    if to_.exists():
        if not force:
            raise FileEvenExistsError(f"'{to_}' even exists")
    if not (is_video(from_) and is_video(to_)):
        raise WrongExtensionError(f"'{from_}' or '{to_}' have wrong extension")

    logger.debug(f"Converting '{from_}' to '{to_}'")
    try:
        video = editor.VideoFileClip(str(from_))
    except Exception as e:
        logger.error(f"{e}\n while opening '{from_}' file")
        raise

    try:
        video.write_videofile(str(to_), **kwargs)
    except Exception as e:
        logger.error(f"{e}\n while converting '{from_}' to '{to_}'")
        raise

    logger.debug(f"Converting '{from_}' to '{to_}' completed")


def change_suffix_to_mp4(path: Path or str) -> Path:
    """
    :param path: Path or str, file to change its extension.
    :return: Path format *.mp4.
    """
    return Path(path).with_suffix('.mp4')


def convert_file_to_mp4(from_: Path,
                        to_: Path = None) -> None:
    """
    Convert a video file to *.mp4.

    Just move source file to destination folder
     if it is even *.mp4.

    Move source file to CONVERTED_VIDEOS_FOLDER
     if converted successfully.

    :param from_: Path to the video file to convert.
    :param to_: Path to the result file.
    :return: None.
    """
    if Path(from_).suffix == '.mp4':
        os.rename(from_, to_)
        logger.error(f"{from_} is even a mp4 file, move to to destination")
        return

    to_ = to_ or change_suffix_to_mp4(from_)
    try:
        convert(from_, to_)
    except Exception as e:
        logger.error(f"{e}\nconverting {from_} to {to_}")


def files(start_path: Path or str,
          dest_path: Path) -> tuple:
    for from_ in os.listdir(start_path):
        if is_video(from_):
            to_ = change_suffix_to_mp4(from_)
            yield from_, dest_path / to_


def convert_all(base_path: Path,
                dest_path: Path,
                processes_count: int = None) -> None:
    processes_count = processes_count or mp.cpu_count() * 2
    with mp.Pool(processes_count) as pool:
        pool.starmap(convert_file_to_mp4, files(base_path, dest_path))


def main() -> None:
    convert_all()


if __name__ == "__main__":
    main()

