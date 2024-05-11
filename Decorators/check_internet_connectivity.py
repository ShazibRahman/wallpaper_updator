import functools
import socket
import logging


@functools.lru_cache(maxsize=1)
def check_internet_connection():
    try:
        # Connect to a well-known website
        socket.create_connection(("www.google.com", 80))
        logging.debug("Internet connection is available")
        return True
    except OSError:
        return False


def check_internet_connection_decorator(func):
    """
    Decorator that checks if there is an internet connection available before executing the decorated function.

    Args:
        func (callable): The function to be decorated.

    Returns:
        callable: The decorated function.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if check_internet_connection():
            return func(*args, **kwargs)
        else:
            print("No internet connection available.")

    return wrapper


def check_internet_connection_async_decorator(func):
    """

    Args:
        func:

    Returns:

    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if check_internet_connection():
            return await func(*args, **kwargs)
        else:
            print("No internet connection available.")

    return wrapper


@check_internet_connection_decorator
def some_function():
    """
    A function that requires an internet connection.
    """
    # Code that requires an internet connection
    pass


if __name__ == "__main__":
    some_function()
