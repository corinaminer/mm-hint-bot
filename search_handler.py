from checks import Checks
from entrances import Entrances
from item_locations import ItemLocations


def get_search_response(
    query: str, item_locations: ItemLocations, checks: Checks, entrances: Entrances
):
    try:
        matching_items = item_locations.find_matches(query)
    except FileNotFoundError:
        return "No location data is currently stored. (Use !set-log to upload a spoiler log.)"
    try:
        matching_checks = checks.find_matches(query)
    except FileNotFoundError:
        # Doesn't really make sense; there should be checks data if there is item location data
        matching_checks = []

    try:
        matching_locs = entrances.find_matches(query)
    except FileNotFoundError:
        # Entrances may be empty if not randomized
        matching_locs = []

    item_matches = (
        f"**Items:** {', '.join(matching_items)}" if len(matching_items) else ""
    )
    check_matches = (
        f"**Checks:** {', '.join(matching_checks)}" if len(matching_checks) else ""
    )
    loc_matches = (
        f"**Locations:** {', '.join(matching_locs)}" if len(matching_locs) else ""
    )
    if not len(item_matches) and not len(check_matches) and not len(loc_matches):
        return "No matching items, checks, or entrances. Note that this command only finds matches that contain your query as an exact substring (case-insensitive)."
    return "\n".join([item_matches, check_matches, loc_matches])
