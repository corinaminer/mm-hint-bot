import os

import pytest

from checks import Checks
from guild import Guild
from hint_handler import (
    get_hint,
    get_hint_response,
    get_hint_without_type,
    get_show_hints_response,
    infer_player_num,
)
from hint_times import HintTimes, hint_times_filename
from item_locations import ItemLocations
from utils import HintType, load

test_guild_id = "test-guild-id"
hint_times_file = hint_times_filename(test_guild_id)

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
        match="Unable to infer player number from your roles. Please specify your player number.",
    ):
        infer_player_num(None, [])

    with pytest.raises(
        ValueError,
        match="Unable to infer player number from your roles. Please specify your player number.",
    ):
        infer_player_num(None, [MockRole("foo"), MockRole("player01")])

    with pytest.raises(
        ValueError,
        match="You have multiple player roles. Please specify player number.",
    ):
        infer_player_num(None, [MockRole("Player5"), MockRole("Player15")])

    assert infer_player_num(None, [MockRole("player5")]) == 5
    assert infer_player_num(None, [MockRole("Player15")]) == 15
    assert infer_player_num(None, [MockRole("@Player10")]) == 10
    assert infer_player_num(None, [MockRole("player 10")]) == 10

    with pytest.raises(ValueError, match="Invalid player number 0."):
        infer_player_num(0, [MockRole("player5")])

    assert infer_player_num(1, [MockRole("player5")]) == 1


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
        duplicate_keys.error
        == "Both item and check hints can match foo. Please use !hint-item or !hint-check."
    )

    match_key_and_alias = get_hint_without_type(g, "bar baz", author, 1)
    assert (
        match_key_and_alias.error
        == "Both item and check hints can match bar baz. Please use !hint-item or !hint-check."
    )

    # Should fail if no item key matches query
    no_match = get_hint_without_type(g, "no match", author, 1)
    assert (
        no_match.error
        == "Query no match not recognized. Try !search <keyword> to find it!"
    )

    # Should identify correct hint type, even if that type is disabled
    g.metadata.disable_hint_types([HintType.ITEM])
    hint_disabled = get_hint_without_type(g, "bars baz", author, 1)
    assert hint_disabled.error == "Item hints are not currently enabled."

    # Test successful call
    g.metadata.enable_hint_types([HintType.ITEM])
    success = get_hint_without_type(g, "bars baz", author, 1)
    assert success.results == ["p1 result"]


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
    hint_times = HintTimes(test_guild_id)
    hint_times.set_cooldown(0, HintType.ITEM)
    author_with_role = MockAuthor(1, "player1")
    author_without_role = MockAuthor(2)

    hint_type_disabled = get_hint(
        item_locs, hint_times, {HintType.ITEM}, author_with_role, None, "foo"
    )
    assert hint_type_disabled.error == "Item hints are not currently enabled."

    no_player_num = get_hint(
        item_locs, hint_times, {HintType.CHECK}, author_without_role, None, "foo"
    )
    assert no_player_num.error.startswith(
        "Unable to infer player number from your roles."
    )

    # Provided player num should take precedence over player num in roles
    assert get_hint(
        item_locs, hint_times, set(), author_with_role, 2, "foo"
    ).results == ["p2 result"]
    assert get_hint(
        item_locs, hint_times, set(), author_with_role, None, "foo"
    ).results == ["p1 result"]


def test_get_hint_response_failures():
    item_locs = ItemLocations(test_guild_id, {})
    hint_times = HintTimes(test_guild_id)
    response = get_hint_response(1, "foo", 0, item_locs, hint_times).error
    assert (
        response
        == "No data is currently stored. (Use !set-log to upload a spoiler log.)"
    )

    item_locs = ItemLocations(test_guild_id, item_locs_dict)

    # HintData.get_results is responsible for validating search query and player number.
    # Test one such request to make sure the result from HintData is handled correctly.
    response = get_hint_response(1, "foo", 0, item_locs, hint_times).error
    assert response == "Item foo not recognized. Try !search <keyword> to find it!"

    response = get_hint_response(3, item_key, 0, item_locs, hint_times).error
    assert (
        response
        == f"For some reason there is no data for player 3's {item_name}........ sorry!!! There must be something wrong with me :( Please report."
    )

    # None of these should have triggered a hint timestamp to be recorded
    with pytest.raises(FileNotFoundError):
        load(hint_times_file)


def test_get_hint_response():
    item_locs = ItemLocations(test_guild_id, item_locs_dict)
    hint_times = HintTimes(test_guild_id)

    # First hint success
    response = get_hint_response(1, item_key, 0, item_locs, hint_times)
    assert response.results == player1_locs

    # Successful hint should trigger creation of hint timestamps file, and result in cooldown response
    hint_times_data = load(hint_times_file)
    assert hint_times_data[HintTimes.HINT_TIMES_KEY].keys() == {"0"}
    response = get_hint_response(1, item_key, 0, item_locs, hint_times)
    assert response.error.startswith(
        "Whoa nelly! You can't get another item hint until <t:"
    )

    # New author should be successful with the same hint request, once
    response = get_hint_response(1, item_key, 1, item_locs, hint_times)
    assert response.results == player1_locs
    response = get_hint_response(1, item_key, 1, item_locs, hint_times)
    assert response.error.startswith(
        "Whoa nelly! You can't get another item hint until <t:"
    )

    # Test response with item name and alias
    response = get_hint_response(1, item_name, 2, item_locs, hint_times)
    assert response.results == player1_locs
    response = get_hint_response(1, item_alias, 3, item_locs, hint_times)
    assert response.results == player1_locs

    # Test response with multiple locations
    response = get_hint_response(2, item_key, 4, item_locs, hint_times)
    assert response.results == player2_locs  # player2 has two locations


def test_get_show_hints_response():
    hint_times = HintTimes(test_guild_id)

    resp = get_show_hints_response(1, [HintType.ITEM], hint_times)
    assert resp == "Player 1 has not even redeemed any item hints yet! :horse: :zzz:"

    is_new_hint = hint_times.record_hint(5, 1, HintType.ITEM, "foo")
    assert is_new_hint is True
    resp = get_show_hints_response(1, [HintType.ITEM, HintType.CHECK], hint_times)
    assert resp == "**Item hints:**\n- foo\n"
    is_new_hint = hint_times.record_hint(5, 1, HintType.ITEM, "foo")
    assert is_new_hint is False

    # Does not surface that recorded hint if asked about a different player or hint type
    resp = get_show_hints_response(2, [HintType.ITEM], hint_times)
    assert resp == "Player 2 has not even redeemed any item hints yet! :horse: :zzz:"
    resp = get_show_hints_response(1, [HintType.CHECK], hint_times)
    assert resp == "Player 1 has not even redeemed any check hints yet! :horse: :zzz:"
