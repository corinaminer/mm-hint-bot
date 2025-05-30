import logging
import re
from typing import Optional

from guild import Guild
from hint_data import HintData
from hint_times import HintTimes
from utils import (
    FailedHintResult,
    HintResult,
    HintType,
    SuccessfulHintResult,
    compose_show_hints_message,
    curtail_message,
)

log = logging.getLogger(__name__)

player_re = re.compile(r"^@?player ?([1-9]\d*)$")  # player14, @Player14


def infer_player_num(player: Optional[int], author_roles):
    """Get player num(s) from author's roles"""
    if player is not None:
        if player >= 1:
            return player
        raise ValueError(f"Invalid player number {player}.")

    player_num = None
    for role in author_roles:
        match = player_re.search(role.name.lower())
        if match:
            if player_num is not None:
                raise ValueError(
                    f"You have multiple player roles. Please specify player number."
                )
            player_num = int(match.group(1))
    if player_num is None:
        raise ValueError(
            "Unable to infer player number from your roles. Please specify your player number."
        )
    return player_num


def get_show_hints_response(
    player: int,
    hint_types: list[HintType],
    hint_times: HintTimes,
) -> str:
    past_hints_for_player = hint_times.past_hints.get(player, {})
    results = compose_show_hints_message(hint_types, past_hints_for_player)
    if not len(results):
        hints_qualifier = "" if len(hint_types) > 1 else f"{hint_types[0].value} "
        return f"Player {player} has not even redeemed any {hints_qualifier}hints yet! :horse: :zzz:"
    return results


def get_show_checks_response(player: int, hint_times: HintTimes) -> str:
    response = ""
    player_world_re = re.compile(f"^World {player} (.+)")
    for other_player in hint_times.past_hints:
        other_player_item_hints = hint_times.past_hints[other_player].get(
            HintType.ITEM, {}
        )
        for hinted_item, results in other_player_item_hints.items():
            for result in results:
                player_world_match = player_world_re.match(result)
                if player_world_match:
                    location = player_world_match.group(1)
                    response += f"- {location}: Player {other_player} {hinted_item}\n"
    if len(response):
        return curtail_message(response)
    return "No redeemed hints have pointed to checks in your world yet."


def get_hint_without_type(
    g: Guild, query: str, author, player: Optional[int]
) -> HintResult:
    item_key, hint_data = None, None
    for ht in HintType:
        hint_data_for_type = g.get_hint_data(ht)
        item_key_for_type = hint_data_for_type.get_item_key(query)
        if item_key_for_type is not None:
            if item_key is not None:
                other_ht = hint_data.hint_type
                return FailedHintResult(
                    f"Both {other_ht} and {ht} hints can match {query}. Please use !hint-{other_ht} or !hint-{ht}."
                )
            item_key, hint_data = item_key_for_type, hint_data_for_type

    if item_key is None:
        return FailedHintResult(
            f"Query {query} not recognized. Try !search <keyword> to find it!"
        )
    return get_hint(
        hint_data,
        g.hint_times,
        g.metadata.disabled_hint_types,
        author,
        player,
        item_key,
    )


def get_hint(
    hint_data: HintData,
    hint_times: HintTimes,
    disabled_hint_types: set[HintType],
    author,
    player_num: Optional[int],
    query: str,
) -> HintResult:
    if hint_data.hint_type in disabled_hint_types:
        return FailedHintResult(
            f"{hint_data.hint_type.value.capitalize()} hints are not currently enabled."
        )

    try:
        player_num = infer_player_num(player_num, author.roles)
    except ValueError as e:
        return FailedHintResult(e.args[0])

    return get_hint_response(player_num, query, author.id, hint_data, hint_times)


def get_hint_response(
    player_number: int,
    item: str,
    author_id: int,
    hint_data: HintData,
    hint_times: HintTimes,
) -> HintResult:
    try:
        item_name, player_locs_for_item = hint_data.get_results(player_number, item)
    except FileNotFoundError:
        return FailedHintResult(
            "No data is currently stored. (Use !set-log to upload a spoiler log.)"
        )
    except ValueError as e:
        return FailedHintResult(e.args[0])
    if not len(player_locs_for_item):
        return FailedHintResult(
            f"For some reason there is no data for player {player_number}'s {item_name}........ sorry!!! There must be something wrong with me :( Please report."
        )

    hint_wait_time = hint_times.attempt_hint(author_id, hint_data.hint_type)
    # TODO add flavors
    if hint_wait_time:
        log.debug(f"Hint denied due to cooldown until {hint_wait_time}")
        return FailedHintResult(
            f"Whoa nelly! You can't get another {hint_data.hint_type} hint until <t:{hint_wait_time}:T> -- hold your horses!!"
        )

    # Record hint time and hint for player
    is_new_hint = hint_times.record_hint(
        author_id,
        player_number,
        hint_data.hint_type,
        item_name,
        player_locs_for_item,
    )
    return SuccessfulHintResult(
        item_name, player_locs_for_item, hint_data.hint_type, player_number, is_new_hint
    )


def format_wait_time(wait_time_sec: int) -> str:
    m = wait_time_sec // 60
    s = wait_time_sec % 60
    hr = m // 60
    m %= 60
    return f"{hr}:{m:02}:{s:02}"
