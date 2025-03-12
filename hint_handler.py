import logging
import re
from typing import Optional

from guild import Guild
from hint_data import HintData
from hint_times import HintTimes
from utils import HintType

log = logging.getLogger(__name__)

player_re = re.compile(r"^@?player ?([1-9]\d*)$")  # player14, @Player14


def infer_player_num(author_roles):
    """Get player num(s) from author's roles"""
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
    player: Optional[int],
    author_roles,
    hint_types: list[HintType],
    hint_times: HintTimes,
) -> str:
    if player is None:
        try:
            player = infer_player_num(author_roles)
        except ValueError as e:
            return e.args[0]
    if player < 1:
        return f"Invalid player number {player}."

    past_hints_for_player = hint_times.past_hints.get(player, {})
    results = ""
    for ht in hint_types:
        if ht in past_hints_for_player:
            results += f"**{ht.value.capitalize()} hints:**\n"
            for hint_result in past_hints_for_player[ht]:
                results += f"- {hint_result}\n"
    if not len(results):
        hints_qualifier = "" if len(hint_types) > 1 else f"{hint_types[0].value} "
        return f"Player {player} has not even redeemed any {hints_qualifier}hints yet! :horse: :zzz:"
    return results


def get_hint_without_type(g: Guild, query: str, author, player: Optional[int]) -> str:
    item_key, hint_data = None, None
    for ht in HintType:
        hint_data_for_type = g.get_hint_data(ht)
        item_key_for_type = hint_data_for_type.get_item_key(query)
        if item_key_for_type is not None:
            if item_key is not None:
                other_ht = hint_data.hint_type
                return f"Both {other_ht} and {ht} hints can match {query}. Please use !hint-{other_ht} or !hint-{ht}."
            item_key, hint_data = item_key_for_type, hint_data_for_type

    if item_key is None:
        return f"Query {query} not recognized. Try !search <keyword> to find it!"
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
):
    if hint_data.hint_type in disabled_hint_types:
        return (
            f"{hint_data.hint_type.value.capitalize()} hints are not currently enabled."
        )

    if player_num is None:
        # Check for player num in author's roles
        try:
            player_num = infer_player_num(author.roles)
        except ValueError as err:
            return err.args[0]

    return get_hint_response(player_num, query, author.id, hint_data, hint_times)


def get_hint_response(
    player_number: int,
    item: str,
    author_id: int,
    hint_data: HintData,
    hint_times: HintTimes,
) -> str:
    try:
        item_name, player_locs_for_item = hint_data.get_results(player_number, item)
    except FileNotFoundError:
        return "No data is currently stored. (Use !set-log to upload a spoiler log.)"
    except ValueError as e:
        return e.args[0]  # message

    if not len(player_locs_for_item):
        return f"For some reason there is no data for player {player_number}'s {item_name}........ sorry!!! There must be something wrong with me :( Please report."

    hint_wait_time = hint_times.attempt_hint(author_id, hint_data.hint_type)
    # TODO add flavors
    if hint_wait_time:
        log.debug(f"Hint denied due to cooldown until {hint_wait_time}")
        return f"Whoa nelly! You can't get another {hint_data.hint_type} hint until <t:{hint_wait_time}:T> -- hold your horses!!"

    # Record hint time and hint for player
    hint_times.record_hint(
        author_id,
        player_number,
        hint_data.hint_type,
        f"{item_name}: {', '.join(player_locs_for_item)}",
    )

    return "\n".join(player_locs_for_item)


def format_wait_time(wait_time_sec: int) -> str:
    m = wait_time_sec // 60
    s = wait_time_sec % 60
    hr = m // 60
    m %= 60
    return f"{hr}:{m:02}:{s:02}"
