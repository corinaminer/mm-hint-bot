import logging

from consts import (
    BOT_VERSION,
    ITEM_LOCATIONS_FILENAME_SUFFIX,
    STANDARD_ALIASES,
    VERSION_KEY,
)
from utils import FileHandler, canonicalize

log = logging.getLogger(__name__)

ITEMS_KEY = "items"
ITEM_NAME_KEY = "name"
ITEM_LOCATIONS_KEY = "locations"
ALIASES_KEY = "aliases"
"""
Item data structure:
{
    VERSION_KEY: BOT_VERSION,
    ALIASES_KEY: { "alias1": "item key", ...}
    ITEM_LOCATIONS_KEY: {
        "item1 key": {
            ITEM_NAME_KEY: "original item name",
            ITEM_LOCATIONS_KEY: [
                ["location1 for player1", "location2 for player1", ...],
                ["location1 for player2", "location2 for player2", ...],
            ]
        }
    }
}
"""

item_locations_fh = FileHandler(ITEM_LOCATIONS_FILENAME_SUFFIX)


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


def set_item_locations(item_locations, guild_id):
    item_loc_file_data = {
        VERSION_KEY: BOT_VERSION,
        ITEMS_KEY: item_locations,
        ALIASES_KEY: generate_aliases(item_locations),
    }
    item_locations_fh.store(item_loc_file_data, guild_id)


def get_item_location_data(guild_id):
    try:
        item_data = item_locations_fh.load(guild_id)
    except FileNotFoundError:
        return {}
    if item_data.get(VERSION_KEY) != BOT_VERSION:
        item_data = update_version(item_data, guild_id)
    return item_data


def update_version(item_location_file_data, guild_id):
    if VERSION_KEY not in item_location_file_data:
        # v0 did not contain a version number
        log.info("Updating locations file from v0")
        item_locations = {}
        for item_key, item_data in item_location_file_data.items():
            new_item_key = canonicalize(item_data["name"])
            item_locations[new_item_key] = item_data
        new_filedata = {
            VERSION_KEY: BOT_VERSION,
            ITEMS_KEY: item_locations,
            ALIASES_KEY: generate_aliases(item_locations),
        }
        item_locations_fh.store(new_filedata, guild_id)
        return new_filedata

    log.info(
        f"No protocol for updating filedata with version {item_location_file_data[VERSION_KEY]}"
    )
    return item_location_file_data
