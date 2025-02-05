import logging
import re

from consts import STANDARD_CHECK_ALIASES
from hint_data import HintData
from utils import HintType, get_owl_aliases

log = logging.getLogger(__name__)


class Checks(HintData):
    def __init__(self, guild_id, items=None):
        super().__init__(guild_id, HintType.CHECK, items)

    def generate_aliases(self):
        aliases = {}
        for alias, check_key in STANDARD_CHECK_ALIASES.items():
            if check_key in self.items:
                aliases[alias] = check_key
            else:
                log.debug(f"Skipping alias {alias}: No such check as {check_key}")
        for check_key in self.items:
            for alias in generate_check_aliases(check_key):
                aliases[alias] = check_key
        return aliases


owl_check_re = re.compile(r"^([a-z ]+) owl statue$")  # e.g. "clock town owl statue"


def generate_check_aliases(check_key):
    """Generates any additional aliases for a check given its original unmodified name."""
    owl_match = owl_check_re.search(check_key)
    if owl_match:
        owl_aliases = get_owl_aliases(owl_match.group(1))
        owl_aliases.remove(check_key)
        return list(owl_aliases) + [alias + " check" for alias in owl_aliases]
    return []
