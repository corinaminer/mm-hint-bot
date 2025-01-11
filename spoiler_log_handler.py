import logging
import re
from enum import Enum
from typing import List

from checks import Checks
from consts import IGNORED_ITEMS, LOCATION_NAME_REFORMATS
from entrances import Entrances
from hint_data import HintData
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
    FIND_PLAYER_COUNT = 1
    FIND_ENTRANCES_OR_LOCATIONS = 2
    PROCESS_ENTRANCES = 3
    FIND_LOCATIONS = 4
    PROCESS_LOCATIONS = 5

    def __str__(self):
        return self.value


def handle_spoiler_log(
    spoiler_log_lines: List[str], guild_id
) -> tuple[str, ItemLocations, Checks, Entrances]:
    current_step = SpoilerStep.FIND_PLAYER_COUNT
    player_count = 0
    item_locations, check_data, entrance_data = {}, {}, {}

    current_world, current_world_player = None, None
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
                    current_step = SpoilerStep.FIND_ENTRANCES_OR_LOCATIONS
                continue
            case SpoilerStep.FIND_ENTRANCES_OR_LOCATIONS:
                if line == "Entrances":
                    current_step = SpoilerStep.PROCESS_ENTRANCES
                    log.debug("Found entrances section")
                elif loc_list_re.search(line):
                    current_step = SpoilerStep.PROCESS_LOCATIONS
                    log.debug("Found location list")
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
                    loc = entrance_match.group(6)
                    if "_FROM_" in loc:
                        # Assumes an entrance leading from X to Y will take you back to X if you return through it
                        continue
                    loc_name = LOCATION_NAME_REFORMATS.get(loc)
                    if loc_name is None:
                        loc_words = loc.replace("MM_", "").split("_")
                        loc_name = " ".join(w.capitalize() for w in loc_words)
                    loc_key = canonicalize(loc_name)
                    # Locations are 1:1 with entrances, but put each entrance in a list to conform with HintData format
                    if loc_key not in entrance_data:
                        entrance_data[loc_key] = {
                            HintData.NAME_KEY: loc_name,
                            HintData.RESULTS_KEY: [[] for _ in range(player_count)],
                        }
                    entrance_name = entrance_match.group(2).replace("MM ", "")
                    entrance_data[loc_key][HintData.RESULTS_KEY][current_world].append(
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
                    current_world_player = int(current_world) - 1
                    log.debug(f"Parsing world {current_world} locations")
                    continue

                loc_match = loc_re.search(line)
                if loc_match:
                    check_name = loc_match.group(1)
                    player = loc_match.group(2)  # player who will receive the item
                    item_name = loc_match.group(3)
                    if item_name.endswith(" (MM)"):
                        item_name = item_name[:-5]

                    # Add check to { check -> item } mapping
                    # Checks are 1:1 with items, but put each item in a list to conform with HintData format
                    check_key = canonicalize(check_name)
                    if check_key not in check_data:
                        check_data[check_key] = {
                            HintData.NAME_KEY: check_name,
                            HintData.RESULTS_KEY: [[] for _ in range(player_count)],
                        }
                    check_data[check_key][HintData.RESULTS_KEY][
                        current_world_player
                    ].append(f"Player {player} {item_name}")

                    if item_name not in IGNORED_ITEMS:
                        # Add item to { item -> locations } mapping
                        player = int(player) - 1
                        loc = f"World {current_world} {check_name}"
                        item_key = canonicalize(item_name)
                        if item_key not in item_locations:
                            item_locations[item_key] = {
                                HintData.NAME_KEY: item_name,
                                HintData.RESULTS_KEY: [[] for _ in range(player_count)],
                            }
                        item_locations[item_key][HintData.RESULTS_KEY][player].append(
                            loc
                        )
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

    checks = Checks(guild_id, check_data)
    entrances = Entrances(guild_id, entrance_data)

    if not len(item_locations):
        if current_step == SpoilerStep.FIND_PLAYER_COUNT:
            err = "Failed to find player count. Could not extract data."
        else:
            err = "Location list is missing or empty. Could not extract data."
        return err, ItemLocations(guild_id, {}), checks, entrances

    item_locs = ItemLocations(guild_id, item_locations)
    if len(unparsed_lines):
        # you can't put \ in an f-strings curly brace expr
        unparsed_lines_str = "\n".join(unparsed_lines)
        return (
            "Some lines in the spoiler log were unrecognized, which may result in missing item locations:\n"
            + f"||{unparsed_lines_str}||",
            item_locs,
            checks,
            entrances,
        )
    return "Spoiler log processed successfully!", item_locs, checks, entrances
