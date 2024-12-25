import os

import pytest

from consts import (
    BOT_VERSION,
    HINT_TIMES_FILENAME_SUFFIX,
    ITEM_LOCATIONS_FILENAME_SUFFIX,
    VERSION_KEY,
)
from hint_handler import (
    COOLDOWN_KEY,
    DEFAULT_HINT_COOLDOWN_MIN,
    MEMBERS_KEY,
    get_hint_response,
    get_hint_times_data,
)
from item_location_handler import (
    ALIASES_KEY,
    ITEM_LOCATIONS_KEY,
    ITEM_NAME_KEY,
    ITEMS_KEY,
)
from utils import FileHandler

test_guild_id = "test-guild-id"


@pytest.fixture
def hint_times_fh():
    fh = FileHandler(HINT_TIMES_FILENAME_SUFFIX)
    yield fh
    filename = fh._get_filename(test_guild_id)
    if os.path.exists(filename):
        os.remove(filename)


item_key = "kafeis mask"
item_name = "Kafei's Mask"
item_alias = "lost manchild mask"
player1_locs = ["Location 1"]
player2_locs = ["Location 2", "Location 3"]
player3_locs = []


@pytest.fixture
def populate_item_locs():
    fh = FileHandler(ITEM_LOCATIONS_FILENAME_SUFFIX)

    def store_locations():
        fh.store(
            {
                VERSION_KEY: BOT_VERSION,
                ITEMS_KEY: {
                    item_key: {
                        ITEM_NAME_KEY: item_name,
                        ITEM_LOCATIONS_KEY: [player1_locs, player2_locs, player3_locs],
                    }
                },
                ALIASES_KEY: {item_alias: item_key},
            },
            test_guild_id,
        )

    yield store_locations

    filename = fh._get_filename(test_guild_id)
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
    assert (
        response
        == "Item foo not recognized. (Not case-sensitive.) Try !search <keyword> to find it!"
    )

    response = get_hint_response("player0", item_name, 0, test_guild_id)
    assert response == "Invalid player number 0."
    response = get_hint_response("player4", item_name, 0, test_guild_id)
    assert response == "Invalid player number 4."

    response = get_hint_response("player3", item_name, 0, test_guild_id)
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
    response = get_hint_response("player1", item_name, 0, test_guild_id)
    assert response == player1_locs[0]  # player1 has one location

    # Successful hint should trigger creation of hint timestamps file, and result in cooldown response
    hint_times_data = hint_times_fh.load(test_guild_id)
    assert hint_times_data[COOLDOWN_KEY] == DEFAULT_HINT_COOLDOWN_MIN
    assert hint_times_data[MEMBERS_KEY].keys() == {"0"}
    response = get_hint_response("player1", item_name, 0, test_guild_id)
    assert response.startswith("Please chill for another 0:29:5")

    # New author should be successful with the same hint request, once
    response = get_hint_response("player1", item_name, 1, test_guild_id)
    assert response == player1_locs[0]
    response = get_hint_response("player1", item_name, 1, test_guild_id)
    assert response.startswith("Please chill for another 0:29:5")

    # Test response with item key and alias
    response = get_hint_response("player1", item_key, 2, test_guild_id)
    assert response == player1_locs[0]
    response = get_hint_response("player1", item_alias, 3, test_guild_id)
    assert response == player1_locs[0]

    # Test response with multiple locations
    response = get_hint_response("player2", item_name, 4, test_guild_id)
    assert response == "\n".join(player2_locs)  # player2 has two locations


def test_update_version(hint_times_fh):
    import time

    cooldown = 101
    now = time.time()
    outdated_hint_time = now - (cooldown * 60) - 1
    relevant_hint_time = now - ((cooldown - 1) * 60)
    v0_hint_times = {
        COOLDOWN_KEY: cooldown,
        MEMBERS_KEY: {},
        "0": outdated_hint_time,
        "1": relevant_hint_time,
    }
    hint_times_fh.store(v0_hint_times, test_guild_id)

    expected_updated_data = {
        VERSION_KEY: BOT_VERSION,
        COOLDOWN_KEY: cooldown,
        MEMBERS_KEY: {"1": relevant_hint_time},
    }
    assert get_hint_times_data(test_guild_id) == expected_updated_data
    assert hint_times_fh.load(test_guild_id) == expected_updated_data
