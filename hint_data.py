import logging
import time
from typing import Optional

from consts import BOT_VERSION, VERSION_KEY
from utils import HintType, canonicalize, load, store

log = logging.getLogger(__name__)

DEFAULT_HINT_COOLDOWN_SEC = 30 * 60


def hint_data_filename(guild_id, hint_type: HintType) -> str:
    return f"{guild_id}-{hint_type}.json"


def hint_times_filename(guild_id, hint_type: HintType) -> str:
    return f"{guild_id}-{hint_type}-hint_times.json"


class HintData:
    """Abstract class representing a mapping of hintable keys to hint results."""

    DATA_KEY = "data"
    NAME_KEY = "name"
    RESULTS_KEY = "results"
    """
    Serialized structure:
    {
        VERSION_KEY: BOT_VERSION,
        DATA_KEY:     {
            "item key": {
                NAME_KEY: "original item name",
                RESULTS_KEY: [
                    ["result1 for player1", "result2 for player1", ...],
                    ["result1 for player2", "result2 for player2", ...],
                ]
            },
            ...
        }
    }
    """

    def __init__(self, guild_id, hint_type: HintType, items: dict[str, dict] = None):
        self.hint_type: HintType = hint_type
        self.filename: str = hint_data_filename(guild_id, hint_type)
        if items is None:
            try:
                items = self._get_items_from_file()
            except FileNotFoundError:
                items = {}
        self.items: dict[str, dict] = items
        self.aliases: dict[str, str] = self.generate_aliases()
        self.hint_times: HintTimes = HintTimes(guild_id, hint_type)
        self.save()

    def _get_items_from_file(self) -> dict[str, dict]:
        data = load(self.filename)
        data_version = data.get(VERSION_KEY)
        if data_version == BOT_VERSION:
            return data[HintData.DATA_KEY]

        # Data in file is outdated or corrupt. If it's a known old version, use it; otherwise ignore it.
        log.info(
            f"No protocol for updating {self.hint_type} data with version {data_version}"
        )
        raise FileNotFoundError

    def find_matches(self, query) -> list[str]:
        """Returns items matching the given search query. Raises FileNotFoundError if no data is stored."""
        if not len(self.items):
            raise FileNotFoundError
        query = canonicalize(query)
        return [
            hint_result[HintData.NAME_KEY]
            for item_key, hint_result in self.items.items()
            if query in item_key
        ]

    def get_item_key(self, query) -> Optional[str]:
        query = canonicalize(query)
        if query in self.items:
            return query
        return self.aliases.get(query)

    def get_results(self, player_num: int, item_query: str) -> tuple[str, list[str]]:
        """
        Returns a tuple of the item name and list of results for the given player.
        Raises FileNotFoundError if no item data is stored, and ValueError for unrecognized player num or item query.
        """
        if not len(self.items):
            raise FileNotFoundError

        item_key = canonicalize(item_query)
        if item_key not in self.items:
            item_key = self.aliases.get(item_key)
        if item_key is None:
            raise ValueError(
                f"Item {item_query} not recognized. Try !search <keyword> to find it!"
            )

        hint_result = self.items[item_key]
        if player_num < 1 or player_num > len(hint_result[HintData.RESULTS_KEY]):
            raise ValueError(f"Invalid player number {player_num}.")

        return (
            hint_result[HintData.NAME_KEY],
            hint_result[HintData.RESULTS_KEY][player_num - 1],
        )

    def _get_filedata(self):
        return {
            VERSION_KEY: BOT_VERSION,
            HintData.DATA_KEY: self.items,
        }

    def save(self):
        store(self._get_filedata(), self.filename)

    def generate_aliases(self):
        # Should be implemented by child classes
        raise NotImplementedError


class HintTimes:
    COOLDOWN_KEY = "cooldown"
    ASKERS_KEY = "askers"

    def __init__(self, guild_id, hint_type: HintType):
        self.filename = hint_times_filename(guild_id, hint_type)
        try:
            self._init_from_file()
        except FileNotFoundError:
            self.cooldown = DEFAULT_HINT_COOLDOWN_SEC
            self.askers = {}

    def _init_from_file(self):
        data = load(self.filename)
        data_version = data.get(VERSION_KEY)
        if data_version == BOT_VERSION:
            self.cooldown = data[HintTimes.COOLDOWN_KEY]
            self.askers = data[HintTimes.ASKERS_KEY]
        else:
            # Data in file is outdated or corrupt. If it's a known old version, use it; otherwise ignore it.
            log.info(
                f"No protocol for updating hint times filedata with version {data_version}"
            )
            raise FileNotFoundError  # will result in default cooldown and no saved askers

    def save(self):
        filedata = {
            VERSION_KEY: BOT_VERSION,
            HintTimes.COOLDOWN_KEY: self.cooldown,
            HintTimes.ASKERS_KEY: self.askers,
        }
        store(filedata, self.filename)

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

    def set_cooldown(self, cooldown_min: int):
        self.cooldown = cooldown_min * 60
        self.save()
