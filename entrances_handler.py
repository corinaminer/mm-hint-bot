import logging

from consts import STANDARD_LOCATION_ALIASES
from hint_data import HintData
from utils import HintType

log = logging.getLogger(__name__)


class Entrances(HintData):
    def __init__(self, guild_id, items=None):
        super().__init__(guild_id, HintType.ENTRANCE, items)

    def generate_aliases(self):
        aliases = {}
        for alias, item_key in STANDARD_LOCATION_ALIASES.items():
            if item_key in self.items:
                aliases[alias] = item_key
        return aliases
