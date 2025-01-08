from entrances import Entrances
from item_locations import ItemLocations


def get_search_response(
    query: str, item_locations: ItemLocations, entrances: Entrances
):
    try:
        matching_items = item_locations.find_matches(query)
    except FileNotFoundError:
        return "No location data is currently stored. (Use !set-log to upload a spoiler log.)"

    try:
        matching_locs = entrances.find_matches(query)
    except FileNotFoundError:
        # Entrances may be empty if not randomized
        matching_locs = []

    item_matches = (
        f"Matching items: {', '.join(matching_items)}" if len(matching_items) else ""
    )
    loc_matches = (
        f"Matching locations: {', '.join(matching_locs)}" if len(matching_locs) else ""
    )
    if item_matches == loc_matches:
        return "No matching items or entrances. Note that this command only finds matches that contain your query as an exact substring (case-insensitive)."
    return "\n".join([item_matches, loc_matches])
