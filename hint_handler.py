import logging
import re
import time
from typing import Optional

from consts import BOT_VERSION, HINT_TIMES_FILENAME_SUFFIX, VERSION_KEY
from item_location_handler import (
    ALIASES_KEY,
    ITEM_LOCATIONS_KEY,
    ITEMS_KEY,
    get_item_location_data,
)
from utils import FileHandler, canonicalize

log = logging.getLogger(__name__)

DEFAULT_HINT_COOLDOWN_MIN = 30
COOLDOWN_KEY = "cooldown"
MEMBERS_KEY = "members"

player_re = re.compile(r"^@?player(\d+)$")  # player14, @Player14

hint_times_fh = FileHandler(HINT_TIMES_FILENAME_SUFFIX)


def get_player_number(player: str) -> int:
    match = player_re.search(player.lower())
    if match:
        return int(match.group(1)) - 1
    raise ValueError()


def get_hint_response(player: str, item: str, author_id: int, guild_id) -> str:
    try:
        player_number = get_player_number(player)
    except ValueError:
        return f'Unrecognized player {player}. (Did you format without spaces as in "player5"?)'

    data = get_item_location_data(guild_id)
    locs = data.get(ITEMS_KEY, {})
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

    player_locs_for_item = item_data[ITEM_LOCATIONS_KEY][player_number]
    if not len(player_locs_for_item):
        return f"For some reason there are no locations listed for {player}'s {item}........ sorry!!! There must be something wrong with me :( Please report."

    hint_wait_time = get_hint_wait_time(author_id, guild_id)
    if hint_wait_time is not None:
        return f"Please chill for another {hint_wait_time}"

    return "\n".join(player_locs_for_item)


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
    try:
        hint_times = get_hint_times_data(guild_id)
    except FileNotFoundError:
        hint_times = {
            VERSION_KEY: BOT_VERSION,
            COOLDOWN_KEY: DEFAULT_HINT_COOLDOWN_MIN,
            MEMBERS_KEY: {},
        }

    member_id = str(member_id)  # because JSON keys must be strings
    hint_cooldown_sec = hint_times[COOLDOWN_KEY] * 60
    last_hint_time = hint_times[MEMBERS_KEY].get(member_id)
    if last_hint_time is not None and current_time - last_hint_time < hint_cooldown_sec:
        log.debug("member asked for hint too recently!")
        wait_time_sec = hint_cooldown_sec - (current_time - last_hint_time)
        return format_wait_time(int(wait_time_sec))

    # Hint is allowed. Record new hint timestamp
    hint_times[MEMBERS_KEY][member_id] = current_time
    hint_times_fh.store(hint_times, guild_id)
    return None


def set_cooldown(cooldown_min: int, guild_id):
    response = None
    if cooldown_min < 0:
        response = "I don't know what you're playing at, but I will just set it to 0..."
        cooldown_min = 0

    try:
        hint_times = get_hint_times_data(guild_id)
        if hint_times.get(COOLDOWN_KEY) == cooldown_min:
            return f"Cooldown time is already set to {cooldown_min} minutes."
        hint_times[COOLDOWN_KEY] = cooldown_min
    except FileNotFoundError:
        hint_times = {
            VERSION_KEY: BOT_VERSION,
            COOLDOWN_KEY: cooldown_min,
            MEMBERS_KEY: {},
        }

    hint_times_fh.store(hint_times, guild_id)
    return response or f"Done, cooldown time set to {cooldown_min} minutes."


def get_hint_times_data(guild_id):
    hint_times_data = hint_times_fh.load(guild_id)
    if hint_times_data.get(VERSION_KEY) != BOT_VERSION:
        return update_version(hint_times_data, guild_id)
    return hint_times_data


def update_version(hint_times_file_data, guild_id):
    if VERSION_KEY not in hint_times_file_data:
        # v0 did not contain a version number
        log.info("Updating hint times file from v0")
        members = {}
        cooldown = hint_times_file_data[COOLDOWN_KEY]
        oldest_relevant_ask_time = time.time() - (cooldown * 60)
        # V0 had a bug where asker IDs went straight in the top level instead of under MEMBERS_KEY
        for asker_id, ask_time in hint_times_file_data.items():
            if (
                asker_id != COOLDOWN_KEY
                and asker_id != MEMBERS_KEY
                and ask_time > oldest_relevant_ask_time
            ):
                members[asker_id] = ask_time
        new_filedata = {
            VERSION_KEY: BOT_VERSION,
            COOLDOWN_KEY: cooldown,
            MEMBERS_KEY: members,
        }
        hint_times_fh.store(new_filedata, guild_id)
        return new_filedata

    log.info(
        f"No protocol for updating filedata with version {hint_times_file_data[VERSION_KEY]}"
    )
    return hint_times_file_data
