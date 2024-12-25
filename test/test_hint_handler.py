import os
import time

import pytest

from consts import BOT_VERSION, VERSION_KEY
from hint_handler import DEFAULT_HINT_COOLDOWN_SEC, HintTimes, get_hint_response
from item_location_handler import ItemLocations, set_item_locations

test_guild_id = "test-guild-id"


@pytest.fixture
def hint_times_fh():
    yield HintTimes.fh
    filename = HintTimes.fh._get_filename(test_guild_id)
    if os.path.exists(filename):
        os.remove(filename)


item_key = "kafeis mask"
item_name = "Kafei's Mask"
item_alias = "kafei mask"
player1_locs = ["Location 1"]
player2_locs = ["Location 2", "Location 3"]
player3_locs = []


@pytest.fixture
def populate_item_locs():
    # Clear any existing ItemLocations first
    set_item_locations({}, test_guild_id)

    def store_locations():
        set_item_locations(
            {
                item_key: {
                    ItemLocations.ITEM_NAME_KEY: item_name,
                    ItemLocations.ITEM_LOCATIONS_KEY: [
                        player1_locs,
                        player2_locs,
                        player3_locs,
                    ],
                }
            },
            test_guild_id,
        )

    yield store_locations

    filename = ItemLocations.fh._get_filename(test_guild_id)
    if os.path.exists(filename):
        os.remove(filename)


def test_get_hint_failures(hint_times_fh, populate_item_locs):
    response = get_hint_response("playerx", "foo", 0, test_guild_id)
    assert (
        response
        == f'Unrecognized player playerx. (Did you format without spaces as in "player5"?)'
    )

    response = get_hint_response("player1", "foo", 0, test_guild_id)
    assert (
        response
        == "No data is currently stored. (Use !set-log to upload a spoiler log.)"
    )

    populate_item_locs()

    response = get_hint_response("player1", "foo", 0, test_guild_id)
    assert response == "Item foo not recognized. Try !search <keyword> to find it!"

    response = get_hint_response("player0", item_key, 0, test_guild_id)
    assert response == "Invalid player number 0."
    response = get_hint_response("player4", item_key, 0, test_guild_id)
    assert response == "Invalid player number 4."

    response = get_hint_response("player3", item_key, 0, test_guild_id)
    assert (
        response
        == f"For some reason there are no locations listed for player3's {item_name}........ sorry!!! There must be something wrong with me :( Please report."
    )

    # None of these should have triggered a hint timestamp to be recorded
    with pytest.raises(FileNotFoundError):
        hint_times_fh.load(test_guild_id)


def test_get_hint_response(hint_times_fh, populate_item_locs):
    populate_item_locs()

    # First hint success
    response = get_hint_response("player1", item_key, 0, test_guild_id)
    assert response == player1_locs[0]  # player1 has one location

    # Successful hint should trigger creation of hint timestamps file, and result in cooldown response
    hint_times_data = hint_times_fh.load(test_guild_id)
    assert hint_times_data[HintTimes.COOLDOWN_KEY] == DEFAULT_HINT_COOLDOWN_SEC
    assert hint_times_data[HintTimes.ASKERS_KEY].keys() == {"0"}
    response = get_hint_response("player1", item_key, 0, test_guild_id)
    assert response[:-1] == "Please chill for another 0:29:5"

    # New author should be successful with the same hint request, once
    response = get_hint_response("player1", item_key, 1, test_guild_id)
    assert response == player1_locs[0]
    response = get_hint_response("player1", item_key, 1, test_guild_id)
    assert response[:-1] == "Please chill for another 0:29:5"

    # Test response with item name and alias
    response = get_hint_response("player1", item_name, 2, test_guild_id)
    assert response == player1_locs[0]
    response = get_hint_response("player1", item_alias, 3, test_guild_id)
    assert response == player1_locs[0]

    # Test response with multiple locations
    response = get_hint_response("player2", item_key, 4, test_guild_id)
    assert response == "\n".join(player2_locs)  # player2 has two locations


def test_update_version_v0(hint_times_fh):
    cooldown = DEFAULT_HINT_COOLDOWN_SEC * 2  # purposely non-default
    now = time.time()
    outdated_hint_time = now - cooldown - 1
    relevant_hint_time = now - cooldown + 60
    v0_hint_times = {
        "cooldown": cooldown // 60,  # v0 cooldown was in minutes
        "members": {},
        "0": outdated_hint_time,
        "1": relevant_hint_time,
    }
    hint_times_fh.store(v0_hint_times, test_guild_id)

    expected_askers = {"1": relevant_hint_time}
    expected_updated_data = {
        VERSION_KEY: BOT_VERSION,
        HintTimes.COOLDOWN_KEY: cooldown,
        HintTimes.ASKERS_KEY: expected_askers,
    }
    hint_times = HintTimes(test_guild_id)
    assert hint_times.cooldown == cooldown and hint_times.askers == expected_askers
    assert hint_times_fh.load(test_guild_id) == expected_updated_data


def test_unknown_version(hint_times_fh):
    # If version is unknown, HintTimes should fall back on default values
    hint_times = {
        VERSION_KEY: "foo",
        HintTimes.COOLDOWN_KEY: 101,
        HintTimes.ASKERS_KEY: {
            "0": time.time(),
        },
    }
    hint_times_fh.store(hint_times, test_guild_id)

    expected_updated_data = {
        VERSION_KEY: BOT_VERSION,
        HintTimes.COOLDOWN_KEY: DEFAULT_HINT_COOLDOWN_SEC,
        HintTimes.ASKERS_KEY: {},
    }
    hint_times = HintTimes(test_guild_id)
    assert hint_times.cooldown == DEFAULT_HINT_COOLDOWN_SEC and hint_times.askers == {}
    hint_times.save()
    assert hint_times_fh.load(test_guild_id) == expected_updated_data
