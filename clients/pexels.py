import asyncio
import logging
import os
import pathlib
import time
from hashlib import sha256
from io import BytesIO, open
from typing import TextIO

import aiohttp
from PIL import Image
from config.config import config
from config.secrets import secrets
from decorator_utils import singleton
from decorator_utils import retry
from decorator_utils.singelton import  singleton_with_no_parameters
ALREADY_DOWNLOADED_IMAGES_DATA_PATH: str | pathlib.Path = pathlib.Path(__file__).parent.parent.joinpath(
    'data').joinpath(
    "pexels_images.txt")


async def _download_image(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.read()
            image = Image.open(BytesIO(data))
            return image
        else:
            logging.error(f"Failed to download image from {url}")
            return None


def prepare_json_data(file: TextIO) -> dict[str:float]:
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
class PexelsImageDownloader:

    def __init__(self, query, session: aiohttp.ClientSession, directory, target_resolution=(1920, 1080),
                 per_page=100):
        self.queue = None
        self.query = query
        self.target_resolution = target_resolution
        self.per_page = per_page
        self.api_url = 'https://api.pexels.com/v1/search'
        self.headers = {
            'Authorization': secrets["pexel_api_key"]
        }
        self.image_dir = directory
        self.count = 0
        self.session = session
        self._create_directory()
        clear_old_data()
        self.data_from_file = read_json_file(ALREADY_DOWNLOADED_IMAGES_DATA_PATH)

    def _create_directory(self):
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)

    def _resize_image(self, image):
        resized_image = image.resize(self.target_resolution, Image.Resampling.LANCZOS)
        return resized_image

    def _save_image(self, image, file_name):
        logging.debug(f'Saving image: {file_name}')
        image_path = os.path.join(self.image_dir, file_name)
        image.save(image_path)
        logging.debug(f'Saved {image_path}')

    def _is_resolution_close(self, image):
        original_width, original_height = image.size
        target_width, target_height = self.target_resolution
        target_resolution_ratio: float = target_width / target_height
        original_resolution_ratio: float = original_width / original_height
        if abs(target_resolution_ratio - original_resolution_ratio) < 0.01:
            return True
        return False

    @retry(retries=3, delay=1)
    async def download_and_resize_images(self,queue_no, no_of_images: int,query):
        self.queue = queue_no
        query = query
        

        async with aiohttp.ClientSession(headers=self.headers) as session:
            params = {
                'query': query,
                'per_page': self.per_page
            }
            for page in range(1,5):
                params['page'] = page

                async with session.get(self.api_url, params=params, timeout=config['timeout']) as response:
                    if response.status == 200:
                        data = await response.json()
                        photos = data.get('photos', [])
                        for i, photo in enumerate(photos):
                            
                            image_url = photo['src']['original']  # Download the highest quality available
                            file_name = f'{query}_pexels_%s.jpg'
                            result = await self._process_image(session, image_url, file_name,no_of_images)
                            if result:
                                return self.queue
                        # logging.info("processed %s images", self.count)
                    else:
                        logging.error(f'Failed to retrieve photos. Status code: {response.status}')
            return None

    async def _process_image(self, session, image_url, file_name,no_of_images):
        url_hash: str = sha256(image_url.encode()).hexdigest()

        if check_if_image_already_exists(url_hash, self.data_from_file):
            logging.debug(f'Skipping {file_name % url_hash} as it already exists')
            print(f"Skipped {file_name % url_hash} as it already exists")
            return
        image = await _download_image(session, image_url)
        if image and self._is_resolution_close(image):
            resized_image = self._resize_image(image)

            file_name_with_hash = file_name % url_hash

            self._save_image(resized_image, file_name_with_hash)
            write_a_single_line(url_hash, time.time())
            self.count += 1
            print(f"Downloaded {self.count} images")
            if self.count >= no_of_images:
                print("downloaded all images")

            return True
            
            logging.debug(f'Downloaded {file_name_with_hash}')
          
        else:
            logging.debug(f'Skipping {file_name} due to resolution mismatch')


# Usage example
if __name__ == "__main__":
    downloader = PexelsImageDownloader(query='nature', directory='downloaded_images', target_resolution=(1920, 1080),
                                       per_page=150, queue=0, session=aiohttp.ClientSession())
    asyncio.run(downloader.download_and_resize_images(5))
