import json
import logging
import re
from typing import List

log = logging.getLogger(__name__)

IGNORED_ITEMS = {
    "Nothing",
    "Recovery Heart",
    "Piece of Heart",
    "Heart Container",
    "Small Magic Jar",
    "Large Magic Jar",
    "Deku Stick",
    "Fairy",
    "10 Arrows",
    "30 Arrows",
    "1 Bombchu",
    "5 Bombchu",
    "10 Bombchu",
    "5 Bombs",
    "10 Bombs",
    "10 Deku Nuts",
    "Green Rupee",
    "Blue Rupee",
    "Red Rupee",
    "Purple Rupee",
    "Silver Rupee",
    "Gold Rupee",
    "Green Potion",
    "Owl Statue (Clock Town)",
    "Owl Statue (Milk Road)",
    "Owl Statue (Southern Swamp)",
    "Owl Statue (Woodfall)",
    "Owl Statue (Mountain Village)",
    "Owl Statue (Snowhead)",
    "Owl Statue (Great Bay)",
    "Owl Statue (Zora Cape)",
    "Owl Statue (Ikana Canyon)",
    "Owl Statue (Stone Tower)",
}

players_re = re.compile(r"players: (\d+)$")  # players: 14
loc_list_re = re.compile(r"Location List \(\d+\)$")  # Location List (4410)
world_re = re.compile(r"World (\d+) \(\d+\)$")  # World 1 (490)
area_re = re.compile(r"(.+) \(\d+\):$")  # Tingle (6):
loc_re = re.compile(r"MM (.+): Player (\d+) ([^\n]+)$")  # MM Woodfall Entrance Chest: Player 7 Postman's Hat


def get_filename(guild_id):
    return f"{guild_id}-locations.json"

def store_locations(loc_info: List[str], guild_id):
    player_count = 0
    locations = {}
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
            item = loc_match.group(3)
            if item.endswith(" (MM)"):
                item = item[:-5]
            if item not in IGNORED_ITEMS:
                player = int(loc_match.group(2)) - 1
                loc = f"World {current_world} {loc_match.group(1)}"
                item_key = item.lower()
                if item_key not in locations:
                    locations[item_key] = {"name": item, "locations": [[] for _ in range(player_count)]}
                locations[item_key]["locations"][player].append(loc)
            continue

        if line.strip() and not area_re.search(line):
            unparsed_lines.append(line)
            log.info(f"Could not parse line: {line}")

    with open(get_filename(guild_id), "w") as f:
        log.debug("Storing location info to file")
        json.dump(locations, f)
    if not len(locations):
        # Should likely still replace current locations file even in this case
        return "Unknown error occurred. Could not extract locations."
    if len(unparsed_lines):
        unparsed_lines_str = "\n".join(unparsed_lines)  # you can't put \ in an f-strings curly brace expr
        return (
                "Some lines in the spoiler log were unrecognized, which may result in missing item locations:\n"
                + f"||{unparsed_lines_str}||"
        )
    return "Spoiler log successfully stored!"


def get_locations(guild_id):
    try:
        with open(get_filename(guild_id), "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
