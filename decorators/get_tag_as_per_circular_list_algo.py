import asyncio
from pathlib import Path
import io
import atexit
from decorator_utils.singelton import singleton_with_no_parameters

INDEX_FILE = Path(__file__).parent.parent.joinpath("data", "circle_index.txt")
print(INDEX_FILE)


def save_index(index: int):
    with io.open(INDEX_FILE, "w") as f:
        f.write(str(index))


def load_index() -> int:
    if Path(INDEX_FILE).exists():
        with io.open(INDEX_FILE, "r") as f:
            return int(f.read().strip())
    return 0


@singleton_with_no_parameters
class GetTagAsPerCircularListAlgo:
    def __init__(self, tags: list[str]):
        self.tags = tags

        self.index = load_index()
        if self.index is None:
            self.index = 0
        atexit.register(self.__del__)

    def get_next_tag(self) -> str:
        print("inside get_next_tag")
        tag = self.tags[self.index]
        print(self.index)

        self.index = (self.index + 1) % len(self.tags)
        print(tag)
        return tag

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("inside aexit")
        save_index(self.index)

    def __del__(self):
        print("inside del")
        save_index(self.index)

# async def main():
#     tags = [
#         "sky",
#         "beach",
#         "waterfall",
#         "night",
#         "mountain",
#         "sunset",
#         "river",
#         "landscape",
#         "forest",
#         "rain",
#         "ocean",
#         "sunrise",
#         "skyline",
#         "northern lights",
#         "stars",
#         "coral reef",
#         "desktop background",
#         "jungle",
#         "desert",
#         "cave",
#         "volcano",
#         "iceberg",
#         "lake",
#         "moon",
#         "clouds",
#         "aurora",
#         "fog"

#     ]
#     obj = GetTagAsPerCircularListAlgo(tags)

#     jobs  =  [asyncio.create_task(asyncio.to_thread(obj.get_next_tag)) for
#               _ in range(100)]
#     await asyncio.gather(*jobs)


# if __name__ == "__main__":
#   asyncio.run(main())
