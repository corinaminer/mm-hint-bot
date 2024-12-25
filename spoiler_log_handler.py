import logging
import re
from typing import List

from consts import IGNORED_ITEMS
from item_location_handler import set_item_locations
from utils import canonicalize

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

players_re = re.compile(r"^ +players: (\d+)$")  # players: 14

loc_list_re = re.compile(r"^Location List \(\d+\)$")  # Location List (4410)
world_re = re.compile(r"^ +World (\d+) \(\d+\)$")  # World 1 (490)
area_re = re.compile(r"^ +([^ ].+) \(\d+\):$")  # Tingle (6):
loc_re = re.compile(
    r"^ {6}MM (.+): Player (\d+) ([^\n]+)$"
)  # MM Woodfall Entrance Chest: Player 7 Postman's Hat


def handle_spoiler_log(spoiler_log_lines: List[str], guild_id):
    player_count = 0
    item_locations = {}

    current_world = None
    in_locs = False
    unparsed_lines = []

    for line in spoiler_log_lines:
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
                if item_key not in item_locations:
                    item_locations[item_key] = {
                        ITEM_NAME_KEY: item_name,
                        ITEM_LOCATIONS_KEY: [[] for _ in range(player_count)],
                    }
                item_locations[item_key][ITEM_LOCATIONS_KEY][player].append(loc)
            continue

        if line.strip() and not area_re.search(line):
            unparsed_lines.append(line)
            log.info(f"Could not parse line: {line}")

    set_item_locations(item_locations, guild_id)

    if not len(item_locations):
        # We still replace current locations file even in this case (with empty data)
        return "Unknown error occurred. Could not extract data."
    if len(unparsed_lines):
        unparsed_lines_str = "\n".join(
            unparsed_lines
        )  # you can't put \ in an f-strings curly brace expr
        return (
            "Some lines in the spoiler log were unrecognized, which may result in missing item locations:\n"
            + f"||{unparsed_lines_str}||"
        )
    return "Spoiler log processed successfully!"
