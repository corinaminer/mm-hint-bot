import json
from enum import Enum

from consts import DISCORD_MAX_MSG_LENGTH


class HintType(Enum):
    ITEM = "item"
    ENTRANCE = "entrance"
    CHECK = "check"

    def __str__(self):
        return self.value


class HintResult:
    def __init__(self, success: bool):
        self.success = success


class SuccessfulHintResult(HintResult):
    def __init__(
        self,
        item_name: str,
        results: list[str],
        hint_type: HintType,
        player_num: int,
        is_new_hint,
    ):
        super().__init__(True)
        self.item_name = item_name
        self.results = results
        self.hint_type = hint_type
        self.player_num = player_num
        self.is_new_hint = is_new_hint


class FailedHintResult(HintResult):
    def __init__(self, error: str):
        super().__init__(False)
        self.error = error


def get_hint_types(query) -> list[HintType]:
    if query == "all":
        return [h for h in HintType]
    try:
        return [HintType(query)]
    except ValueError:
        return []


def compose_show_hints_message(hint_types: list[HintType], player_past_hints):
    message = ""
    for ht in hint_types:
        if ht in player_past_hints:
            message += f"**{ht.value.capitalize()} hints:**\n"
            for hint_result in player_past_hints[ht]:
                message += f"- {hint_result}\n"
        if len(message) > DISCORD_MAX_MSG_LENGTH:
            end_note = "\n...and more"
            message = message[: DISCORD_MAX_MSG_LENGTH - len(end_note)] + end_note
            break
    return message


def canonicalize(s: str) -> str:
    """Lowercases & removes punctuation"""
    new_s = ""
    for c in s.lower():
        if c.isalnum() or c == " ":
            new_s += c
    return new_s


def get_owl_aliases(owl_location):
    # Since check and item names for owl statues are so similar, ensure that we have all the same aliases
    # for a given owl statue's check and item. This way any hint request like "!hint ct owl" will tell the
    # user to disambiguate with !hint-item or !hint-check.
    suffixes = [" owl", " owl statue"]
    aliases = {owl_location + suffix for suffix in suffixes}
    aliases.add(f"owl statue {owl_location}")
    if owl_location == "clock town":
        aliases.update(["clocktown" + suffix for suffix in suffixes])
        aliases.update(["ct" + suffix for suffix in suffixes])
    elif owl_location == "southern swamp":
        aliases.update(["swamp" + suffix for suffix in suffixes])
    elif owl_location == "mountain village":
        aliases.update(["mv" + suffix for suffix in suffixes])
    elif owl_location == "great bay coast" or owl_location == "great bay":
        # This is the only case where check and item disagree on location name:
        # check is Great Bay Coast Owl Statue, item is Owl Statue (Great Bay)
        other_loc = "great bay coast" if owl_location == "great bay" else "great bay"
        aliases.update([other_loc + suffix for suffix in suffixes])
        aliases.add(f"owl statue {other_loc}")
        aliases.update(["gbc" + suffix for suffix in suffixes])
    return aliases


def store(data, filename: str):
    with open(filename, "w") as f:
        json.dump(data, f)


def load(filename: str):
    with open(filename, "r") as f:
        return json.load(f)
