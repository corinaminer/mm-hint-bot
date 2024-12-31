import logging

from consts import BOT_VERSION, STANDARD_ITEM_ALIASES, VERSION_KEY
from hint_data import HintData
from utils import FileHandler, canonicalize

log = logging.getLogger(__name__)


class ItemLocations(HintData):
    fh = FileHandler("locations")

    def __init__(self, guild_id, items=None):
        self.guild_id = guild_id
        if items is None:
            try:
                items = self._get_items_from_file()
            except FileNotFoundError:
                items = {}
        super().__init__(items)
        self.save()

    def _get_items_from_file(self) -> dict[str, dict]:
        data = ItemLocations.fh.load(self.guild_id)
        data_version = data.get(VERSION_KEY)
        if data_version == BOT_VERSION:
            return data[ItemLocations.DATA_KEY]

        # Data in file is outdated or corrupt. If it's a known old version, use it; otherwise ignore it.
        if data_version is None:
            # v0 did not contain a version number, and RESUlTS_KEY was "locations" instead of "results"
            log.info("Updating locations file from v0")
            items = {}
            for item_key, item_data in data.items():
                new_item_key = canonicalize(item_data["name"])
                items[new_item_key] = {
                    ItemLocations.NAME_KEY: item_data["name"],
                    ItemLocations.RESULTS_KEY: item_data["locations"],
                }
            return items

        log.info(f"No protocol for updating filedata with version {data_version}")
        raise FileNotFoundError  # will result in default cooldown and no saved askers

    def save(self):
        ItemLocations.fh.store(self._get_filedata(), self.guild_id)

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
