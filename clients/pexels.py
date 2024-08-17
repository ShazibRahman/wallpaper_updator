import asyncio
import logging
import os
from hashlib import sha256
from io import BytesIO

import aiohttp
from PIL import Image
from config.config import config
from decorators.retry import retry
from config.secrets import secrets


async def _download_image(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.read()
            image = Image.open(BytesIO(data))
            return image
        else:
            logging.error(f"Failed to download image from {url}")
            return None


def check_if_image_already_exists(url_hash, image_dir):
    for file in os.listdir(image_dir):
        if url_hash in file:
            return True
    return False


class PexelsImageDownloader:

    def __init__(self, query, queue: int, session: aiohttp.ClientSession, directory, target_resolution=(1920, 1080),
                 per_page=15):
        self.query = query
        self.target_resolution = target_resolution
        self.per_page = per_page
        self.api_url = 'https://api.pexels.com/v1/search'
        self.headers = {
            'Authorization': secrets["pexel_api_key"]
        }
        self.image_dir = directory
        self.count = 0
        self.queue = queue
        self.session = session
        self._create_directory()

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
        print(f'Original resolution: {original_width}x{original_height}')
        width_diff = original_width - target_width
        height_diff = original_height - target_height
        # Define a threshold for resolution closeness
        threshold = -100  # This can be adjusted based on preference
        return width_diff >= threshold and height_diff >= threshold

    @retry(retries=3, delay=1)
    async def download_and_resize_images(self, no_of_images: int):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            params = {
                'query': self.query,
                'per_page': self.per_page,
            }
            async with session.get(self.api_url, params=params, timeout=config['timeout']) as response:
                if response.status == 200:
                    data = await response.json()
                    photos = data.get('photos', [])
                    for i, photo in enumerate(photos):
                        if self.count >= no_of_images:
                            return self.queue
                        image_url = photo['src']['original']  # Download the highest quality available
                        file_name = f'{self.query}_pexels_%s.jpg'
                        await self._process_image(session, image_url, file_name)
                else:
                    logging.info(f'Failed to retrieve photos. Status code: {response.status}')

    async def _process_image(self, session, image_url, file_name):
        image = await _download_image(session, image_url)
        if image and self._is_resolution_close(image):
            resized_image = self._resize_image(image)
            url_hash: str = sha256(image_url.encode()).hexdigest()
            if check_if_image_already_exists(url_hash, self.image_dir):
                logging.info(f'Skipping {file_name % url_hash} as it already exists')
                return
            file_name_with_hash = file_name % url_hash

            self._save_image(resized_image, file_name_with_hash)
            self.count += 1
        else:
            logging.info(f'Skipping {file_name} due to resolution mismatch')


# Usage example
if __name__ == "__main__":
    downloader = PexelsImageDownloader(query='nature', directory='downloaded_images', target_resolution=(1920, 1080),
                                       per_page=15, queue=0, session=aiohttp.ClientSession())
    asyncio.run(downloader.download_and_resize_images(5))
