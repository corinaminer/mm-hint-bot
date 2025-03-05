import logging
from typing import Optional

from consts import BOT_VERSION, VERSION_KEY
from utils import HintType, canonicalize, load, store

log = logging.getLogger(__name__)

DEFAULT_HINT_COOLDOWN_SEC = 30 * 60


def hint_data_filename(guild_id, hint_type: HintType) -> str:
    return f"{guild_id}-{hint_type}.json"


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
        """
        Creates hint data with the given hint type. If item data is given, a hint data file is saved. Otherwise,
        data is populated from existing file (or empty if no file exists).
        """
        self.hint_type: HintType = hint_type
        self.filename: str = hint_data_filename(guild_id, hint_type)

        if items is not None:
            self.items = items
            self.save()
        else:
            try:
                self.items = self._get_items_from_file()
            except FileNotFoundError:
                self.items = {}

        self.aliases: dict[str, str] = (
            self.generate_aliases() if len(self.items) else {}
        )

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
        results = set()
        for item_key, hint_result in self.items.items():
            if query in item_key:
                results.add(hint_result[HintData.NAME_KEY])
        for alias, item_key in self.aliases.items():
            if query in alias:
                results.add(self.items[item_key][HintData.NAME_KEY])
        return sorted(results)

    def get_item_key(self, query) -> Optional[str]:
        """Returns the item key matching the hint query, or None if it doesn't match a key or alias."""
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
