import os

import pytest

from checks import Checks
from consts import BOT_VERSION, VERSION_KEY
from guild import Guild
from hint_data import DEFAULT_HINT_COOLDOWN_SEC, HintTimes, hint_times_filename
from hint_handler import (
    get_hint,
    get_hint_response,
    get_hint_without_type,
    infer_player_num,
)
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


class MockAuthor:
    def __init__(self, id, *roles: str):
        self.id = id
        self.roles = [MockRole(r) for r in roles]


def test_infer_player_nums():
    with pytest.raises(
        ValueError,
        match='Unable to infer player number from your roles. Please specify your player number, e.g. "!hint 3 sword".',
    ):
        infer_player_num([])

    with pytest.raises(
        ValueError,
        match='Unable to infer player number from your roles. Please specify your player number, e.g. "!hint 3 sword".',
    ):
        infer_player_num([MockRole("foo"), MockRole("player01")])

    with pytest.raises(
        ValueError,
        match='You have multiple player roles. Please specify player number to hint, e.g. "!hint 5 sword".',
    ):
        infer_player_num([MockRole("Player5"), MockRole("Player15")])

    assert infer_player_num([MockRole("player5")]) == 5
    assert infer_player_num([MockRole("Player15")]) == 15
    assert infer_player_num([MockRole("@Player10")]) == 10
    assert infer_player_num([MockRole("player 10")]) == 10


def test_get_hint_without_type():
    item_locs = ItemLocations(
        test_guild_id,
        {
            "foo": {
                ItemLocations.NAME_KEY: "Foo",
                ItemLocations.RESULTS_KEY: [["p1 result"]],
            },
            "bars baz": {
                ItemLocations.NAME_KEY: "Bar's Baz",
                ItemLocations.RESULTS_KEY: [["p1 result"]],
            },
        },
    )
    checks = Checks(
        test_guild_id,
        {
            "foo": {
                Checks.NAME_KEY: "Foo",
                Checks.RESULTS_KEY: [["p1 result"]],
            },
            "bar baz": {
                Checks.NAME_KEY: "Bar Baz",
                Checks.RESULTS_KEY: [["p1 result"]],
            },
        },
    )
    g = Guild(test_guild_id, item_locs, checks, None)
    author = MockAuthor(1)

    # Should fail if query matches item keys in two hint types
    duplicate_keys = get_hint_without_type(g, "foo", author, 1)
    assert (
        duplicate_keys
        == "Both item and check hints can match foo. Please use !hint-item or !hint-check."
    )

    match_key_and_alias = get_hint_without_type(g, "bar baz", author, 1)
    assert (
        match_key_and_alias
        == "Both item and check hints can match bar baz. Please use !hint-item or !hint-check."
    )

    # Should fail if no item key matches query
    no_match = get_hint_without_type(g, "no match", author, 1)
    assert (
        no_match == "Query no match not recognized. Try !search <keyword> to find it!"
    )

    # Should identify correct hint type, even if that type is disabled
    g.metadata.disable_hint_types([HintType.ITEM])
    hint_disabled = get_hint_without_type(g, "bars baz", author, 1)
    assert hint_disabled == "Item hints are not currently enabled."

    # Test successful call
    g.metadata.enable_hint_types([HintType.ITEM])
    success = get_hint_without_type(g, "bars baz", author, 1)
    assert success == "p1 result"


def test_get_hint():
    item_locs = ItemLocations(
        test_guild_id,
        {
            "foo": {
                ItemLocations.NAME_KEY: "Foo",
                ItemLocations.RESULTS_KEY: [["p1 result"], ["p2 result"]],
            }
        },
    )
    item_locs.hint_times.set_cooldown(0)
    author_with_role = MockAuthor(1, "player1")
    author_without_role = MockAuthor(2)

    hint_type_disabled = get_hint(
        item_locs, {HintType.ITEM}, author_with_role, None, "foo"
    )
    assert hint_type_disabled == "Item hints are not currently enabled."

    no_player_num = get_hint(
        item_locs, {HintType.CHECK}, author_without_role, None, "foo"
    )
    assert no_player_num.startswith("Unable to infer player number from your roles.")

    # Provided player num should take precedence over player num in roles
    assert get_hint(item_locs, set(), author_with_role, 2, "foo") == "p2 result"
    assert get_hint(item_locs, set(), author_with_role, None, "foo") == "p1 result"


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
