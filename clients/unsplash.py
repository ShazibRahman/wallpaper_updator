import asyncio
import logging
import os
import uuid

import aiohttp
from config.config import config
from decorators.retry import retry


def get_screen_resolution():
    cmd = "xrandr | grep '*' | cut -d' ' -f4"
    result = os.popen(cmd).read().strip() # well this doesnt work when you run your script through a cron job because cron job does not have access to the display and also not on windows or mac so you need to find a better way to get the screen resolution
    try:
        width, height = map(int, result.split('x'))
    except ValueError:
        width, height = 1920, 1080 # default resolution if the command fails
    return width, height


website = "http://source.unsplash.com/random/{dimension}"


@retry(retries=3, delay=1)
async def download_random_image_unsplash(
        session: aiohttp.ClientSession, tag: str, queue_no: int, dir_path: str
) -> int:
    """
    Downloads a random image using the provided aiohttp ClientSession.

    Args:
        session (aiohttp.ClientSession): The aiohttp ClientSession to use for the request.

    Returns:
        None: This function does not return anything.
    """

    logging.info("Downloading image with tag %s at queue %s", tag, queue_no)
    width, height = get_screen_resolution()
    dimension = f"{width}x{height}"
    logging.debug("downloading image with dimension %s", dimension)
    response = None

    response = await session.get(
        website.format(dimension=dimension),
        params=tag,
        timeout=config['timeout'],
        ssl=False
    )
    if response is None:
        logging.error("failed to download image for queue %s", queue_no)
        return -1
    if response.status == 200:
        if "404" in response.url.path.lower():
            logging.error("Image not found. for queue %s", queue_no)
            return -1
        if response.content_length is None or response.content_length == 0:
            logging.error("Image is empty. for queue %s", queue_no)
            return -1
        logging.info(
            "Image downloaded for queue %s",
            queue_no,
        )

        # Download the image
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        image_path = os.path.join(
            dir_path, f"{tag.replace(',', '_')}_{uuid.uuid4()}_unsplash.jpg"
        )
        with open(image_path, "wb") as file:
            content = await response.read()
            file.write(content)

    else:
        logging.error(
            "failed to download image response failed with %s for queue %s ",
            response.status,
            queue_no,
        )
        return -1
    return queue_no


async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [download_random_image_unsplash(session, "lights", queue_no=_ + 1) for _ in range(10)]

        results = await asyncio.gather(*tasks)
        print(results)


if __name__ == "__main__":
    wallpaper = "wallpaperD"
    current_directory = os.path.dirname(os.path.realpath(__file__))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                f"{current_directory}/wallpaper_updator.log", mode="a", encoding="utf-8"
            ),
        ],
    )

    asyncio.run(main())
