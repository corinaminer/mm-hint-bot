import logging
import re
import time

from consts import BOT_VERSION, HINT_TIMES_FILENAME_SUFFIX, VERSION_KEY
from item_location_handler import (
    ALIASES_KEY,
    ITEM_LOCATIONS_KEY,
    ITEMS_KEY,
    get_item_location_data,
)
from utils import FileHandler, canonicalize

log = logging.getLogger(__name__)

DEFAULT_HINT_COOLDOWN_SEC = 30 * 60
COOLDOWN_KEY = "cooldown"
ASKERS_KEY = "askers"

player_re = re.compile(r"^@?player(\d+)$")  # player14, @Player14


class HintTimes:
    fh = FileHandler(HINT_TIMES_FILENAME_SUFFIX)

    def __init__(self, guild_id):
        self.guild_id = guild_id
        try:
            self._init_from_file()
        except FileNotFoundError:
            self.cooldown = DEFAULT_HINT_COOLDOWN_SEC
            self.askers = {}

    def _init_from_file(self):
        data = HintTimes.fh.load(self.guild_id)
        data_version = data.get(VERSION_KEY)
        if data_version == BOT_VERSION:
            self.cooldown = data[COOLDOWN_KEY]
            self.askers = data[ASKERS_KEY]

        # Data in file is outdated or corrupt. If it's a known old version, use it; otherwise ignore it.
        elif data_version is None:
            # v0 did not contain a version number and stored cooldown in minutes. It also had a bug where asker IDs went
            # straight into the top level instead of under key "members" (now "askers"), so the members dict is empty.
            log.info("Updating hint timestamps file from v0")
            self.cooldown = data[COOLDOWN_KEY] * 60
            self.askers = {}
            oldest_relevant_ask_time = time.time() - self.cooldown
            for asker_id, ask_time in data.items():
                if isinstance(ask_time, float) and ask_time > oldest_relevant_ask_time:
                    self.askers[asker_id] = ask_time
            self.save()
        else:
            log.info(f"No protocol for updating filedata with version {data_version}")
            raise FileNotFoundError  # will result in default cooldown and no saved askers

    def save(self):
        filedata = {
            VERSION_KEY: BOT_VERSION,
            COOLDOWN_KEY: self.cooldown,
            ASKERS_KEY: self.askers,
        }
        HintTimes.fh.store(filedata, self.guild_id)

    def attempt_hint(self, asker_id: str) -> float:
        """
        Returns seconds remaining before the given member can get another hint, or 0 if member is currently eligible.
        When this function returns 0, it also sets the member's last hint time to the current time.
        """
        current_time = time.time()
        last_hint_time = self.askers.get(asker_id, 0)
        wait_time_sec = max(self.cooldown - (current_time - last_hint_time), 0)
        if wait_time_sec == 0:
            # Hint is allowed. Record new hint timestamp.
            self.askers[asker_id] = current_time
            self.save()
        return wait_time_sec

    def set_cooldown(self, cooldown_min):
        self.cooldown = cooldown_min * 60
        self.save()


# Never contains more than the most-recently-used HintTimes.
# Don't want to keep them all around because the bot could be running for a long time.
cached_hint_times: list[HintTimes] = []


def get_hint_times(guild_id):
    if not len(cached_hint_times):
        cached_hint_times.append(HintTimes(guild_id))
    elif cached_hint_times[0].guild_id != guild_id:
        cached_hint_times[0] = HintTimes(guild_id)
    return cached_hint_times[0]


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

    hint_times = get_hint_times(guild_id)
    # Convert author ID for serialization; JSON keys must be strings
    hint_wait_time = hint_times.attempt_hint(str(author_id))
    if hint_wait_time:
        return f"Please chill for another {format_wait_time(int(hint_wait_time))}"

    return "\n".join(player_locs_for_item)


def format_wait_time(wait_time_sec: int) -> str:
    m = wait_time_sec // 60
    s = wait_time_sec % 60
    hr = m // 60
    m %= 60
    return f"{hr}:{m:02}:{s:02}"


def set_cooldown(cooldown_min: int, guild_id):
    response = None
    if cooldown_min < 0:
        response = "I don't know what you're playing at, but I will just set it to 0..."
        cooldown_min = 0

    hint_times = get_hint_times(guild_id)
    if hint_times.cooldown // 60 == cooldown_min:
        return f"Cooldown time is already set to {cooldown_min} minutes."

    hint_times.set_cooldown(cooldown_min)
    return response or f"Done, cooldown time set to {cooldown_min} minutes."
