#!/usr/bin/env python3.8
import argparse
import datetime
import logging
import mimetypes
import multiprocessing as mp
import os
import time
from pathlib import Path
from typing import Tuple, Iterator

import colorama
import ffmpy

import exceptions
import logger


DEST_FOLDER = Path('result/')
# store here videos have been converted (original files)
CONVERTED_VIDEOS_FOLDER = Path('processed/')

MAX_FILENAME_LENGTH = 16

logger = logger.Logger(__name__, logging.DEBUG)
logger.add_stream_handler(logging.DEBUG)
logger.add_file_handler(logging.DEBUG)


def is_video(path: Path) -> bool:
    """
    :param path: Path to file.
    :return: bool, check whether the file conversion is supported.
    """
    try:
        return mimetypes.guess_type(path)[0].startswith('video')
    except AttributeError:
        return False


def short_filename(path: Path,
                   length: int = MAX_FILENAME_LENGTH) -> str:
    """
    Short the filename, remove its parent dirs,
    and add ... inside the name.

    :param path: Path to the file.
    :param length: int, expected name length.

    :return: str, shorted file name.
    """
    shorted_name = Path(path).name
    if len(shorted_name) > length:
        shorted_name = ''.join(
            shorted_name[:length // 2].strip() +
            '...' +
            shorted_name[-length // 2:].strip())
    return shorted_name


def get_size(path: Path,
             decimal_places: int = 1) -> float:
    """
    Get file size in MB, rounded to decimal_places.

    :param path: Path to the file.
    :param decimal_places: int, count of sighs after dor in result value.

    :return: float, rounded size of the file in MB.
    """
    if not path.exists():
        return -1

    return round(os.path.getsize(path) / 1024**2, decimal_places)


def get_info(from_: Path = None,
             to_: Path = None,
             *,
             short: bool = False) -> str:
    """
    Short the file names, add their sizes.

    :param from_: Path to the file to be converted.
    :param to_: Path to the file result file. None by default.
    :param short: bool, short file names ot not.

    :return: str, str with this info for log messages.
    """
    short = short_filename if short else (lambda path: path)
    res = ''

    if from_ is not None:
        res += f"'{short(from_)}', {get_size(from_)}MB"
    if to_ is not None:
        res += bool(from_) * ' to '
        res += f"'{short(to_)}'" + to_.exists() * f"{get_size(to_)}MB"

    return res


def convert(from_: Path,
            to_: Path,
            *,
            force: bool = False) -> None:
    """
    Convert a video to another video format.

    :param from_: Path to video to be converted.
    :param to_: Path to result file.
    :param force: bool, rewrite existing to_ file if True.
     False by default.
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
            raise exceptions.FileEvenExistsError(f"'{to_}' even exists")
    if not (is_video(from_) and is_video(to_)):
        raise exceptions.WrongExtensionError(
            f"'{from_.suffix}' or '{to_.suffix}' is wrong extension")

    logger.debug(f"Converting {get_info(from_)}")

    try:
        ff = ffmpy.FFmpeg(
            inputs={from_: None},
            outputs={to_: None}
        )

        ff.run()
    except Exception as e:
        logger.error(f"{e}\n while converting '{from_}' file")
        raise

    logger.debug(f"Converting {get_info(from_, to_)} completed")


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
    except Exception:
        pass
    else:
        # move processed video
        os.rename(from_, CONVERTED_VIDEOS_FOLDER / from_)
        logger.debug(
            f"Converted successfully, source file {short_filename(from_, 8)} "
            f"moved to {CONVERTED_VIDEOS_FOLDER}"
        )


def is_item_valid(path: Path,
                  max_size: int) -> bool:
    """
    Check whether the item is a valid video file to convert.

    :param path: Path to the file.
    :param max_size: int, max size of the file.

    :return: bool, whether the item is valid.
    """
    return is_video(path) and get_size(path) <= max_size


def validate_videos(base_path: Path,
                    max_size: int) -> Iterator[Tuple[Path, bool]]:
    """
    Get path to file and status whether
    the file is valid to convert.

    Skip all files (dirs) with no extension.

    :param base_path: Path to the folder from
    where get files to convert.
    :param max_size: int, max size of the file in MB.
    If length of the file is > max_size, regard it's invalid.

    :return: tuple of Path and bool.
    """
    for item in os.listdir(base_path):
        item = Path(item)
        if item.suffix:
            yield item, is_item_valid(item, max_size)


def files(base_path: Path,
          dest_path: Path,
          count: int,
          max_size: int) -> Iterator[Tuple[Path, Path]]:
    """
    Yield path to valid source file to be
    converted and destination path.

    :param base_path: Path to the folder from
    where get files to convert.
    :param dest_path: Path to the folder
    where store the results.
    :param count: int, count of files to convert.
    -1 if you need to convert all files.
    :param max_size: int, max size of the
    file to be converted in MB.

    :return: yield tuple of Path to valid
    source file and destination file.
    """
    processed = 0
    for from_, is_ok in validate_videos(base_path, max_size):
        if count != -1 and processed >= count:
            return

        if is_ok:
            processed += 1
            to_ = change_suffix_to_mp4(from_)
            yield from_, dest_path / to_


def validate(base_path: Path,
             max_size: int) -> None:
    """
    Print which files are valid to be converted but which not.

    :param base_path: Path to the folder from 
    where get files to convert.
    :param max_size: int, max size of the file to be converted in MB.
    If length of the file is > max_size, regard it's invalid.

    :return: None.
    """
    valid = invalid = 0
    for path, is_valid in validate_videos(base_path, max_size):
        print(colorama.Fore.GREEN if is_valid else colorama.Fore.RED,
              "Processing", end='', sep='')

        if is_valid:
            valid += 1
            print(f"{get_info(path, short=True)} is valid".rjust(50, '.'))
        else:
            invalid += 1
            print(f"{get_info(path, short=True)} is invalid".rjust(50, '.'))

    print(colorama.Fore.GREEN, "=" * 60, colorama.Fore.RESET, sep='')
    print(f"Total files count: {len(os.listdir(base_path))}")
    if valid == invalid == 0:
        print(f"No video found")
        return

    print(f"Total videos count: {valid + invalid}\n")
    if invalid == 0:
        print(f"All {valid} videos are valid")
    else:
        print(f"Total valid videos: {valid}")
        print(f"Total invalid videos: {invalid}")


def convert_all(base_path: Path,
                dest_path: Path,
                count: int,
                max_size: int) -> None:
    """
    Start converting in some processes.

    Processes count is equal to count of cpu cores - 1
    (or 1 if there's only one cpu core).

    :param base_path: Path to the folder from 
    where get files to convert.
    :param dest_path: Path to the folder where store the results.
    :param count: int, count of files to be converted convert.
    -1 if you want to convert all files.
    :param max_size: int, max size of the file to be converted in MB.

    :return: None.
    """
    os.makedirs(DEST_FOLDER, exist_ok=True)
    os.makedirs(CONVERTED_VIDEOS_FOLDER, exist_ok=True)

    processes_count = mp.cpu_count() - 1 or 1
    with mp.Pool(processes_count) as pool:
        pool.starmap(
            convert_file_to_mp4, files(base_path, dest_path, count, max_size)
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a video file to .mp4"
    )
    parser.add_argument(
        '-v', '--validate',
        help="See which videos might be converted.",
        action="store_true",
        default=False,
        dest='validate',
        required=False
    )
    parser.add_argument(
        '-c', '--convert',
        type=int,
        help="Set count of videos to convert. If -1 "
             "all files will be converted. 0 by default.",
        default=0,
        dest="count",
        required=False
    )
    parser.add_argument(
        '-p', '--start-path',
        help="Path to dir where there are videos to convert. "
             "Current dir by default.",
        type=Path,
        default=Path('.'),
        dest='start_path',
        required=False
    )
    parser.add_argument(
        '-d', '--destination-path',
        help=f"Path to where store processed videos. "
             f"'{DEST_FOLDER}' by default.",
        type=Path,
        default=DEST_FOLDER,
        dest='dest_path',
        required=False
    )
    parser.add_argument(
        '--max-size',
        help="Max size of the file in MB. If file size > it, "
             "skip this file. 10MB by default.",
        type=int,
        default=10,
        dest='max_size',
        required=False
    )
    parser.add_argument(
        '--stream-handler-level',
        help="Level of the stream handler.",
        type=str,
        choices=("debug", "info", "warning", "error", "critical"),
        default="debug",
        dest="stream_handler_level",
        required=False
    )
    parser.add_argument(
        '--file-handler-level',
        help="Level of the file handler.",
        type=str,
        choices=("debug", "info", "warning", "error", "critical"),
        default="debug",
        dest="file_handler_level",
        required=False
    )
    args = parser.parse_args()

    logger.set_stream_handler_level(args.stream_handler_level)
    logger.set_file_handler_level(args.file_handler_level)

    if args.validate:
        validate(args.start_path, args.max_size)
    if count := args.count:
        logger.info("Converting started...")
        start = time.perf_counter()

        convert_all(args.start_path, args.dest_path, count, args.max_size)

        ex_time = round(time.perf_counter() - start, 2)
        logger.info("Converting <= %s videos completed by %s",
                    count, ex_time)


if __name__ == "__main__":
    main()
