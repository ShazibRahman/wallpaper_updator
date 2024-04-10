"""
This is a module-level docstring that provides an overview of the purpose
and functionality of this module.
"""
import asyncio
import logging
import math
import bisect
import os
import pathlib
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta

import aiohttp
import psutil
from Decorators.check_internet_connectivity import check_internet_connection , check_internet_connection_async_decorator
from clients.pixabay import Pixabay
from clients.unsplash import download_random_image_unsplash

WALLPAPER = "wallpaper"

PYTHON_RUNNUNG_FROM_CRON = os.environ.get("PYTHON_RUNNUNG_FROM_CRON")

os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1000/bus"

current_directory = os.path.dirname(os.path.realpath(__file__))
log_path = os.path.join(current_directory, "wallpaper_updator.log")
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

lock_file = f"{current_directory}/wallpaper_updator.lock"



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
    Acquires control by checking if a lock file exists. If the lock file does not exist, it creates one and writes the current process ID to it. If the lock file exists, it reads the process ID from it and compares it with the current process ID. If the process IDs match, it logs a message indicating that control is already acquired. If the process IDs do not match, it logs a message indicating that another instance of the program is already running with the process ID and exits.

    Parameters:
    - None

    Returns:
    - None
    """
    while os.path.exists(lock_file):
        with open(lock_file, "r", encoding="utf-8") as file:
            pid = file.read()
            if pid == str(os.getpid()):
                logging.info("Control already acquired.")
                return
            elif check_pid_exists(int(pid)):
                logging.info(
                    "Another instance of the program is already running with pid %s exiting...",
                    pid,
                )
                sys.exit(0)
            else:
                # Remove stale lock file
                release_control()

    with open(lock_file, "w", encoding="utf-8") as file:
        file.write(str(os.getpid()))
    logging.info("Control acquired.")


def release_control():
    """
    Removes the lock file and prints a message indicating that control has been released.
    """
    os.remove(lock_file)
    logging.info("Control released.")


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
    logging.info("Uncaught exception", exc_info=(exctype, value, traceback))


sys.excepthook = log_uncaught_exceptions
tags = [
    "nature",
    "tree",
    "sky",
    "beach",
    "waterfall",
    "night",
    "mountain",
    "garden",
    "sunset",
    "river",
    "landscape",
    "forest",
    "rain",
    "bird",
    "ocean",
    "fish in water",
    "butterfly",
    "flower",
    "sunrise",
    "skyline",
    "northern lights",
    "forest rain"
]

tag_already_used = set()


def get_random_tag_or_tag_from_sys_args_for_unsplash():
    """
    Generate a random tag or retrieve a tag from the system arguments.

    Returns:
        str: The randomly chosen tag or the tag from the system arguments, followed by ",dark".
    """

    return f"{sys.argv[1] if len(sys.argv) > 1 else get_random_tag()},dark"


def get_random_tag_or_tag_from_sys_args_for_pixabay():
    """
    Generate a random tag or retrieve a tag from the system arguments.

    Returns:
        str: The randomly chosen tag or the tag from the system arguments.
    """
    return sys.argv[1] if len(sys.argv) > 1 else get_random_tag()


def get_random_tag() -> str:
    global tag_already_used
    tag = random.choice(tags)
    while tag in tag_already_used:
        tag = random.choice(tags)
    tag_already_used.add(tag)
    return tag


async def download_random_image_with_cient(session: aiohttp.ClientSession, queue_no: int, client: str) -> int | None:
    match client:
        case "unsplash":
            return await download_random_image_unsplash(session,
                                                        get_random_tag_or_tag_from_sys_args_for_unsplash(),
                                                        queue_no,dir_path=wallpaper_directory)
        case "pixabay":
            return await Pixabay(dir_patch=wallpaper_directory).get_images(session,
                                              get_random_tag_or_tag_from_sys_args_for_pixabay(),
                                              images=1,
                                              queue_no=queue_no)
        case _:
            raise ValueError(f"Invalid client: {client}")


@check_internet_connection_async_decorator
async def download_random_images(force=False, nums=10):
    """
    Downloads random images asynchronously using aiohttp.

    Args:
        force (bool, optional): If True, force the download even if the last run was less than 48 hours ago. Defaults to False.
        nums (int, optional): The number of random images to download. Defaults to 10.

    Returns:
        None
    """
    last_run_file_path = os.path.join(current_directory, "last_run.txt")

    # check if there is an internet connection
    # list wallpaper directory
    list_of_files_wallpaper_directory = os.listdir(wallpaper_directory)

    if not force and not len(list_of_files_wallpaper_directory) == 0:
        try:
            with open(last_run_file_path, "r", encoding="utf-8") as file:
                data_read = file.read()
                last_run = float(data_read) if data_read else 0

                if time.time() - last_run < 24 * 60 * 60:
                    logging.info("last run was less than 48 hours ago")
                    return
        except FileNotFoundError as error:
            last_run = 0
            logging.error("error reading last run file witn %s ", error)

    async with aiohttp.ClientSession() as session:
        tasks = [download_random_image_with_cient(session, queue_no, get_random_client()) for queue_no in range(nums)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # here results contains asyncio TimeoutError if the download fails , handle the error and dont save the last run if more than 50% of the images are not downloaded
        # we must also count the timeout errors

        logging.info(f"{results =}")

        # how can we count errors and non zereos in the results
        error_count:int = 0

        for result in results:
            if not type(result)== type(0) or result <=0:
                error_count+=1

        if error_count >= 0.5 * nums:
            logging.error("more than 50% of the images are not downloaded")
            return




    with open(last_run_file_path, "w", encoding="utf-8") as file:
        file.write(str(time.time()))


def get_random_client() -> str:
    return random.choice(["unsplash"])


def weighted_choice_with_values(weighted_items: dict[str:float]):
    total_weight = sum(weighted_items.values())
    rand_val = random.uniform(0.60*total_weight, total_weight)
    cumulative_weight = 0
    for key, weight in weighted_items.items():
        cumulative_weight += weight
        if rand_val <= cumulative_weight:
            return key


def set_wallpaper():
    """
    Sets the wallpaper by randomly selecting an image from the "wallpaper" directory.

    Args:
        None

    Returns:
        None
    """
    file_list = os.listdir(os.path.join(current_directory, WALLPAPER))

    ## check if no images are there
    if len(file_list) == 0:
        logging.warning("no images found in wallpaper directory")
        return
    ## creating a dictionary of fileList with its respective timestamps
    file_list_with_timestamps: dict[str:float] = {
        file: os.path.getmtime(os.path.join(current_directory, WALLPAPER, file)) \
        for file in file_list
    }
    file_list_with_normalized_timestamps: dict[str:float] = normalize_timestamps(file_list_with_timestamps)

    file_selected_for_wallpaper: str = weighted_choice_with_values(file_list_with_normalized_timestamps)
    print(file_selected_for_wallpaper, file_list_with_normalized_timestamps[file_selected_for_wallpaper])

    image_path = pathlib.Path(current_directory).joinpath(WALLPAPER, file_selected_for_wallpaper)
    logging.info("setting wallpaper to %s", image_path)

    task1 = subprocess.run(
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

    task2 = subprocess.run(
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

def clear_directory(path, max_size=100):
    """
    Clear the given directory if its size is greater than 200 MB.

    Args:
        path (str): The path to the directory.

    Returns:
        None
    """
    unit = "MB"
    if (size := get_folder_size(path, unit)) <= max_size:
        # if the size of the folder is less than 200 MB, then return without deleting any files
        return

    logging.info(
        "clearing the wallpaper folder as it is taking more than %s MB of space",
        max_size,
    )

    # delete the file if its size is 0 bytes


    try:
        n = 5
        n_days = datetime.now() - timedelta(days=n)
        if os.path.exists(path):
            for file in os.listdir(path):
                file_path = os.path.join(path, file)
                if os.path.isfile(file_path):
                    modified_time = os.path.getmtime(file_path)
                    modified_datetime = datetime.fromtimestamp(modified_time)
                    if modified_datetime <= n_days:
                        logging.info(
                            "deleting %s because modified date %s  \
                            is greater than %s days",
                            file_path,
                            modified_datetime,
                            n,
                        )
                        os.remove(file_path)
        while get_folder_size(path, unit) > max_size:
            files_withFileStamp: dic[str:float] = {
                os.path.join(path, file): datetime.fromtimestamp(os.path.getmtime(os.path.join(path, file))) for file in
                os.listdir(path)}

            # get 2 oldest files
            oldest_files = sorted(files_withFileStamp.items(), key=lambda x: x[1])[:2]

            # delete oldest files
            for file, _ in oldest_files:
                logging.info("deleting %s", file)
                os.remove(file)

    except FileNotFoundError as error:
        logging.error("erro clearing the wallpaper folder with %s ", error)


def convert_size(size_bytes, unit="MB"):
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
    size = round(size_bytes / math.pow(base, size_unit), 2)
    return size


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
                    logging.info("Deleting empty file: %s", file_path)
                    os.remove(file_path)
                except OSError as e:
                    logging.error("Error deleting file: %s", e)
                    continue
            total_size += file_size

    logging.info("total files %s", total_files)

    return convert_size(total_size, unit)


async def main(is_forced=False):
    """
    Asynchronous function that serves as the entry point of the program.

    Args:
        is_forced (bool, optional): A flag indicating whether the download of random images should be forced. Defaults to False.

    Returns:
        None
    """

    acquire_control()
    await download_random_images(is_forced,nums=2)
    set_wallpaper()
    clear_directory(os.path.join(current_directory, "%s" % WALLPAPER))

    if PYTHON_RUNNUNG_FROM_CRON:
        logging.info(
            "started job as % s and running as cron %s",
            os.environ.get("USER", "CRON"),
            PYTHON_RUNNUNG_FROM_CRON,
        )
    release_control()


if __name__ == "__main__":
    WALLPAPER = "wallpaper"
    wallpaper_directory = f"{current_directory}/{WALLPAPER}"
    if not os.path.exists(wallpaper_directory):
        os.makedirs(wallpaper_directory)

    asyncio.run(main(False))
    # asyncio.run(main(True))
