import logging

from consts import BOT_VERSION, STANDARD_ALIASES, VERSION_KEY
from utils import FileHandler, canonicalize

log = logging.getLogger(__name__)


class ItemLocations:
    fh = FileHandler("locations")
    ITEMS_KEY = "items"
    ITEM_NAME_KEY = "name"
    ITEM_LOCATIONS_KEY = "locations"
    ALIASES_KEY = "aliases"
    """
    Serialized structure:
    {
        VERSION_KEY: BOT_VERSION,
        ALIASES_KEY: { "alias1": "item key", ...}
        ITEMS_KEY: {
            "item1 key": {
                ITEM_NAME_KEY: "original item name",
                ITEM_LOCATIONS_KEY: [
                    ["location1 for player1", "location2 for player1", ...],
                    ["location1 for player2", "location2 for player2", ...],
                ]
            },
            ...
        }
    }
    """

    def __init__(self, guild_id, items=None):
        self.guild_id = guild_id
        if items is not None:
            self.items = items
            self.aliases = generate_aliases(self.items)
            self.save()
        else:
            try:
                self._init_from_file()
            except FileNotFoundError:
                self.aliases = {}
                self.items = {}

    def _init_from_file(self):
        data = ItemLocations.fh.load(self.guild_id)
        data_version = data.get(VERSION_KEY)
        if data_version == BOT_VERSION:
            self.aliases = data[ItemLocations.ALIASES_KEY]
            self.items = data[ItemLocations.ITEMS_KEY]

        # Data in file is outdated or corrupt. If it's a known old version, use it; otherwise ignore it.
        elif data_version is None:
            # v0 did not contain a version number or aliases
            log.info("Updating locations file from v0")
            self.items = {}
            for item_key, item_data in data.items():
                new_item_key = canonicalize(item_data["name"])
                self.items[new_item_key] = item_data
            self.aliases = generate_aliases(self.items)
            self.save()
        else:
            log.info(f"No protocol for updating filedata with version {data_version}")
            raise FileNotFoundError  # will result in default cooldown and no saved askers

    def save(self):
        new_filedata = {
            VERSION_KEY: BOT_VERSION,
            ItemLocations.ITEMS_KEY: self.items,
            ItemLocations.ALIASES_KEY: self.aliases,
        }
        ItemLocations.fh.store(new_filedata, self.guild_id)

    def find_matching_items(self, query) -> list[str]:
        """Returns items matching the given search query. Raises FileNotFoundError if no data is stored."""
        if not len(self.items):
            raise FileNotFoundError
        query = canonicalize(query)
        matching_items = []
        for item, data in self.items.items():
            if query in item:
                matching_items.append(data[ItemLocations.ITEM_NAME_KEY])
        return matching_items

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

        item_data = self.items[item_key]
        if player_num < 1 or player_num > len(
            item_data[ItemLocations.ITEM_LOCATIONS_KEY]
        ):
            raise ValueError(f"Invalid player number {player_num}.")

        return (
            item_data[ItemLocations.ITEM_NAME_KEY],
            item_data[ItemLocations.ITEM_LOCATIONS_KEY][player_num - 1],
        )


def generate_item_aliases(item_name):
    """Generates any aliases for an item given its original unmodified name."""
    aliases = []
    no_poss = item_name.replace("'s ", " ")
    if no_poss != item_name:
        aliases.append(canonicalize(no_poss))
    return aliases


def generate_aliases(item_locations):
    aliases = {}
    for alias, item_key in STANDARD_ALIASES.items():
        if item_key in item_locations:
            aliases[alias] = item_key
    for item_key, item_data in item_locations.items():
        for alias in generate_item_aliases(item_data["name"]):
            aliases[alias] = item_key
    return aliases


# Never contains more than the most-recently-used ItemLocations.
# Don't want to keep them all around because the bot could be running for a long time.
cached_item_locations: list[ItemLocations] = []


def get_item_locations(guild_id) -> ItemLocations:
    if not len(cached_item_locations):
        cached_item_locations.append(ItemLocations(guild_id))
    elif cached_item_locations[0].guild_id != guild_id:
        cached_item_locations[0] = ItemLocations(guild_id)
    return cached_item_locations[0]


def set_item_locations(item_locations, guild_id):
    new_item_locations = ItemLocations(guild_id, item_locations)
    if len(cached_item_locations):
        cached_item_locations[0] = new_item_locations
    else:
        cached_item_locations.append(new_item_locations)
