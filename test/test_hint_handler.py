import os
import time

import pytest

from consts import BOT_VERSION, VERSION_KEY
from hint_data import DEFAULT_HINT_COOLDOWN_SEC, HintTimes, hint_times_filename
from hint_handler import get_hint_response, infer_player_nums, set_cooldown
from item_locations import ItemLocations
from utils import HintType, load, store

test_guild_id = "test-guild-id"
hint_times_file = hint_times_filename(test_guild_id, HintType.ITEM)

item_key = "kafeis mask"
item_name = "Kafei's Mask"
item_alias = "kafei mask"
player1_locs = ["Location 1"]
player2_locs = ["Location 2", "Location 3"]
player3_locs = []
item_locs_dict = {
    item_key: {
        ItemLocations.NAME_KEY: item_name,
        ItemLocations.RESULTS_KEY: [
            player1_locs,
            player2_locs,
            player3_locs,
        ],
    }
}


@pytest.fixture(autouse=True)
def cleanup():
    yield

    for file in os.listdir():
        if file.startswith(test_guild_id) and file.endswith(".json"):
            os.remove(file)


class MockRole:
    def __init__(self, name: str):
        self.name = name


def test_infer_player_nums():
    def to_roles(role_names: list[str]):
        return [MockRole(rn) for rn in role_names]

    assert infer_player_nums([]) == []
    assert infer_player_nums(to_roles(["foo", "bar", "player"])) == []
    assert infer_player_nums(to_roles(["player5"])) == [5]
    assert infer_player_nums(to_roles(["Player5", "Player15"])) == [5, 15]


def test_get_hint_response_failures():
    item_locs = ItemLocations(test_guild_id, {})
    response = get_hint_response(1, "foo", 0, item_locs)
    assert (
        response
        == "No data is currently stored. (Use !set-log to upload a spoiler log.)"
    )

    item_locs = ItemLocations(test_guild_id, item_locs_dict)

    # HintData.get_results is responsible for validating search query and player number.
    # Test one such request to make sure the result from HintData is handled correctly.
    response = get_hint_response(1, "foo", 0, item_locs)
    assert response == "Item foo not recognized. Try !search <keyword> to find it!"

    response = get_hint_response(3, item_key, 0, item_locs)
    assert (
        response
        == f"For some reason there is no data for player 3's {item_name}........ sorry!!! There must be something wrong with me :( Please report."
    )

    # None of these should have triggered a hint timestamp to be recorded
    with pytest.raises(FileNotFoundError):
        load(hint_times_file)


def test_get_hint_response():
    item_locs = ItemLocations(test_guild_id, item_locs_dict)

    # First hint success
    response = get_hint_response(1, item_key, 0, item_locs)
    assert response == player1_locs[0]  # player1 has one location

    # Successful hint should trigger creation of hint timestamps file, and result in cooldown response
    hint_times_data = load(hint_times_file)
    assert hint_times_data[HintTimes.COOLDOWN_KEY] == DEFAULT_HINT_COOLDOWN_SEC
    assert hint_times_data[HintTimes.ASKERS_KEY].keys() == {"0"}
    response = get_hint_response(1, item_key, 0, item_locs)
    assert response.startswith("Whoa nelly! You can't get another item hint until <t:")

    # New author should be successful with the same hint request, once
    response = get_hint_response(1, item_key, 1, item_locs)
    assert response == player1_locs[0]
    response = get_hint_response(1, item_key, 1, item_locs)
    assert response.startswith("Whoa nelly! You can't get another item hint until <t:")

    # Test response with item name and alias
    response = get_hint_response(1, item_name, 2, item_locs)
    assert response == player1_locs[0]
    response = get_hint_response(1, item_alias, 3, item_locs)
    assert response == player1_locs[0]

    # Test response with multiple locations
    response = get_hint_response(2, item_key, 4, item_locs)
    assert response == "\n".join(player2_locs)  # player2 has two locations


def test_set_cooldown():
    hint_times = HintTimes(test_guild_id, HintType.ITEM)
    assert hint_times.cooldown == DEFAULT_HINT_COOLDOWN_SEC

    # run 2 hints, second should be denied
    assert hint_times.attempt_hint("0") == 0  # first hint is allowed
    hint_time = time.time()
    approx_next_hint_time = hint_time + DEFAULT_HINT_COOLDOWN_SEC
    next_hint_timestamp = hint_times.attempt_hint("0")
    assert approx_next_hint_time - 5 < next_hint_timestamp <= approx_next_hint_time

    # change cooldown to 0 and ask again
    set_cooldown(0, hint_times)
    assert hint_times.cooldown == 0
    assert hint_times.attempt_hint("0") == 0  # a second hint is allowed
    hint_time = time.time()

    # increase cooldown, hint should be denied again
    set_cooldown(5, hint_times)
    assert hint_times.cooldown == 5 * 60
    approx_next_hint_time = hint_time + 5 * 60
    next_hint_timestamp = hint_times.attempt_hint("0")
    assert approx_next_hint_time - 5 < next_hint_timestamp <= approx_next_hint_time

    # Setting cooldown to a negative number should set it to 0
    set_cooldown(-10, hint_times)
    assert hint_times.cooldown == 0


def test_unknown_version():
    # If version is unknown, HintTimes should fall back on default values
    hint_times = {
        VERSION_KEY: "foo",
        HintTimes.COOLDOWN_KEY: 101,
        HintTimes.ASKERS_KEY: {"0": 0},
    }
    store(hint_times, hint_times_file)

    expected_updated_data = {
        VERSION_KEY: BOT_VERSION,
        HintTimes.COOLDOWN_KEY: DEFAULT_HINT_COOLDOWN_SEC,
        HintTimes.ASKERS_KEY: {},
    }
    hint_times = HintTimes(test_guild_id, HintType.ITEM)
    assert hint_times.cooldown == DEFAULT_HINT_COOLDOWN_SEC and hint_times.askers == {}
    hint_times.save()
    assert load(hint_times_file) == expected_updated_data
