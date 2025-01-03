import logging
import re
import time

from consts import BOT_VERSION, VERSION_KEY
from hint_data import HintData
from utils import FileHandler

log = logging.getLogger(__name__)

DEFAULT_HINT_COOLDOWN_SEC = 30 * 60

player_re = re.compile(r"^@?player(\d+)$")  # player14, @Player14


class HintTimes:
    fh = FileHandler("hint_timestamps")
    COOLDOWN_KEY = "cooldown"
    ASKERS_KEY = "askers"

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
            self.cooldown = data[HintTimes.COOLDOWN_KEY]
            self.askers = data[HintTimes.ASKERS_KEY]

        # Data in file is outdated or corrupt. If it's a known old version, use it; otherwise ignore it.
        elif data_version is None:
            # v0 did not contain a version number and stored cooldown in minutes. It also had a bug where asker IDs went
            # straight into the top level instead of under key "members" (now "askers"), so the members dict is empty.
            log.info("Updating hint timestamps file from v0")
            self.cooldown = data[HintTimes.COOLDOWN_KEY] * 60
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
            HintTimes.COOLDOWN_KEY: self.cooldown,
            HintTimes.ASKERS_KEY: self.askers,
        }
        HintTimes.fh.store(filedata, self.guild_id)

    def attempt_hint(self, asker_id: str) -> int:
        """
        Returns timestamp in seconds at which the member is allowed another hint, or 0 if member is currently eligible.
        When this function returns 0, it also sets the member's last hint time to the current time.
        """
        next_hint_time = self.askers.get(asker_id, 0) + self.cooldown
        current_time = int(time.time())
        if next_hint_time < current_time:
            # Hint is allowed. Record new hint timestamp.
            self.askers[asker_id] = current_time
            self.save()
            return 0
        return int(next_hint_time)

    def set_cooldown(self, cooldown_min):
        self.cooldown = cooldown_min * 60
        self.save()


def get_player_number(player: str) -> int:
    match = player_re.search(player.lower())
    if match:
        return int(match.group(1))
    raise ValueError()


def get_hint_response(
    player: str,
    item: str,
    author_id: int,
    hint_times: HintTimes,
    hint_data: HintData,
) -> str:
    try:
        player_number = get_player_number(player)
    except ValueError:
        return f'Unrecognized player {player}. (Did you format without spaces as in "player5"?)'

    try:
        item_name, player_locs_for_item = hint_data.get_locations(player_number, item)
    except FileNotFoundError:
        return "No data is currently stored. (Use !set-log to upload a spoiler log.)"
    except ValueError as e:
        return e.args[0]  # message

    if not len(player_locs_for_item):
        return f"For some reason there are no locations listed for {player}'s {item_name}........ sorry!!! There must be something wrong with me :( Please report."

    # Convert author ID for serialization; JSON keys must be strings
    hint_wait_time = hint_times.attempt_hint(str(author_id))
    # TODO Bring back hold your horses plus flavors
    if hint_wait_time:
        log.debug(f"Hint denied due to cooldown until {hint_wait_time}")
        return f"Whoa nelly! You can't get another hint until <t:{hint_wait_time}:T> -- hold your horses!!"

    return "\n".join(player_locs_for_item)


def format_wait_time(wait_time_sec: int) -> str:
    m = wait_time_sec // 60
    s = wait_time_sec % 60
    hr = m // 60
    m %= 60
    return f"{hr}:{m:02}:{s:02}"


def set_cooldown(cooldown_min: int, hint_times: HintTimes):
    response = None
    if cooldown_min < 0:
        response = "I don't know what you're playing at, but I will just set it to 0..."
        cooldown_min = 0

    if hint_times.cooldown // 60 == cooldown_min:
        return f"Cooldown time is already set to {cooldown_min} minutes."

    hint_times.set_cooldown(cooldown_min)
    return response or f"Done, cooldown time set to {cooldown_min} minutes."
