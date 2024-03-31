import logging
import asyncio
from functools import wraps
from time import sleep
from typing import Callable, Any, Union


def retry(retries: int = 3, delay: float = 1) -> Callable:
    """
    Attempt to call a function, if it fails, try again with a specified delay.

    :param retries: The max amount of retries you want for the function call
    :param delay: The delay (in seconds) between each function retry
    :return:
    """

    # Don't let the user use this decorator if they are high
    if retries < 1 or delay <= 0:
        raise ValueError('Are you high, mate?')

    def decorator(func: Union[Callable, Callable[..., Any]]) -> Union[Callable, Callable[..., Any]]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            for i in range(1, retries + 1):  # 1 to retries + 1 since upper bound is exclusive
                try:
                    logging.debug(f'Running ({i}): {func.__name__}()')
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Break out of the loop if the max amount of retries is exceeded
                    if i == retries:
                        logging.error(f'Error: {repr(e)}.')
                        logging.error(f'"{func.__name__}()" failed after {retries} retries.')
                        break
                    else:
                        logging.debug(f'Error: {repr(e)} -> Retrying...')
                        await asyncio.sleep(delay)  # Add a delay before running the next iteration

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            for i in range(1, retries + 1):  # 1 to retries + 1 since upper bound is exclusive
                try:
                    logging.debug(f'Running ({i}): {func.__name__}()')
                    return func(*args, **kwargs)
                except Exception as e:
                    # Break out of the loop if the max amount of retries is exceeded
                    if i == retries:
                        logging.error(f'Error: {repr(e)}.')
                        logging.error(f'"{func.__name__}()" failed after {retries} retries.')
                        break
                    else:
                        logging.debug(f'Error: {repr(e)} -> Retrying...')
                        sleep(delay)  # Add a delay before running the next iteration

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
