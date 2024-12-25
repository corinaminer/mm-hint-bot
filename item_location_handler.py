import logging
import re
from typing import List

from consts import BOT_VERSION, IGNORED_ITEMS, STANDARD_ALIASES
from utils import canonicalize, FileHandler

log = logging.getLogger(__name__)

ITEMS_KEY = "items"
ITEM_NAME_KEY = "name"
ITEM_LOCATIONS_KEY = "locations"
ALIASES_KEY = "aliases"
VERSION_KEY = "version"
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

players_re = re.compile(r"players: (\d+)$")  # players: 14
loc_list_re = re.compile(r"Location List \(\d+\)$")  # Location List (4410)
world_re = re.compile(r"World (\d+) \(\d+\)$")  # World 1 (490)
area_re = re.compile(r"(.+) \(\d+\):$")  # Tingle (6):
loc_re = re.compile(r"MM (.+): Player (\d+) ([^\n]+)$")  # MM Woodfall Entrance Chest: Player 7 Postman's Hat

item_locations_fh = FileHandler("locations")


def generate_aliases(item_name):
    """Generates any aliases for an item given its original unmodified name."""
    aliases = []
    no_poss = item_name.replace("'s ", " ")
    if no_poss != item_name:
        aliases.append(canonicalize(no_poss))
    return aliases


def store_locations(loc_info: List[str], guild_id):
    player_count = 0
    locations = {}
    aliases = {k: v for k, v in STANDARD_ALIASES.items()}

    current_world = None
    in_locs = False
    unparsed_lines = []

    for line in loc_info:
        if player_count == 0:
            players_match = players_re.search(line)
            if players_match:
                player_count = int(players_match.group(1))
                log.debug(f"Found player count {player_count}")
            continue

        if not in_locs:
            if loc_list_re.search(line):
                in_locs = True
                log.debug("Found location list")
            continue

        world_match = world_re.search(line)
        if world_match:
            current_world = world_match.group(1)
            log.debug(f"Parsing world {current_world} locations")
            continue

        loc_match = loc_re.search(line)
        if loc_match:
            item_name = loc_match.group(3)
            if item_name.endswith(" (MM)"):
                item_name = item_name[:-5]
            if item_name not in IGNORED_ITEMS:
                player = int(loc_match.group(2)) - 1
                loc = f"World {current_world} {loc_match.group(1)}"
                item_key = canonicalize(item_name)
                if item_key not in locations:
                    locations[item_key] = {
                        ITEM_NAME_KEY: item_name,
                        ITEM_LOCATIONS_KEY: [[] for _ in range(player_count)]
                    }
                locations[item_key][ITEM_LOCATIONS_KEY][player].append(loc)
                for a in generate_aliases(item_name):
                    aliases[a] = item_key
            continue

        if line.strip() and not area_re.search(line):
            unparsed_lines.append(line)
            log.info(f"Could not parse line: {line}")

    filedata = {
        VERSION_KEY: BOT_VERSION,
        ITEMS_KEY: locations,
        ALIASES_KEY: aliases if len(locations) else {},
    }

    log.debug("Storing location info to file")
    item_locations_fh.store(filedata, guild_id)
    if not len(locations):
        # Should likely still replace current locations file even in this case
        return "Unknown error occurred. Could not extract data."
    if len(unparsed_lines):
        unparsed_lines_str = "\n".join(unparsed_lines)  # you can't put \ in an f-strings curly brace expr
        return (
                "Some lines in the spoiler log were unrecognized, which may result in missing item locations:\n"
                + f"||{unparsed_lines_str}||"
        )
    return "Spoiler log successfully stored!"


def get_item_data(guild_id):
    try:
        item_data = item_locations_fh.load(guild_id)
    except FileNotFoundError:
        return {}
    if item_data.get(VERSION_KEY) != BOT_VERSION:
        item_data = update_version(item_data, guild_id)
    return item_data


def update_version(item_data, guild_id):
    if VERSION_KEY not in item_data:
        # v0 was not numbered
        log.info("Updating locations file from v0")
        items = {}
        aliases = {k: v for k, v in STANDARD_ALIASES.items()}
        for item_key in item_data:
            item_aliases = generate_aliases(item_data[item_key]["name"])
            new_item_key = canonicalize(item_key)
            items[new_item_key] = item_data[item_key]
            for a in item_aliases:
                aliases[a] = new_item_key
        new_filedata = {
            VERSION_KEY: BOT_VERSION,
            ITEMS_KEY: items,
            ALIASES_KEY: aliases,
        }
        item_locations_fh.store(new_filedata, guild_id)
        return new_filedata

    log.info(f"No routine for updating filedata with version {item_data[VERSION_KEY]}")
    return item_data
