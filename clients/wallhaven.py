import pathlib
import sys
from typing import TextIO, Any, Coroutine
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import quote
import os
import time
import logging
from decorator_utils.retry import retry
from decorator_utils import singleton
from decorator_utils.singelton import singleton_with_no_parameters

from config.config import config

ALREADY_DOWNLOADED_IMAGES_DATA_PATH: str | pathlib.Path = pathlib.Path(__file__).parent.parent.joinpath(
    'data').joinpath(
    "wallhaven_images.txt")


def prepare_json_data(file: TextIO) -> dict[str, float]:
    data = {}
    for line in file:
        key, value = line.strip().split(':')
        data[key] = float(value)
    return data


def read_json_file(file_path: str | pathlib.Path) -> dict:
    with open(file_path, 'r') as file:
        data = prepare_json_data(file)
    return data


def write_a_single_line(key: str, value: float):
    with open(ALREADY_DOWNLOADED_IMAGES_DATA_PATH, 'a') as file:
        file.write(f'{key}:{value}\n')


def check_if_image_already_exists(url_hash: str, data: dict) -> bool:
    if url_hash in data:
        return True
    data[url_hash] = time.time()
    return False


def clear_old_data():
    data = read_json_file(ALREADY_DOWNLOADED_IMAGES_DATA_PATH)
    current_time = time.time()
    key_to_delete = [key for key, value in data.items() if current_time - value > config['clear_images_data_after_days'] * 24 * 60 * 60]

    print(f"Deleting {len(key_to_delete)} images")
    for key in key_to_delete:
        del data[key]

    with open(ALREADY_DOWNLOADED_IMAGES_DATA_PATH, 'w') as file:
        for key, value in data.items():
            file.write(f'{key}:{value}\n')


@singleton_with_no_parameters
class WallhavenDownloader:
    def __init__(self, query, session: aiohttp.ClientSession, directory):
        self.base_url = None
        self.queue_no = None
        self.max_images = None
        self.query = query
        self.image_dir = directory
        self.session = session
        self._create_directory()
        clear_old_data()
        self.data_from_file = read_json_file(ALREADY_DOWNLOADED_IMAGES_DATA_PATH)
        self.count = 0

    async def fetch_image_page_links(self, query,page_no=1):
        print(f"🔍 Searching Wallhaven for: {query}")
        self.base_url = f"https://wallhaven.cc/search?q={quote(query)}&resolutions=1920x1080&page={page_no}"
        async with self.session.get(self.base_url) as res:
            soup = BeautifulSoup(await res.text(), "html.parser")
            links = [a['href'] for a in soup.select("figure.thumb > a.preview")]
        return links

    def _create_directory(self):
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)

    @retry(retries=3, delay=2)
    async def download_image(self, max_images, queue_no,query)-> Any | None:
        for page in range(1,5):
            page_urls = await self.fetch_image_page_links(query, page)
            if not page_urls:
                print(f"No more pages found for query: {query}")
                break
            print(f"Page {page})")
            for page_url in page_urls:

                async with self.session.get(page_url) as res:
                    soup = BeautifulSoup(await res.text(), "html.parser")
                    img_tag = soup.select_one("img#wallpaper")
                    if img_tag:
                        img_url = img_tag["src"]
                        basename = os.path.basename(img_url)
                        extracted_hash = basename.split("-")[1].split(".")[0]
                        file_path = os.path.join(self.image_dir, query+"_"+basename)

                        if check_if_image_already_exists(extracted_hash, self.data_from_file):
                            logging.debug(f'Skipping {file_path} as it already exists')
                            print(f"Skipped {file_path} as it already exists")
                            continue

                        async with self.session.get(img_url) as img_res:
                            with open(file_path, "wb") as f:
                                f.write(await img_res.read())
                                write_a_single_line(extracted_hash, time.time())
                        self.count += 1
                        if self.count >= max_images:
                            print(f"✅ Downloaded {self.count} images.")
                            return queue_no

                        print(f"✅ Downloaded: {file_path}")
        return None

    async def run(self, queue_no, max_images, query)->int:
        self.max_images = max_images
        self.queue_no = queue_no
        return await self.download_image(max_images, queue_no,query)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python wallhaven_downloader.py <search_tag>")
        sys.exit(1)

    tag = " ".join(sys.argv[1:])
    async with aiohttp.ClientSession() as session:
        downloader = WallhavenDownloader(query=tag, session=session, directory="wallhaven_images")
        await downloader.run(queue_no=1, max_images=10, query=tag)


if __name__ == "__main__":
    asyncio.run(main())
