tags: list[str] = [
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
    "butterfly",
    "flower",
    "sunrise",
    "skyline",
    "northern lights",
    "forest rain",
    "garden flowers",
    "sky stars",
]
config: dict[str:str | int | float | list] = {
    "check_internet_connection": True,
    "run_after_every_hour": 16,
    "not_delete_from_last_day": 7,
    "tags": tags,
    "no_of_images_to_download": 2,
    "force_download": False,
    "log_file": "wallpaper_updator.log",
    "lock_file": "wallpaper_updator.lock",
    "last_run_file": "last_run.txt",
    "timeout": 20,
    "clear_images_data_after_days": 90,

}

if __name__ == "__main__":
    print(tags)
