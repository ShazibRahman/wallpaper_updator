tags: list[str] = [
    "sky",
    "beach",
    "waterfall",
    "night",
    "mountain",
    "sunset",
    "river",
    "landscape",
    "forest",
    "rain",
    "ocean",
    "sunrise",
    "skyline",
    "northern lights",
    "stars",
    "coral reef",
    "desktop background",
    "jungle"

]
config: dict[str:str | int | float | list] = {
    "check_internet_connection": True,
    "run_after_every_hour": 20,
    "not_delete_from_last_day": 7,
    "tags": tags,
    "no_of_images_to_download": 2,
    "force_download": False,
    "log_file": "wallpaper_updator.log",
    "lock_file": "wallpaper_updator.lock",
    "last_run_file": "last_run.txt",
    "timeout": 20,
    "clear_images_data_after_days": 180,

}

if __name__ == "__main__":
    print(tags)
