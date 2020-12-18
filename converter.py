#!/usr/bin/env python3
import argparse
import logging
import os
import multiprocessing
import moviepy.editor as editor
from pathlib import Path


VIDEO = (
    '.mp4', '.m4v', '.mkv', '.flv',
    '.webm', '.avi', '.wmv', '.mpg', '.mov'
)


class FileEvenExistsError(Exception):
    pass


class WrongExtentionError(Exception):
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


def is_video(path: Path or str) -> bool:
    return Path(path).suffix in VIDEO


def convert(from_: Path or str,
            to_: Path or str,
            force: bool = False,
            **kwargs) -> None:
    """
    Convert a video file to another video format.

    :param from_: Path or str, path to video file to convert.
    :param to_: Path or str, path to result file.
    :param force: bool, rewrite existing to_ file if True.
    :param kwargs: key words to writing a new video file.
    :return: None.
    :exception FileNotFoundError: if the file doesn't exist.
    :exception FileEvenExistsError: if the result file even
     exists and force = False.
    :exception WrongExtentionError: if path has a wrong suffix.
    """
    from_ = Path(from_)
    to_ = Path(to_)

    if not from_.exists():
        raise FileNotFoundError(f"{from_} doesn't exist")
    if to_.exists():
        if not force:
            raise FileEvenExistsError(f"{to_} even exists")
    if not (is_video(from_) and is_video(to_)):
        raise WrongExtentionError(f"{from_} or {to_} have a wrong extension")

    logger.debug(f"Converting {from_} to {to_}")
    try:
        video = editor.VideoFileClip(str(from_))
    except Exception as e:
        logger.error(f"{e}\n while openning {from_} file")
        raise

    try:
        video.write_videofile(str(to_), **kwargs)
    except Exception as e:
        logger.error(f"{e}\n while converting {from_} {to_}")
        raise

    logger.debug(f"Converting {from_} to {to_} was completed")


def convert_suffix_to_mp4(path: Path or str) -> Path:
    """
    Change a filename extension to mp4.

    :param path: Path or str, path to change its extension.
    :return: Path with changed to .mp4 extension.
    """
    return Path(path).with_suffix('.mp4')


def convert_file_to_mp4(from_: Path or str,
                        to_: Path or str = None) -> None:
    """
    Convert a video file to file with mp4 format.

    :param from_: Path or str, path to the video file to convert.
    :param to_: Path or str, path to the result video file.
    :return: None.
    """
    if Path(from_).suffix == '.mp4':
        logger.error(f"{from_} is even a mp4 filr, nothing to convert")
        return

    to_ = to_ or convert_suffix_to_mp4(from_)
    try:
        convert(from_, to_)
    except Exception as e:
        logger.error(f"{e}\nconverting {from_} to {to_}")


def convert_all(path: Path or str) -> None:
    convert_file_to_mp4(path)


def main() -> None:
    convert_all('sample_1280x720.flv')


if __name__ == "__main__":
    main()

