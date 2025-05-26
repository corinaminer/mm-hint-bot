from test.conftest import TEST_GUILD_ID

from hint_data import HintData
from spoiler_log_handler import handle_spoiler_log

sample_spoiler_file = "sample_spoiler.txt"


def test_empty_spoiler():
    resp, item_locs, checks, entrances = handle_spoiler_log([], TEST_GUILD_ID)
    assert resp == "Failed to find player count. Could not extract data."
    assert item_locs.items == {} and checks.items == {} and entrances.items == {}


def test_no_entrances_or_locations():
    resp, item_locs, checks, entrances = handle_spoiler_log(
        ["  players: 2"], TEST_GUILD_ID
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
        spoiler.split("\n"), TEST_GUILD_ID
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
        spoiler.split("\n"), TEST_GUILD_ID
    )
    assert resp == "Location list is missing or empty. Could not extract data."
    assert item_locs.items == {} and checks.items == {}
    assert entrances.items == {
        "woodfall temple": {
            HintData.NAME_KEY: "Woodfall Temple",  # reformatted from LOCATION_NAME_REFORMATS
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
        spoiler_lines, TEST_GUILD_ID
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
        "woodfall temple": {
            HintData.NAME_KEY: "Woodfall Temple",
            HintData.RESULTS_KEY: [
                ["Clock Tower Platform to Clock Tower Roof"],
                ["Clock Tower Platform to Clock Tower Roof"],
            ],
        },
    }
