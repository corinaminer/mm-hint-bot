import logging
import re
from enum import Enum
from typing import List

from consts import IGNORED_ITEMS
from item_location_handler import ItemLocations
from utils import canonicalize

log = logging.getLogger(__name__)

players_re = re.compile(r"^ +players: (\d+)$")  # players: 14

loc_list_re = re.compile(r"^Location List \(\d+\)$")  # Location List (4410)
world_re = re.compile(r"^ +World (\d+) \(\d+\)$")  # World 1 (490)
area_re = re.compile(r"^ +([^ ].+) \(\d+\):$")  # Tingle (6):
loc_re = re.compile(
    r"^ {6}MM (.+): Player (\d+) ([^\n]+)$"
)  # MM Woodfall Entrance Chest: Player 7 Postman's Hat


class SpoilerStep(Enum):
    FIND_PLAYER_COUNT = "find player count"
    FIND_LOCATIONS = "find locations section"
    PROCESS_LOCATIONS = "process locations section"


def handle_spoiler_log(
    spoiler_log_lines: List[str], guild_id
) -> tuple[str, ItemLocations]:
    current_step = SpoilerStep.FIND_PLAYER_COUNT
    player_count = 0
    item_locations = {}

    current_world = None
    unparsed_lines = []

    for line in spoiler_log_lines:
        match current_step:
            case SpoilerStep.FIND_PLAYER_COUNT:
                players_match = players_re.search(line)
                if players_match:
                    player_count = int(players_match.group(1))
                    log.debug(f"Found player count {player_count}")
                    current_step = SpoilerStep.FIND_LOCATIONS
                continue
            case SpoilerStep.FIND_LOCATIONS:
                if loc_list_re.search(line):
                    current_step = SpoilerStep.PROCESS_LOCATIONS
                    log.debug("Found location list")
                continue
            case SpoilerStep.PROCESS_LOCATIONS:
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
                                ItemLocations.ITEM_NAME_KEY: item_name,
                                ItemLocations.ITEM_LOCATIONS_KEY: [
                                    [] for _ in range(player_count)
                                ],
                            }
                        item_locations[item_key][ItemLocations.ITEM_LOCATIONS_KEY][
                            player
                        ].append(loc)
                    continue

                if line.strip() and not area_re.search(line):
                    unparsed_lines.append(line)
                    log.info(f"Could not parse line: {line}")
            case _:
                log.info(f"Unrecognized step {current_step}")
                item_locations = {}
                break

    if not len(item_locations):
        return (
            f"Failed to {current_step.value}. Could not extract data.",
            ItemLocations(guild_id, {}),
        )

    item_locs = ItemLocations(guild_id, item_locations)
    if len(unparsed_lines):
        # you can't put \ in an f-strings curly brace expr
        unparsed_lines_str = "\n".join(unparsed_lines)
        return (
            "Some lines in the spoiler log were unrecognized, which may result in missing item locations:\n"
            + f"||{unparsed_lines_str}||",
            item_locs,
        )
    return (
        "Spoiler log processed successfully!",
        item_locs,
    )
