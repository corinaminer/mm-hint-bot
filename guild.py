import logging
from dataclasses import dataclass
from typing import Optional

from checks import Checks
from consts import BOT_VERSION, VERSION_KEY
from entrances import Entrances
from hint_data import HintData
from hint_times import HintTimes
from item_locations import ItemLocations
from utils import HintType, load, store

log = logging.getLogger(__name__)


@dataclass
class Guild:
    """class to group a guild's info together"""

    def __init__(
        self,
        guild_id,
        item_locations: Optional[ItemLocations] = None,
        checks: Optional[Checks] = None,
        entrances: Optional[Entrances] = None,
    ):
        self.metadata = GuildMetadata(guild_id)
        self.item_locations = item_locations or ItemLocations(guild_id)
        self.checks = checks or Checks(guild_id)
        self.entrances = entrances or Entrances(guild_id)
        self.hint_times = HintTimes(guild_id)

    def get_hint_data(self, hint_type: HintType) -> HintData:
        match hint_type:
            case HintType.ITEM:
                return self.item_locations
            case HintType.CHECK:
                return self.checks
            case HintType.ENTRANCE:
                return self.entrances
            case _:
                raise ValueError(hint_type)


def guild_metadata_filename(guild_id) -> str:
    return f"{guild_id}-metadata.json"


class GuildMetadata:
    """Contains metadata for a guild"""

    DISABLED_HINT_TYPES_KEY = "disabled hint types"
    """
    Serialized structure:
    {
        VERSION_KEY: BOT_VERSION,
        DISABLED_HINT_TYPES_KEY: [
            # HintType values for disabled HintTypes
            "item",
            ...
        ]
    }
    """

    def __init__(self, guild_id, disabled_hint_types: Optional[list[HintType]] = None):
        """Creates guild data with disabled_hint_types if given, otherwise from hint types in file if it exists"""
        self.filename: str = guild_metadata_filename(guild_id)
        if disabled_hint_types is not None:
            self.disabled_hint_types = {ht for ht in disabled_hint_types}
            if len(disabled_hint_types):
                self.save()
        else:
            self.disabled_hint_types = self._get_hint_types_from_file()

    def get_enabled_hint_types(self):
        return [h for h in HintType if h not in self.disabled_hint_types]

    def enable_hint_types(self, hint_types: list[HintType]) -> bool:
        """Enables the given hint types. Returns False if these hint types were all already enabled."""
        changed = False
        for hint_type in hint_types:
            if hint_type in self.disabled_hint_types:
                self.disabled_hint_types.remove(hint_type)
                changed = True
        if changed:
            self.save()
        return changed

    def disable_hint_types(self, hint_types: list[HintType]) -> bool:
        """Disables the given hint types. Returns False if these hint types were all already disabled."""
        initial_len = len(self.disabled_hint_types)
        self.disabled_hint_types.update(hint_types)
        if initial_len != len(self.disabled_hint_types):
            self.save()
            return True
        return False

    def _get_hint_types_from_file(self) -> set[HintType]:
        try:
            data = load(self.filename)
        except FileNotFoundError:
            return set()
        data_version = data.get(VERSION_KEY)
        if data_version == BOT_VERSION:
            return {
                HintType(value) for value in data[GuildMetadata.DISABLED_HINT_TYPES_KEY]
            }

        # Data in file is outdated or corrupt. If it's a known old version, use it; otherwise ignore it.
        log.info(f"No protocol for guild metadata with version {data_version}")
        return set()

    def _get_filedata(self):
        return {
            VERSION_KEY: BOT_VERSION,
            GuildMetadata.DISABLED_HINT_TYPES_KEY: [
                ht.value for ht in self.disabled_hint_types
            ],
        }

    def save(self):
        store(self._get_filedata(), self.filename)
