import json

BOT_VERSION = 1

IGNORED_ITEMS = {
    "Nothing",
    "Recovery Heart",
    "Piece of Heart",
    "Heart Container",
    "Small Magic Jar",
    "Large Magic Jar",
    "Deku Stick",
    "Fairy",
    "10 Arrows",
    "30 Arrows",
    "1 Bombchu",
    "5 Bombchu",
    "10 Bombchu",
    "5 Bombs",
    "10 Bombs",
    "10 Deku Nuts",
    "Green Rupee",
    "Blue Rupee",
    "Red Rupee",
    "Purple Rupee",
    "Silver Rupee",
    "Gold Rupee",
    "Green Potion",
    "Ocean Skulltula Token",
    "Swamp Skulltula Token",
    "Owl Statue (Clock Town)",
    "Owl Statue (Milk Road)",
    "Owl Statue (Southern Swamp)",
    "Owl Statue (Woodfall)",
    "Owl Statue (Mountain Village)",
    "Owl Statue (Snowhead)",
    "Owl Statue (Great Bay)",
    "Owl Statue (Zora Cape)",
    "Owl Statue (Ikana Canyon)",
    "Owl Statue (Stone Tower)",
}

STANDARD_ALIASES = {
    "bow": "heros bow",
    "cow mask": "romanis mask",
    "magic": "magic upgrade",
    "magic power": "magic upgrade",
    "scale": "progressive scale",
    "sniffa": "mask of scents",
    "strength": "progressive strength",
    "sword": "progressive sword",
    "wallet": "progressive wallet",
}


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
