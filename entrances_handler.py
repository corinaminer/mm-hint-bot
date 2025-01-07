import logging

from consts import BOT_VERSION, STANDARD_LOCATION_ALIASES, VERSION_KEY
from hint_data import HintData
from utils import FileHandler, HintType

log = logging.getLogger(__name__)


class Entrances(HintData):
    fh = FileHandler("entrances")

    def __init__(self, guild_id, items=None):
        self.guild_id = guild_id
        if items is None:
            try:
                items = self._get_items_from_file()
            except FileNotFoundError:
                items = {}
        super().__init__(items, guild_id, HintType.ENTRANCE)
        self.save()

    def _get_items_from_file(self) -> dict[str, dict]:
        data = Entrances.fh.load(self.guild_id)
        data_version = data.get(VERSION_KEY)
        if data_version == BOT_VERSION:
            return data[Entrances.DATA_KEY]

        # Data in file is outdated or corrupt. If it's a known old version, use it; otherwise ignore it.
        log.info(f"No protocol for updating entrance data with version {data_version}")
        raise FileNotFoundError  # will result in default cooldown and no saved askers

    def save(self):
        Entrances.fh.store(self._get_filedata(), self.guild_id)

    def generate_aliases(self):
        aliases = {}
        for alias, item_key in STANDARD_LOCATION_ALIASES.items():
            if item_key in self.items:
                aliases[alias] = item_key
        return aliases
