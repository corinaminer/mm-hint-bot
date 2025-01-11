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

    if not len(matching_items) and not len(matching_checks) and not len(matching_locs):
        return "No matching items, checks, or entrances."
    response = ""
    if len(matching_items):
        response += f"**Items:** {', '.join(matching_items)}\n"
    if len(matching_checks):
        response += f"**Checks:** {', '.join(matching_checks)}\n"
    if len(matching_locs):
        response += f"**Locations:** {', '.join(matching_locs)}\n"
    return response
