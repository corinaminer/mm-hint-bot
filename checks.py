import logging

from hint_data import HintData
from utils import HintType

log = logging.getLogger(__name__)


class Checks(HintData):
    def __init__(self, guild_id, items=None):
        super().__init__(guild_id, HintType.CHECK, items)

    def generate_aliases(self):
        # TODO
        return {}
