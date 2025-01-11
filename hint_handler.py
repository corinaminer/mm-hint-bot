import logging
import re

from hint_data import HintData, HintTimes

log = logging.getLogger(__name__)

player_re = re.compile(r"^@?player(\d+)$")  # player14, @Player14


def infer_player_nums(author_roles):
    """Get player num(s) from author's roles"""
    nums = []
    for role in author_roles:
        match = player_re.search(role.name.lower())
        if match:
            nums.append(int(match.group(1)))
    return nums


def get_hint_response(
    player_number: int,
    item: str,
    author_id: int,
    hint_data: HintData,
) -> str:
    try:
        item_name, player_locs_for_item = hint_data.get_results(player_number, item)
    except FileNotFoundError:
        return "No data is currently stored. (Use !set-log to upload a spoiler log.)"
    except ValueError as e:
        return e.args[0]  # message

    if not len(player_locs_for_item):
        return f"For some reason there is no data for player {player_number}'s {item_name}........ sorry!!! There must be something wrong with me :( Please report."

    # Convert author ID for serialization; JSON keys must be strings
    hint_wait_time = hint_data.hint_times.attempt_hint(str(author_id))
    # TODO add flavors
    if hint_wait_time:
        log.debug(f"Hint denied due to cooldown until {hint_wait_time}")
        return f"Whoa nelly! You can't get another {hint_data.hint_type} hint until <t:{hint_wait_time}:T> -- hold your horses!!"

    return "\n".join(player_locs_for_item)


def format_wait_time(wait_time_sec: int) -> str:
    m = wait_time_sec // 60
    s = wait_time_sec % 60
    hr = m // 60
    m %= 60
    return f"{hr}:{m:02}:{s:02}"


def set_cooldown(cooldown_min: int, hint_times: HintTimes):
    cooldown_min = max(cooldown_min, 0)
    if hint_times.cooldown // 60 != cooldown_min:
        hint_times.set_cooldown(cooldown_min)
