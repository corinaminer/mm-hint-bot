import logging

from consts import BOT_VERSION, VERSION_KEY
from utils import canonicalize

log = logging.getLogger(__name__)


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

    def __init__(self, items: dict[str, dict]):
        self.items = items
        self.aliases = self.generate_aliases()

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

    def get_locations(self, player_num: int, item_query: str) -> tuple[str, list[str]]:
        """
        Returns a tuple of the item name and list of locations where it can be found for the given player.
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
        # Should be implemented by child classes, which have an associated filename
        raise NotImplementedError

    def generate_aliases(self):
        # Should be implemented by child classes
        raise NotImplementedError
