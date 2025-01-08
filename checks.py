import logging

from consts import STANDARD_CHECK_ALIASES
from hint_data import HintData
from utils import HintType

log = logging.getLogger(__name__)


class Checks(HintData):
    def __init__(self, guild_id, items=None):
        super().__init__(guild_id, HintType.CHECK, items)

    def generate_aliases(self):
        aliases = {}
        for alias, item_key in STANDARD_CHECK_ALIASES.items():
            if item_key in self.items:
                aliases[alias] = item_key
        return aliases
