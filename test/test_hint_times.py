import os
import time

import pytest

from consts import BOT_VERSION, VERSION_KEY
from hint_data import DEFAULT_HINT_COOLDOWN_SEC, hint_data_filename
from hint_times import HintTimes
from item_locations import ItemLocations
from utils import HintType, load, store

test_guild_id = "test-guild-id"
hint_data_filename = hint_data_filename(test_guild_id, HintType.ITEM)

serialized_items = {
    "kafeis mask": {
        ItemLocations.NAME_KEY: "Kafei's Mask",
        ItemLocations.RESULTS_KEY: [["location1"], ["location2"]],
    },
    "mask of scents": {
        ItemLocations.NAME_KEY: "Mask of Scents",
        ItemLocations.RESULTS_KEY: [["location3"], ["location4"]],
    },
}
serialized_hint_data = {
    VERSION_KEY: BOT_VERSION,
    ItemLocations.DATA_KEY: serialized_items,
}


@pytest.fixture(autouse=True)
def cleanup():
    yield

    for file in os.listdir():
        if file.startswith(test_guild_id) and file.endswith(".json"):
            os.remove(file)


def test_hint_times_cooldown():
    hint_times = HintTimes(test_guild_id)
    assert hint_times.get_cooldown(HintType.ITEM) == DEFAULT_HINT_COOLDOWN_SEC

    # run 2 hints, second should be denied
    assert hint_times.attempt_hint(0, HintType.ITEM) == 0  # first hint is allowed
    hint_times.record_hint(0, 0, HintType.ITEM, "foo")
    hint_time = time.time()
    approx_next_hint_time = hint_time + DEFAULT_HINT_COOLDOWN_SEC
    next_hint_timestamp = hint_times.attempt_hint(0, HintType.ITEM)
    assert approx_next_hint_time - 5 < next_hint_timestamp <= approx_next_hint_time

    # change cooldown to 0 and ask again
    hint_times.set_all_cooldowns(0)
    assert hint_times.get_cooldown(HintType.ITEM) == 0
    assert hint_times.attempt_hint(0, HintType.ITEM) == 0  # a second hint is allowed
    hint_time = time.time()

    # increase cooldown, hint should be denied again
    hint_times.set_all_cooldowns(5)
    assert hint_times.get_cooldown(HintType.ITEM) == 5 * 60
    approx_next_hint_time = hint_time + 5 * 60
    next_hint_timestamp = hint_times.attempt_hint(0, HintType.ITEM)
    assert approx_next_hint_time - 5 < next_hint_timestamp <= approx_next_hint_time
