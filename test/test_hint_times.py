import time
from test.conftest import TEST_GUILD_ID

from hint_data import DEFAULT_HINT_COOLDOWN_SEC
from hint_times import HintTimes, hint_times_filename
from item_locations import ItemLocations
from utils import HintType, load

hint_times_fname = hint_times_filename(TEST_GUILD_ID)

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


def test_hint_times_cooldown():
    hint_times = HintTimes(TEST_GUILD_ID)
    assert hint_times.get_cooldown(HintType.ITEM) == DEFAULT_HINT_COOLDOWN_SEC

    # run 2 hints, second should be denied
    assert hint_times.attempt_hint(0, HintType.ITEM) == 0  # first hint is allowed
    hint_times.record_hint(0, 0, HintType.ITEM, "foo", ["bar"])
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


def test_clear_past_hints():
    hint_times = HintTimes(TEST_GUILD_ID)

    hint_times.record_hint(1, 2, HintType.ITEM, "foo", ["bar"])
    assert hint_times.past_hints == {2: {HintType.ITEM: {"foo": ["bar"]}}}
    saved_data = load(hint_times_fname)
    assert saved_data[HintTimes.PAST_HINTS_KEY] == {
        "2": {HintType.ITEM.value: {"foo": ["bar"]}}
    }

    hint_times.clear_past_hints()
    assert hint_times.past_hints == {}
    saved_data = load(hint_times_fname)
    assert saved_data[HintTimes.PAST_HINTS_KEY] == {}
