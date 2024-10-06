"""
This is a module-level docstring that provides an overview of the purpose
and functionality of this module.
"""
import asyncio
import logging
import math
import os
import pathlib
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta

import aiohttp
import psutil
from clients import pixabay, unsplash, pexels  # noqa
from config.config import config  # noqa
from decorators.add_tag_used_count import add_tag_used_count_return_tag_with_least_usage
from decorators.check_internet_connectivity import check_internet_connection_async_decorator  # noqa

WALLPAPER = "wallpaper"

PYTHON_RUNNING_FROM_CRON = os.environ.get("PYTHON_RUNNING_FROM_CRON")

os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1000/bus"

current_directory = os.path.dirname(os.path.realpath(__file__))
log_path = os.path.join(current_directory, config['log_file'])
formatter = logging.Formatter(
    "%(levelname)s - (%(asctime)s): %(message)s (Line: %(lineno)d [%(filename)s])"
)

formatter.datefmt = "%m/%d/%Y %I:%M:%S %p"

logging.basicConfig(
    filename=log_path,
    filemode="a",
    level=logging.INFO,
    format="%(levelname)s - (%(asctime)s): %(message)s (Line: %(lineno)d [%(filename)s])",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logging.getLogger().addHandler(stream_handler)


def log_uncaught_exceptions(exctype, value, traceback):
    logging.exception("Uncaught exception", exc_info=(exctype, value, traceback))


sys.excepthook = log_uncaught_exceptions

lock_file = f"{current_directory}/{config['lock_file']}"


def check_pid_exists(pid):
    """
    Check if a process with the given PID exists.

    Args:
        pid (int): The PID of the process to check.

    Returns:
        bool: True if a process with the given PID exists, False otherwise.
    """
    return psutil.pid_exists(pid)


def normalize_timestamps(timestamps: dict[str:float]) -> dict[str:float]:
    """

    Args:
        timestamps:

    Returns:

    """

    min_timestamp: float = min(timestamps.values())
    max_timestamp: float = max(timestamps.values())
    delta = max_timestamp - min_timestamp
    normalized_timestamps_dict: dict[str:float] = {key: (timestamp - min_timestamp) / delta for key, timestamp in
                                                   timestamps.items()}
    return dict(sorted(normalized_timestamps_dict.items(), key=lambda x: x[1]))


def acquire_control():
    """
    Acquires control by checking if a lock file exists. If the lock file does not exist, it creates one and writes the
    current process ID to it. If the lock file exists, it reads the process ID from it and compares it with the current
    process ID. If the process IDs match, it logs a message indicating that control is already acquired.
    If the process IDs do not match, it logs a message indicating that another instance of the program
    is already running with the process ID and exits.

    Parameters:
    - None

    Returns:
    - None
    """
    while os.path.exists(lock_file):
        with open(lock_file, "r", encoding="utf-8") as file:
            pid = file.read()
            if pid == str(os.getpid()):
                logging.debug("Control already acquired.")
                return
            elif check_pid_exists(int(pid)):
                logging.error(
                    "Another instance of the program is already running with pid %s exiting...",
                    pid,
                )
                sys.exit(0)
            else:
                # Remove stale lock file
                release_control()

    with open(lock_file, "w", encoding="utf-8") as file:
        file.write(str(os.getpid()))
    logging.debug("Control acquired.")


def release_control():
    """
    Removes the lock file and prints a message indicating that control has been released.
    """
    os.remove(lock_file)
    logging.debug("Control released.")


# noinspection PyTypeChecker
def log_uncaught_exceptions(exctype, value, traceback):
    """
    Log uncaught exceptions and include the exception type, value, and traceback information.

    Parameters:
        exctype (type): The type of the uncaught exception.
        value (BaseException): The value of the uncaught exception.
        traceback (traceback): The traceback information of the uncaught exception.

    Returns:
        None: This function does not return a value.
    """
    logging.error("Uncaught exception", exc_info=(exctype, value, traceback))


sys.excepthook = log_uncaught_exceptions
tags = config["tags"]

tag_already_used = set()


def get_random_tag_or_tag_from_sys_args_for_unsplash():
    """
    Generate a random tag or retrieve a tag from the system arguments.

    Returns:
        str: The randomly chosen tag or the tag from the system arguments, followed by ",dark".
    """

    return f"{sys.argv[1] if len(sys.argv) > 1 else get_random_tag(tags)},dark"


def get_random_tag_or_tag_from_sys_args_for_pixabay():
    """
    Generate a random tag or retrieve a tag from the system arguments.

    Returns:
        str: The randomly chosen tag or the tag from the system arguments.
    """
    return sys.argv[1] if len(sys.argv) > 1 else get_random_tag(tags)

@add_tag_used_count_return_tag_with_least_usage
def get_random_tag(tags_to_be_used) -> str:
    ...


async def download_random_image_with_client(session: aiohttp.ClientSession, queue_no: int, client: str) -> int | None:
    match client:
        case "unsplash":
            return await unsplash.download_random_image_unsplash(session,
                                                                 get_random_tag_or_tag_from_sys_args_for_unsplash(),
                                                                 queue_no, dir_path=wallpaper_directory)
        case "pixabay":
            return await (
                pixabay.Pixabay(dir_patch=wallpaper_directory)
                .get_images(
                    session,
                    get_random_tag_or_tag_from_sys_args_for_pixabay(),
                    images=1,
                    queue_no=queue_no)
            )
        case "pexels":
            return await pexels.PexelsImageDownloader(
                query=get_random_tag_or_tag_from_sys_args_for_pixabay(),
                session=session,
                queue=queue_no,
                directory=wallpaper_directory,
                target_resolution=(1920, 1080),
                per_page=15
            ).download_and_resize_images(1)
        case _:
            raise ValueError(f"Invalid client: {client}")


@check_internet_connection_async_decorator
async def download_random_images(force=False, nums=10):
    """
    Downloads random images asynchronously using aiohttp.

    Args:
        force (bool, optional): If True, force the download even
         if the last run was less than 48 hours ago. Defaults to False.
        nums (int, optional): The number of random images to download. Defaults to 10.

    Returns:
        None
    """
    last_run_file_path = os.path.join(current_directory, config["last_run_file"])

    # check if there is an internet connection
    # list wallpaper directory
    list_of_files_wallpaper_directory = os.listdir(wallpaper_directory)
    logging.debug("downloading random images to folder %s", wallpaper_directory)

    if not force and not len(list_of_files_wallpaper_directory) == 0:
        try:
            with open(last_run_file_path, "r", encoding="utf-8") as file:
                data_read = file.read()
                last_run = float(data_read) if data_read else 0

                time_diff = time.time() - last_run
                least_time_diff_to_run_hrs = config["run_after_every_hour"]
                least_time_diff_to_run = least_time_diff_to_run_hrs * 60 * 60

                if time_diff < least_time_diff_to_run:
                    # logging.info(f"last run was less than {least_time_diff_to_run_hrs} hours ago")
                    return
        except FileNotFoundError as error:
            logging.error("error reading last run file witn %s ", error)

    async with aiohttp.ClientSession() as session:
        tasks = [download_random_image_with_client(session, queue_no, get_random_client()) for queue_no in range(nums)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # here results contains asyncio TimeoutError if the download fails , handle the error and don't save the last
        # run if more than 50% of the images are not downloaded we must also count the timeout errors

        # logging.info("results %s", results)

        # how can we count errors and non zereos in the results
        error_count: int = 0

        for result in results:
            if not isinstance(result, int) or result < 0:
                error_count += 1

        if error_count >= 0.5 * nums:
            logging.error("more than half of the images are not downloaded")
            return

        # save the last run time to the file only if all the images are downloaded

    with open(last_run_file_path, "w", encoding="utf-8") as file:
        file.write(str(time.time()))


def get_random_client() -> str:
    return random.choice(["pexels"])


def weighted_choice_with_values(weighted_items: dict[str:float]):
    total_weight = sum(weighted_items.values())
    rand_val = random.uniform(0.60 * total_weight, total_weight)
    cumulative_weight = 0
    for key, weight in weighted_items.items():
        cumulative_weight += weight
        if rand_val <= cumulative_weight:
            return key


def delete_current_wallpaper():
    """
    Deletes the current wallpaper by reading the path from the "wallpaper_path.txt" file.

    Returns:
        None
    """
    wallpaper_path_file = os.path.join(current_directory, "wallpaper_path.txt")
    if os.path.exists(wallpaper_path_file):
        with open(wallpaper_path_file, "r", encoding="utf-8") as file:
            wallpaper_path = file.read().strip()
            if os.path.exists(wallpaper_path):
                os.remove(wallpaper_path)
            else:
                logging.warning("Wallpaper path does not exist: %s", wallpaper_path)
    else:
        logging.warning("Wallpaper path file does not exist: %s", wallpaper_path_file)


def write_to_file(file_path: str, data: str):
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(data)


def set_wallpaper():
    """
    Sets the wallpaper by randomly selecting an image from the "wallpaper" directory.

    Returns:
        None
    """
    file_list = os.listdir(os.path.join(current_directory, WALLPAPER).strip())
    if len(file_list) == 0:
        logging.warning("no images found in wallpaper directory")
        return

    image_path = pathlib.Path(current_directory).joinpath(WALLPAPER, random.choice(file_list))
    logging.debug("setting wallpaper to %s", image_path)
    write_to_file(os.path.join(current_directory, "wallpaper_path.txt"), str(image_path))

    subprocess.run(
        [
            "/usr/bin/gsettings",
            "set",
            "org.gnome.desktop.background",
            "picture-uri-dark",
            f"file://{image_path}",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    subprocess.run(
        [
            "/usr/bin/gsettings",
            "set",
            "org.gnome.desktop.background",
            "picture-options",
            "scaled",
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def clear_directory(path, no_of_days_int: int = 10):
    """
    Clear the given directory if its size is greater than 200 MB.

    Args:
        no_of_days_int:
        path (str): The path to the directory.

    Returns:
        None
    """

    try:

        n_days = datetime.now() - timedelta(days=no_of_days_int)
        if os.path.exists(path):
            for file in os.listdir(path):
                file_path = os.path.join(path, file)

                if os.path.isfile(file_path):
                    if convert_size(os.path.getsize(file_path), "KB") < 1:
                        logging.debug("deleting %s because size is less than 1 KB", file_path)
                        os.remove(file_path)
                        continue

                    modified_time = os.path.getmtime(file_path)
                    modified_datetime = datetime.fromtimestamp(modified_time)

                    if modified_datetime <= n_days:
                        logging.info(
                            "deleting %s because modified date %s is greater than %s days",
                            file_path,
                            modified_datetime,
                            no_of_days_int,
                        )
                        os.remove(file_path)

    except FileNotFoundError as error:
        logging.error("error clearing the wallpaper folder with %s ", error)


def convert_size(size_bytes, unit="MB", rounding=2):
    """
    Function to convert the given size in bytes to a specified unit.

    Parameters:
        - size_bytes (int): The size in bytes to be converted.
        - unit (str, optional): The unit to convert the size to. Defaults to "MB".

    Returns:
        - float: The size in the specified unit.
    """

    if size_bytes == 0:
        return 0

    # Define the units and their respective labels
    units = ["B", "KB", "MB", "GB", "TB"]
    if unit not in units:
        unit = "MB"  # fall back to MB if unit is invalid
    base = 1000
    size_unit = units.index(unit)
    size = round(size_bytes / math.pow(base, size_unit), rounding)
    return size


# not being  used
def get_folder_size(folder_path, unit="MB"):
    """
    Calculates the size of a folder.

    Parameters:
    - folder_path (str): The path to the folder.
    - unit (str, optional): The unit of the size. Defaults to "MB".

    Returns:
    - float: The size of the folder in the specified unit.

    """
    total_size = 0
    total_files = 0

    for path, _, files in os.walk(folder_path):
        total_files += len(files)
        for file in files:
            file_path = os.path.join(path, file)
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                try:
                    logging.debug("Deleting empty file: %s", file_path)
                    os.remove(file_path)
                except OSError as e:
                    logging.error("Error deleting file: %s", e)
                    continue
            total_size += file_size

    return convert_size(total_size, unit)


async def main():
    """
    Asynchronous function that serves as the entry point of the program.

        Defaults to False.

    Returns:
        None
    """

    acquire_control()
    clear_directory(os.path.join(current_directory, WALLPAPER.strip()),
                    no_of_days_int=config['not_delete_from_last_day'])
    await download_random_images(config['force_download'], nums=config['no_of_images_to_download'])
    set_wallpaper()

    if PYTHON_RUNNING_FROM_CRON:
        logging.debug(
            "started job as % s and running as cron %s",
            os.environ.get("USER", "CRON"),
            PYTHON_RUNNING_FROM_CRON,
        )
    release_control()


if __name__ == "__main__":
    WALLPAPER = os.environ.get("FOLDER_PATH", "wallpaper")

    wallpaper_directory = f"{current_directory}/{WALLPAPER}"
    if not os.path.exists(wallpaper_directory):
        os.makedirs(wallpaper_directory)

    asyncio.run(main())
    # asyncio.run(main(True))

    print(convert_size(234, unit="KB", rounding=100))
