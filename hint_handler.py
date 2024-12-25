import json
import logging
import re
import time
from typing import Optional

from location_file_handler import get_item_data, ALIASES_KEY, ITEM_LOCATIONS_KEY, ITEMS_KEY
from utils import canonicalize

log = logging.getLogger(__name__)

DEFAULT_HINT_COOLDOWN_MIN = 30

player_re = re.compile(r"^@?player(\d+)$")  # player14, @Player14


def get_player_number(player: str) -> int:
    match = player_re.search(player.lower())
    if match:
        return int(match.group(1)) - 1
    raise ValueError()


def get_hint_response(player: str, item: str, author_id: int, guild_id) -> str:
    try:
        player_number = get_player_number(player)
    except ValueError:
        return f"Unrecognized player {player}. (Did you format without spaces as in \"player5\"?)"

    data = get_item_data(guild_id)
    locs = data[ITEMS_KEY]
    if not len(locs):
        return "No data is currently stored. (Use !set-log to upload a spoiler log.)"

    canonical_item = canonicalize(item)
    if canonical_item not in locs:
        canonical_item = data[ALIASES_KEY].get(canonical_item)
    if canonical_item is None:
        return f"Item {item} not recognized. (Not case-sensitive.) Try !search <keyword> to find it!"

    item_data = locs[canonical_item]
    if player_number < 0 or player_number >= len(item_data[ITEM_LOCATIONS_KEY]):
        return f"Invalid player number {player_number + 1}."

    hint_wait_time = get_hint_wait_time(author_id, guild_id)
    if hint_wait_time is not None:
        return f"Please chill for another {hint_wait_time}"

    player_locs_for_item = item_data[ITEM_LOCATIONS_KEY][player_number]
    if not len(player_locs_for_item):
        return f"For some reason there are no locations listed for {player}'s {item}........ sorry!!! There must be something wrong with me :( Please report."
    else:
        return "\n".join(player_locs_for_item)


def get_hint_timestamps_filename(guild_id):
    return f"{guild_id}-hint_timestamps.json"


def format_wait_time(wait_time_sec: int) -> str:
    m = wait_time_sec // 60
    s = wait_time_sec % 60
    hr = m // 60
    m %= 60
    return f"{hr}:{m:02}:{s:02}"


def get_hint_wait_time(member_id: int, guild_id) -> Optional[str]:
    """
    Returns remaining wait time before the given member can get another hint, or None if member is currently eligible.
    When this function returns None, it also sets the member's last hint time to the current time.
    """
    log.debug("finding hint wait time")
    current_time = time.time()
    filename = get_hint_timestamps_filename(guild_id)
    try:
        with open(filename, "r") as f:
            hint_times = json.load(f)
    except FileNotFoundError:
        hint_times = {"cooldown": DEFAULT_HINT_COOLDOWN_MIN, "members": {}}

    member_id = str(member_id)  # because JSON keys must be strings
    hint_cooldown_sec = hint_times["cooldown"] * 60
    last_hint_time = hint_times.get(member_id)
    if last_hint_time is not None and current_time - last_hint_time < hint_cooldown_sec:
        log.debug("member asked for hint too recently!")
        wait_time_sec = hint_cooldown_sec - (current_time - last_hint_time)
        return format_wait_time(int(wait_time_sec))

    # Hint is allowed. Record new hint timestamp
    hint_times[member_id] = current_time
    with open(filename, "w") as f:
        json.dump(hint_times, f)
    return None


def set_cooldown(cooldown_min: int, guild_id):
    response = None
    if cooldown_min < 0:
        response = "I don't know what you're playing at, but I will just set it to 0..."
        cooldown_min = 0

    filename = get_hint_timestamps_filename(guild_id)
    try:
        with open(filename, "r") as f:
            hint_times = json.load(f)
        hint_times["cooldown"] = cooldown_min
    except FileNotFoundError:
        hint_times = {"cooldown": cooldown_min, "members": {}}

    with open(filename, "w") as f:
        json.dump(hint_times, f)
    return response if response is not None else f"Done, cooldown time set to {cooldown_min} minutes."
