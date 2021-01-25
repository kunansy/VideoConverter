#!/usr/bin/env python3.8
import argparse
import logging
import multiprocessing as mp
import os
import time
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

MAX_FILENAME_LENGTH = 16


class FileEvenExistsError(Exception):
    pass


class WrongExtensionError(Exception):
    pass


class HandlerNotFoundError(Exception):
    pass


MSG_FMT = "[{asctime},{msecs:3.0f}] [{levelname}] " \
          "[{process}:{module}:{funcName}] {message}"
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
file_handler.setLevel(logging.CRITICAL)
file_handler.setFormatter(formatter)

# creating logger
logger = logging.getLogger('converter')
logger.setLevel(logging.DEBUG)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def set_handler_level(logger_: logging.Logger,
                      handler_class: type):
    def wrapped(level: int or str):
        try:
            level = level.upper()
        except AttributeError:
            pass

        is_there_the_handler = False
        for handler_index in range(len(logger_.handlers)):
            if logger_.handlers[handler_index].__class__ == handler_class:
                logger_.handlers[handler_index].setLevel(level)
                is_there_the_handler = True

        if not is_there_the_handler:
            raise HandlerNotFoundError(
                f"Handler {handler_class.__class__.__name__} not found")

    return wrapped


set_stream_handler_level = set_handler_level(logger, logging.StreamHandler)
set_file_handler_level = set_handler_level(logger, logging.FileHandler)


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
        logger.info(f"{from_} is even a mp4 file, move it to destination")
        return

    if to_ is not None and to_.suffix != '.mp4':
        logger.error(f"Destination file must have .mp4 extension, "
                     f"but '{to_.suffix}' found in '{to_}'")
        return

    to_ = to_ or change_suffix_to_mp4(from_)
    try:
        convert(from_, to_)
    except Exception as e:
        logger.error(f"{e}\nconverting {from_} to {to_}")

    # move processed video
    os.rename(from_, CONVERTED_VIDEOS_FOLDER / from_)


def files(start_path: Path,
          dest_path: Path) -> Iterator[Tuple[Path, Path]]:
    for from_, is_ok in validate_videos(start_path):
        if is_ok:
            to_ = change_suffix_to_mp4(from_)
            yield from_, dest_path / to_


def convert_all(base_path: Path,
                dest_path: Path,
                processes_count: int = None) -> None:
    os.makedirs(DEST_FOLDER, exist_ok=True)
    os.makedirs(CONVERTED_VIDEOS_FOLDER, exist_ok=True)

    processes_count = processes_count or mp.cpu_count() * 2
    with mp.Pool(processes_count) as pool:
        pool.starmap(convert_file_to_mp4, files(base_path, dest_path))


def validate_videos(start_path: Path) -> Iterator[Tuple[Path, bool]]:
    """
    Get path to file and status whether
     the file is valid to convert.

    Skip all files (dirs) with no extension.

    :param start_path: start Path.
    :return: tuple of Path and bool.
    """
    for item in os.listdir(start_path):
        item = Path(item)
        if item.suffix:
            yield item, is_video(item)


def short_filename(path: Path,
                   length: int = MAX_FILENAME_LENGTH) -> str:
    """
    Short the filename.

    :param path: Path to the file.
    :param length: int, expected name length.

    :return: str, shorted file name.
    """
    shorted_name = Path(path).name
    if len(shorted_name) > length:
        shorted_name = ''.join(
            shorted_name[:length // 2] +
            '...' +
            shorted_name[-length // 2:])
    return shorted_name


def validate(start_path: Path) -> None:
    """
    Print which files are valid to convert but which not.

    :param start_path: start Path.
    :return: None.
    """
    valid = invalid = 0
    for path, is_valid in validate_videos(start_path):
        shorted_name = short_filename(path)
        print(colorama.Fore.GREEN if is_valid else colorama.Fore.RED,
              "Processing",
              end='', sep='')

        if is_valid:
            valid += 1
            print(f"{shorted_name} is valid".rjust(40, '.'))
        else:
            invalid += 1
            print(f"{shorted_name} is invalid".rjust(40, '.'))

    print(colorama.Fore.GREEN, "=" * 50, colorama.Fore.RESET, sep='')
    print(f"Total files count: {len(os.listdir(start_path))}")
    if invalid == 0:
        print(f"All {valid} videos are valid")
    else:
        print(f"Total valid videos: {valid}")
        print(f"Total invalid videos: {invalid}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert video to .mp4"
    )
    parser.add_argument(
        '-v', '--validate',
        action="store_true",
        default=True,
        dest='validate',
        required=False
    )
    parser.add_argument(
        '-c', '--convert',
        action="store_true",
        default=False,
        dest='convert',
        required=False
    )
    parser.add_argument(
        '-p', '--start-path',
        metavar="Path to dir where there are videos to convert",
        type=str,
        default=Path('.'),
        dest='start_path',
        required=False
    )
    parser.add_argument(
        '-d', '--destination-path',
        metavar="Path to where store processed videos",
        type=str,
        default=DEST_FOLDER,
        dest='dest_path',
        required=False
    )
    parser.add_argument(
        '-l', '--log-level',
        metavar="Level of stream handler",
        type=str,
        default='INFO',
        dest="level",
        required=False
    )
    args = parser.parse_args()

    if level := args.level:
        set_stream_handler_level(level)

    start_path = Path(args.start_path)
    dest_path = Path(args.dest_path)

    if args.validate:
        validate(Path(start_path))
    if args.convert:
        logger.info("Converting started...")
        start = time.time()
        convert_all(start_path, dest_path)
        logger.info(f"Converting completed by {time.time() - start:.2f}s")


if __name__ == "__main__":
    main()
