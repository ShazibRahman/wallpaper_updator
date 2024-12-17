from functools import wraps
from pathlib import Path
import ujson as json

TAG_COUNT_JSON_FILE_PATH = Path(__file__).parent.parent.joinpath("data", "tags_counts.json")

def read_tag_count_json()->dict:
    """
    Reads the tag count JSON file.

    Returns:
        dict: The tag count data.
    """
    with open(TAG_COUNT_JSON_FILE_PATH, "r") as file:
        return json.load(file)


def write_tag_count_json(data):
    """
    Writes the tag count data to the tag count JSON file.

    Args:
        data (dict): The tag count data.
    """
    with open(TAG_COUNT_JSON_FILE_PATH, "w") as file_to_write:
        json.dump(data, file_to_write, indent=4)
        
        
def choose_tag_with_least_usage(tags:list[str], tag_count:dict[str:str]):
    """
    Chooses a tag with the least usage count from the available tags.

    Args:
        tags (list[str]): The list of available tags.
        tag_count (dict[str:str]): The dictionary containing the count of each tag.

    Returns:
        str: The tag with the least usage count.
    """
    least_used_tag = tags[0]
    least_used_count = tag_count.get(tags[0], 0)
    for tag in tags:
        count = tag_count.get(tag, 0)
        if count < least_used_count:
            least_used_tag = tag
            least_used_count = count
    return least_used_tag

def add_tag_used_count_return_tag_with_least_usage(func):
    """
    Decorator that increments the count of how many times a tag has been used.

    Args:
        func (callable): The function to be decorated.

    Returns:
        callable: The decorated function.
    """

    @wraps(func)
    def wrapper(*args):
        tags:list[str] = args[0]
        tag_count = read_tag_count_json()
        _remove_tag_count_if_not_in_tags(tag_count, tags)
        tag_chosen = choose_tag_with_least_usage(tags, tag_count)
        tag_count[tag_chosen] = tag_count.get(tag_chosen, 0) + 1
        write_tag_count_json(tag_count)
        return tag_chosen
    return wrapper


def _remove_tag_count_if_not_in_tags(tag_count:dict[str:int], tags:list[str]):
    """
    Removes tags from the tag count dictionary if they are not in the list of tags.

    Args:
        tag_count (dict[str:str]): The tag count dictionary.
        tags (list[str]): The list of tags.
    """
    for tag in list(tag_count.keys()):
        if tag not in tags:
            del tag_count[tag]


if __name__ == "__main__":
    from config.config import tags
    tag_count = read_tag_count_json()
    _remove_tag_count_if_not_in_tags(tag_count, tags)
    write_tag_count_json(tag_count)