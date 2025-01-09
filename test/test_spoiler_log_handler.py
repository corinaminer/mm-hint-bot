import os

import pytest

from hint_data import HintData
from spoiler_log_handler import handle_spoiler_log

test_guild_id = "test-guild-id"
sample_spoiler_file = "sample_spoiler.txt"


@pytest.fixture(autouse=True)
def cleanup():
    yield

    for file in os.listdir():
        if file.startswith(test_guild_id) and file.endswith(".json"):
            os.remove(file)


def test_empty_spoiler():
    resp, item_locs, checks, entrances = handle_spoiler_log([], test_guild_id)
    assert resp == "Failed to find player count. Could not extract data."
    assert item_locs.items == {} and checks.items == {} and entrances.items == {}


def test_no_entrances_or_locations():
    resp, item_locs, checks, entrances = handle_spoiler_log(
        ["  players: 2"], test_guild_id
    )
    assert resp == "Location list is missing or empty. Could not extract data."
    assert item_locs.items == {} and checks.items == {} and entrances.items == {}


def test_spoiler_no_entrances():
    # Should still be successful if entrances are not randomized
    spoiler = """
  players: 2
Location List (2)
  World 1 (1)
    Tingle (1):
      MM Tingle Map Clock Town: Player 1 Light Arrows (MM)
  World 2 (1)
    Tingle (1):
      MM Tingle Map Clock Town: Player 2 Light Arrows (MM)
    """
    resp, item_locs, checks, entrances = handle_spoiler_log(
        spoiler.split("\n"), test_guild_id
    )
    assert resp == "Spoiler log processed successfully!"
    assert entrances.items == {}
    assert item_locs.items == {
        "light arrows": {
            HintData.NAME_KEY: "Light Arrows",
            HintData.RESULTS_KEY: [
                ["World 1 Tingle Map Clock Town"],
                ["World 2 Tingle Map Clock Town"],
            ],
        }
    }
    assert checks.items == {
        "tingle map clock town": {
            HintData.NAME_KEY: "Tingle Map Clock Town",
            HintData.RESULTS_KEY: [
                ["Player 1 Light Arrows"],
                ["Player 2 Light Arrows"],
            ],
        }
    }


def test_spoiler_no_locations():
    # Still handles entrances if no locations are included, but give failure response since this is unexpected
    spoiler = """
  players: 2
Entrances
  World 1
    MM Clock Tower Platform to MM Clock Tower Roof (MM_CLOCK_TOWER_ROOF) -> MM Woodfall Temple from MM Woodfall Front of Temple (MM_TEMPLE_WOODFALL)
  World 2
    MM Clock Tower Platform to MM Clock Tower Roof (MM_CLOCK_TOWER_ROOF) -> MM Woodfall Temple from MM Woodfall Front of Temple (MM_TEMPLE_WOODFALL)
    """
    resp, item_locs, checks, entrances = handle_spoiler_log(
        spoiler.split("\n"), test_guild_id
    )
    assert resp == "Location list is missing or empty. Could not extract data."
    assert item_locs.items == {} and checks.items == {}
    assert entrances.items == {
        "temple woodfall": {
            HintData.NAME_KEY: "Temple Woodfall",
            HintData.RESULTS_KEY: [
                ["Clock Tower Platform to Clock Tower Roof"],
                ["Clock Tower Platform to Clock Tower Roof"],
            ],
        }
    }


def test_complete_spoiler():
    with open(sample_spoiler_file, "r") as f:
        spoiler_lines = f.read().split("\n")
    resp, item_locs, checks, entrances = handle_spoiler_log(
        spoiler_lines, test_guild_id
    )
    assert resp == "Spoiler log processed successfully!"
    assert item_locs.items == {
        # The spoiler log also contains a Red Rupee and a 10 Deku Nuts, which should be ignored
        "progressive sword": {
            HintData.NAME_KEY: "Progressive Sword",
            HintData.RESULTS_KEY: [
                [
                    "World 1 Tingle Map Clock Town",
                    "World 2 Tingle Map Snowhead",
                ],
                [
                    "World 2 Tingle Map Woodfall",
                    "World 2 Tingle Map Ranch",
                ],
            ],
        },
        "light arrows": {
            HintData.NAME_KEY: "Light Arrows",
            HintData.RESULTS_KEY: [
                ["World 1 Tingle Map Woodfall"],
                ["World 1 Tingle Map Snowhead"],
            ],
        },
    }
    assert checks.items == {
        "tingle map clock town": {
            HintData.NAME_KEY: "Tingle Map Clock Town",
            HintData.RESULTS_KEY: [
                ["Player 1 Progressive Sword"],
                ["Player 1 10 Deku Nuts"],
            ],
        },
        "tingle map woodfall": {
            HintData.NAME_KEY: "Tingle Map Woodfall",
            HintData.RESULTS_KEY: [
                ["Player 1 Light Arrows"],
                ["Player 2 Progressive Sword"],
            ],
        },
        "tingle map snowhead": {
            HintData.NAME_KEY: "Tingle Map Snowhead",
            HintData.RESULTS_KEY: [
                ["Player 2 Light Arrows"],
                ["Player 1 Progressive Sword"],
            ],
        },
        "tingle map ranch": {
            HintData.NAME_KEY: "Tingle Map Ranch",
            HintData.RESULTS_KEY: [
                ["Player 2 Red Rupee"],
                ["Player 2 Progressive Sword"],
            ],
        },
    }
    assert entrances.items == {
        "clock tower roof": {
            HintData.NAME_KEY: "Clock Tower Roof",
            HintData.RESULTS_KEY: [
                ["Woodfall Front of Temple to Woodfall Temple"],
                ["Woodfall Front of Temple to Woodfall Temple"],
            ],
        },
        "clock town from clock tower roof": {
            HintData.NAME_KEY: "Clock Town From Clock Tower Roof",
            HintData.RESULTS_KEY: [
                ["Woodfall Temple to Woodfall Front of Temple"],
                ["Woodfall Temple to Woodfall Front of Temple"],
            ],
        },
        "temple woodfall": {
            HintData.NAME_KEY: "Temple Woodfall",
            HintData.RESULTS_KEY: [
                ["Clock Tower Platform to Clock Tower Roof"],
                ["Clock Tower Platform to Clock Tower Roof"],
            ],
        },
        "woodfall from temple": {
            HintData.NAME_KEY: "Woodfall From Temple",
            HintData.RESULTS_KEY: [
                ["Clock Tower Roof to Clock Tower Platform"],
                ["Clock Tower Roof to Clock Tower Platform"],
            ],
        },
    }
