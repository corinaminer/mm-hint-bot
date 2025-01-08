import logging

from consts import STANDARD_ITEM_ALIASES
from hint_data import HintData
from utils import HintType, canonicalize

log = logging.getLogger(__name__)


class ItemLocations(HintData):
    def __init__(self, guild_id, items=None):
        super().__init__(guild_id, HintType.ITEM, items)

    def generate_aliases(self):
        aliases = {}
        for alias, item_key in STANDARD_ITEM_ALIASES.items():
            if item_key in self.items:
                aliases[alias] = item_key
        for item_key, item_data in self.items.items():
            for alias in generate_item_aliases(item_data[HintData.NAME_KEY]):
                aliases[alias] = item_key
        return aliases


def generate_item_aliases(item_name):
    """Generates any aliases for an item given its original unmodified name."""
    aliases = []
    no_poss = item_name.replace("'s ", " ")
    if no_poss != item_name:
        aliases.append(canonicalize(no_poss))
    return aliases
