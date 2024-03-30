from datetime import datetime
import click
import os

current_directory = os.path.dirname(os.path.realpath(__file__))


@click.group()
def cli():
    pass


@cli.command()
@click.option("--open-folder",default=True, is_flag=True, help="Open the folder")
def open_folder(open_folder):
    wallpaper_path = os.path.join(current_directory, "wallpaper")
    print(wallpaper_path)
    os.system(f"nautilus {wallpaper_path}")


@cli.command()
@click.option("--last-run",default=True ,is_flag=True, help="Show the last run time")
def last_run(last_run):
    if last_run:
        with open(
            os.path.join(current_directory, "last_run.txt"), "r", encoding="utf-8"
        ) as file:
            data_read = file.read()
            last_run = float(data_read) if data_read else 0

            # convert last_run from seconds to date
            last_run = datetime.fromtimestamp(last_run)
            last_run = last_run.strftime("%Y-%m-%d %H:%M:%S")
            print(last_run)


if __name__ == "__main__":
    cli()
