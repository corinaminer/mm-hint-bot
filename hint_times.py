import logging
import time

from consts import BOT_VERSION, VERSION_KEY
from utils import HintType, load, store

log = logging.getLogger(__name__)

DEFAULT_HINT_COOLDOWN_SEC = 30 * 60


def hint_times_filename(guild_id) -> str:
    return f"{guild_id}-hint_times.json"


class HintTimes:
    """
    File structure:
    {
        VERSION_KEY: version,
        COOLDOWNS_KEY: {
            hint type 1: cooldown,
            ...
        },
        HINT_TIMES_KEY: {
            asker 1: {
                hint type 1: timestamp of last hint,
                ...
            }
        },
        PAST_HINTS_KEY: {
            player number: {
                hint type 1: [
                    "past hint query: answer",
                    ...
                ],
                ...
            },
            ...
        }
    }
    """

    COOLDOWNS_KEY = "cooldowns"
    HINT_TIMES_KEY = "hint_times"
    PAST_HINTS_KEY = "past_hints"

    def __init__(self, guild_id):
        self.filename = hint_times_filename(guild_id)
        try:
            self._init_from_file()
        except FileNotFoundError:
            self.cooldowns = {}
            self.hint_times = {}
            self.past_hints = {}

    def _init_from_file(self):
        data = load(self.filename)
        data_version = data.get(VERSION_KEY)
        if data_version == BOT_VERSION:
            self.cooldowns = {
                HintType(ht): cooldown
                for ht, cooldown in data[HintTimes.COOLDOWNS_KEY].items()
            }
            self.hint_times = {}
            self.past_hints = {}
            for asker, hint_timestamps in data[HintTimes.HINT_TIMES_KEY].items():
                self.hint_times[int(asker)] = {
                    HintType(ht): timestamp for ht, timestamp in hint_timestamps.items()
                }
            for player, past_hints in data[HintTimes.PAST_HINTS_KEY].items():
                self.past_hints[int(player)] = {
                    HintType(ht): hint_list for ht, hint_list in past_hints.items()
                }
        else:
            # Data in file is outdated or corrupt. If it's a known old version, use it; otherwise ignore it.
            log.info(
                f"No protocol for updating hint times filedata with version {data_version}"
            )
            raise FileNotFoundError  # will result in default cooldowns and no saved askers

    def save(self):
        serialized_hint_times = {}
        serialized_past_hints = {}
        for asker, hint_timestamps in self.hint_times.items():
            serialized_hint_times[asker] = {
                str(ht): timestamp for ht, timestamp in hint_timestamps.items()
            }
        for player, past_hints in self.past_hints.items():
            serialized_past_hints[player] = {
                str(ht): hint_list for ht, hint_list in past_hints.items()
            }
        filedata = {
            VERSION_KEY: BOT_VERSION,
            HintTimes.COOLDOWNS_KEY: {
                str(ht): cooldown for ht, cooldown in self.cooldowns.items()
            },
            HintTimes.HINT_TIMES_KEY: serialized_hint_times,
            HintTimes.PAST_HINTS_KEY: serialized_past_hints,
        }
        store(filedata, self.filename)

    def attempt_hint(self, asker_id: int, hint_type: HintType) -> int:
        """
        Returns timestamp in seconds at which the member is allowed another hint, or 0 if member is currently eligible.
        """
        last_hint_time = self.hint_times.get(asker_id, {}).get(hint_type, 0)
        if last_hint_time == 0:
            return 0
        next_hint_time = last_hint_time + self.get_cooldown(hint_type)
        current_time = int(time.time())
        if next_hint_time <= current_time:
            return 0
        return int(next_hint_time)

    def record_hint(
        self, asker_id: int, player_num: int, hint_type: HintType, hint_result: str
    ):
        # Record current time as the asker's latest hint time
        self.hint_times.setdefault(asker_id, {})[hint_type] = int(time.time())
        # Add hint to past hints if it's not a repeat
        past_hints = self.past_hints.setdefault(player_num, {}).setdefault(
            hint_type, []
        )
        if hint_result not in past_hints:
            past_hints.append(hint_result)
        self.save()

    def get_cooldown(self, hint_type: HintType):
        return self.cooldowns.get(hint_type, DEFAULT_HINT_COOLDOWN_SEC)

    def set_all_cooldowns(self, cooldown_min: int):
        changed = False
        for ht in HintType:
            changed = self._set_cooldown(cooldown_min, ht) or changed
        if changed:
            self.save()

    def set_cooldown(self, cooldown_min: int, hint_type: HintType):
        if self._set_cooldown(cooldown_min, hint_type):
            self.save()

    def _set_cooldown(self, cooldown_min: int, hint_type: HintType) -> bool:
        old_cooldown = self.get_cooldown(hint_type)
        new_cooldown = cooldown_min * 60
        self.cooldowns[hint_type] = new_cooldown
        return old_cooldown != new_cooldown

    def clear_past_hints(self):
        if len(self.past_hints):
            self.past_hints = {}
            self.save()
