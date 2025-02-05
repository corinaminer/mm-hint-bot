import os

import pytest

from hint_data import hint_data_filename
from spoiler_log_handler import handle_spoiler_log
from utils import HintType

test_guild_id = "test-guild-id"
hint_data_filename = hint_data_filename(test_guild_id, HintType.ITEM)
owl_spoiler_file = "owl_spoiler.txt"


@pytest.fixture(autouse=True)
def cleanup():
    yield

    for file in os.listdir():
        if file.startswith(test_guild_id) and file.endswith(".json"):
            os.remove(file)


def test_generate_item_aliases():
    with open(owl_spoiler_file, "r") as f:
        spoiler_lines = f.read().split("\n")
    resp, item_locs, checks, entrances = handle_spoiler_log(
        spoiler_lines, test_guild_id
    )
    item_aliases = item_locs.aliases
    check_aliases = checks.aliases
    item_keys = set(item_aliases.values())
    check_keys = set(check_aliases.values())

    # The owl spoiler file just contains a single player with all the owl statue items and checks
    assert all("owl statue" in item_key for item_key in item_keys)
    assert all("owl statue" in check_key for check_key in check_keys)

    # Any item key should resolve both an owl item and an owl check
    for owl_item_key in item_keys:
        assert checks.get_item_key(owl_item_key) is not None
    for owl_check_key in check_keys:
        assert item_locs.get_item_key(owl_check_key) is not None

    # Any alias should resolve both an owl item and an owl check, unless it specifies "item" or "check"
    for owl_item_alias in item_locs.aliases:
        if owl_item_alias.endswith(" item"):
            assert checks.get_item_key(owl_item_alias) is None
        else:
            assert checks.get_item_key(owl_item_alias) is not None
    for owl_check_alias in checks.aliases:
        if owl_check_alias.endswith(" check"):
            assert item_locs.get_item_key(owl_check_alias) is None
        else:
            assert item_locs.get_item_key(owl_check_alias) is not None
