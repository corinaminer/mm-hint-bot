import json
from enum import Enum


class HintType(Enum):
    ITEM = "item"
    ENTRANCE = "entrance"
    CHECK = "check"

    def __str__(self):
        return self.value


def get_hint_types(query) -> list[HintType]:
    if query == "all":
        return [h for h in HintType]
    try:
        return [HintType(query)]
    except ValueError:
        return []


def canonicalize(s: str) -> str:
    """Lowercases & removes punctuation"""
    new_s = ""
    for c in s.lower():
        if c.isalnum() or c == " ":
            new_s += c
    return new_s


def store(data, filename: str):
    with open(filename, "w") as f:
        json.dump(data, f)


def load(filename: str):
    with open(filename, "r") as f:
        return json.load(f)
