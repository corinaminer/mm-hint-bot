import json


def canonicalize(s: str) -> str:
    """Lowercases & removes punctuation"""
    new_s = ""
    for c in s.lower():
        if c.isalpha() or c == " ":
            new_s += c
    return new_s


class FileHandler:

    def __init__(self, filename_suffix):
        self.filename_suffix = filename_suffix

    def _get_filename(self, guild_id):
        return f"{guild_id}-{self.filename_suffix}.json"

    def store(self, data, guild_id):
        with open(self._get_filename(guild_id), "w") as f:
            json.dump(data, f)

    def load(self, guild_id):
        with open(self._get_filename(guild_id), "r") as f:
            return json.load(f)
