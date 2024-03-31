import logging
import os
import uuid
import aiohttp
from Decorators.check_internet_connectivity import check_internet_connection
import asyncio

height,width = "2048x1080".split("x")
api_key = "33208678-2727b1eb70c1c232cbf99b821"

class Pixabay:
    def __init__(self,dir_patch):
        self.api_key = api_key
        self.dir_path = dir_patch

    async def get_images(self,session:aiohttp.ClientSession, query,images=5,queue_no=0):
        page =1
        self.query = query
        query = query.replace(" ","&")
        self.queue_no = queue_no
        logging.info("Downloading image with tag %s at queue %s", query, queue_no)

        async with session.get(
            f"https://pixabay.com/api/?key={self.api_key}&q={query}&image_type=photo&page={page}&orientation=horizontal") as response:
            if response.status == 200:
                return await self._download_urls( self._prepare_url(await response.json(),images),session)
            else:
                return None
    def _prepare_url(self, response:dict,images:int):
        if response:
            urls = []
            for image in response["hits"]:
                urls.append(image["largeImageURL"])
            return urls[:images]
        else:
            return []
    async def _download_urls(self, urls:list,session:aiohttp.ClientSession):
        if check_internet_connection():
            for url in urls:
                async with session.get(url) as response:
                    print(response.content_length)
                    print(response.status)
                    print(self.dir_path)
                    if response.status == 200:
                        logging.info("Image downloaded for queue %s", self.queue_no)
                        if not os.path.exists(self.dir_path):
                            os.makedirs(self.dir_path)
                        logging.info(self.dir_path)
                        image_path = os.path.join(
                            self.dir_path, f"{self.query.replace(',', '_')}_{uuid.uuid4()}_pixabay.jpg"
                        )
                        with open(image_path, "wb") as file:
                            content = await response.read()
                            file.write(content)

                    else:
                        logging.error("failed to download image response failed with ", response.status)


async def main():
    async with aiohttp.ClientSession() as session:
        pixabay = Pixabay(dir_patch=os.path.join(os.path.dirname(__file__),"..", 'wallpaperT'))
        # pixabay.dir_path = os.path.join(os.path.dirname(__file__),"..", wallpaper)
        urls = await pixabay.get_images(session,"lights",5,queue_no=1)
        print(urls)

if __name__ == "__main__":
    asyncio.run(main())