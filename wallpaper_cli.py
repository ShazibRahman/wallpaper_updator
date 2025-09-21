import os
from datetime import datetime, timedelta

import click
from wallpaper_updator import (
    delete_current_wallpaper as del_cur_walp,
    set_wallpaper,
)  # noqa
from wallpaper_updator import config

current_directory = os.path.dirname(os.path.realpath(__file__))


@click.group()
def cli():
    pass


@cli.command()
@click.option("--open-folder", default=True, is_flag=True, help="Open the folder")
def open_folder(open_folder: bool):  # noqa
    if open_folder:
        wallpaper_path = os.path.join(current_directory, "wallpaper")
        print(wallpaper_path)
        os.system(f"nautilus {wallpaper_path}")


@cli.command()
@click.option("--last-run", default=True, is_flag=True, help="Show the last run time")
def last_run(last_run):  # noqa
    if last_run:
        with open(
            os.path.join(current_directory, "last_run.txt"), "r", encoding="utf-8"
        ) as file:
            data_read = file.read()
            last_run_edited = float(data_read) if data_read else 0

            # convert last_run from seconds to date
            last_run_edited = datetime.fromtimestamp(last_run_edited)
            last_run_edited = last_run_edited.strftime("%Y-%m-%d %H:%M:%S")
            print(last_run_edited)


@cli.command()
@click.option(
    "--show-logs", default=True, is_flag=True, help="tail wallpaper_updator.log"
)
def show_logs(show_logs):  # noqa
    if show_logs:
        os.system(f"tail -n 40 -f  {current_directory}/wallpaper_updator.log")


@cli.command()
@click.option("--next-run", default=True, is_flag=True, help="Show the next run time")
def next_run(next_run):
    if next_run:
        with open(
            os.path.join(current_directory, "last_run.txt"), "r", encoding="utf-8"
        ) as file:
            data_read = file.read()
            last_run_edited = float(data_read) if data_read else 0

            # convert last_run from seconds to date
            last_run_edited: datetime = datetime.fromtimestamp(last_run_edited)

            next_run_datetime = last_run_edited + timedelta(
                hours=config["run_after_every_hour"]
            )
            print(next_run_datetime.strftime("%Y-%m-%d %H:%M:%S"))


@cli.command()
@click.option(
    "--delete-current-wallpaper",
    default=True,
    is_flag=True,
    help="Delete the current wallpaper",
)
def delete_current_wallpaper(delete_current_wallpaper):
    if delete_current_wallpaper:
        del_cur_walp()
        set_wallpaper()


if __name__ == "__main__":
    cli()
