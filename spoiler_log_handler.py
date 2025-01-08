import logging
import re
from enum import Enum
from typing import List

from consts import IGNORED_ITEMS
from entrances import Entrances
from item_locations import ItemLocations
from utils import canonicalize

log = logging.getLogger(__name__)

players_re = re.compile(r"^ +players: (\d+)$")  # players: 14

# MM Clock Tower Platform to MM Clock Tower Roof (MM_CLOCK_TOWER_ROOF)
#     -> MM Stone Tower Temple from MM Stone Tower Front of Temple (MM_TEMPLE_STONE_TOWER)
# (no line break)
entrance_re = re.compile(r"^ +(MM )?(.+) \(([A-Z_]+)\) +-> (MM )?(.+) \(([A-Z_]+)\)$")
entrance_world_re = re.compile(r"^ +World (\d+)$")  # World 1

loc_list_re = re.compile(r"^Location List \(\d+\)$")  # Location List (4410)
loc_world_re = re.compile(r"^ +World (\d+) \(\d+\)$")  # World 1 (490)
area_re = re.compile(r"^ +([^ ].+) \(\d+\):$")  # Tingle (6):
# MM Woodfall Entrance Chest: Player 7 Postman's Hat
loc_re = re.compile(r"^ {6}MM (.+): Player (\d+) ([^\n]+)$")


class SpoilerStep(Enum):
    FIND_PLAYER_COUNT = "find player count"
    FIND_ENTRANCES = "find entrances section"
    PROCESS_ENTRANCES = "process entrances section"
    FIND_LOCATIONS = "find locations section"
    PROCESS_LOCATIONS = "process locations section"


def handle_spoiler_log(
    spoiler_log_lines: List[str], guild_id
) -> tuple[str, ItemLocations, Entrances]:
    current_step = SpoilerStep.FIND_PLAYER_COUNT
    player_count = 0
    entrance_data = {}
    item_locations = {}

    current_world = None
    unparsed_lines = []

    for line in spoiler_log_lines:
        if not line.strip():
            continue
        match current_step:
            case SpoilerStep.FIND_PLAYER_COUNT:
                players_match = players_re.search(line)
                if players_match:
                    player_count = int(players_match.group(1))
                    log.debug(f"Found player count {player_count}")
                    current_step = SpoilerStep.FIND_ENTRANCES
                continue
            case SpoilerStep.FIND_ENTRANCES:
                if line == "Entrances":
                    current_step = SpoilerStep.PROCESS_ENTRANCES
                    log.debug("Found entrances section")
                continue
            case SpoilerStep.PROCESS_ENTRANCES:
                world_match = entrance_world_re.search(line)
                if world_match:
                    current_world = world_match.group(1)
                    log.debug(f"Parsing world {current_world} entrances")
                    current_world = int(current_world) - 1  # index for player results
                    continue

                entrance_match = entrance_re.search(line)
                if entrance_match:
                    loc_words = entrance_match.group(6).replace("MM_", "").split("_")
                    loc_name = " ".join(w[0] + w[1:].lower() for w in loc_words)
                    loc_key = canonicalize(loc_name)
                    # Locations are 1:1 with entrances, but put each entrance in a list to conform with HintData format
                    if loc_key not in entrance_data:
                        entrance_data[loc_key] = {
                            Entrances.NAME_KEY: loc_name,
                            Entrances.RESULTS_KEY: [[] for _ in range(player_count)],
                        }
                    entrance_name = entrance_match.group(2).replace("MM ", "")
                    entrance_data[loc_key][Entrances.RESULTS_KEY][current_world].append(
                        entrance_name
                    )
                    continue

                if line[0] == " ":
                    unparsed_lines.append(line)
                    log.info(f"Could not parse line: {line}")
                    continue

                # New section
                if loc_list_re.search(line):
                    current_step = SpoilerStep.PROCESS_LOCATIONS
                else:
                    current_step = SpoilerStep.FIND_LOCATIONS
                continue
            case SpoilerStep.FIND_LOCATIONS:
                if loc_list_re.search(line):
                    current_step = SpoilerStep.PROCESS_LOCATIONS
                    log.debug("Found location list")
                continue
            case SpoilerStep.PROCESS_LOCATIONS:
                world_match = loc_world_re.search(line)
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
                                ItemLocations.NAME_KEY: item_name,
                                ItemLocations.RESULTS_KEY: [
                                    [] for _ in range(player_count)
                                ],
                            }
                        item_locations[item_key][ItemLocations.RESULTS_KEY][
                            player
                        ].append(loc)
                    continue

                if not area_re.search(line):
                    unparsed_lines.append(line)
                    log.info(f"Could not parse line: {line}")
                continue
            case _:
                log.info(f"Unrecognized step {current_step}")
                item_locations = {}
                entrance_data = {}
                break

    entrances = Entrances(guild_id, entrance_data)

    if not len(item_locations):
        return (
            f"Failed to {current_step.value}. Could not extract data.",
            ItemLocations(guild_id, {}),
            entrances,
        )

    item_locs = ItemLocations(guild_id, item_locations)
    if len(unparsed_lines):
        # you can't put \ in an f-strings curly brace expr
        unparsed_lines_str = "\n".join(unparsed_lines)
        return (
            "Some lines in the spoiler log were unrecognized, which may result in missing item locations:\n"
            + f"||{unparsed_lines_str}||",
            item_locs,
            entrances,
        )
    return ("Spoiler log processed successfully!", item_locs, entrances)
