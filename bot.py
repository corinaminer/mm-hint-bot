import logging
import os
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from checks import Checks
from entrances import Entrances
from hint_handler import get_hint_response, infer_player_nums, set_cooldown
from item_locations import ItemLocations
from search_handler import get_search_response
from spoiler_log_handler import handle_spoiler_log
from utils import HintType, get_hint_types

ADMIN_ROLE_NAME = "admin"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

player_param = commands.parameter(
    description="Optional player number, e.g. 5. Defaults to author's @playerN role.",
    default=None,
)
hint_type_param = commands.parameter(
    description="Optional hint type: item | check | entrance | all",
    default="all",
    displayed_default="all",
)

# Cache tracking spoiler & hint data for each guild
# TODO: Periodically clear old cache items if a lot of guilds start using me :o
guilds = {}


def create_hint_data(hint_type: HintType, guild_id):
    match hint_type:
        case HintType.ITEM:
            return ItemLocations(guild_id)
        case HintType.CHECK:
            return Checks(guild_id)
        case HintType.ENTRANCE:
            return Entrances(guild_id)
        case _:
            raise ValueError(hint_type)


def get_hint_data(hint_type: HintType, guild_id):
    guild_data = guilds.setdefault(guild_id, {})
    hint_data = guild_data.get(hint_type)
    if hint_data is None:
        log.debug(f"creating {hint_type} data")
        hint_data = create_hint_data(hint_type, guild_id)
        guild_data[hint_type] = hint_data
    return hint_data


def get_item_locations(guild_id) -> ItemLocations:
    return get_hint_data(HintType.ITEM, guild_id)


def get_checks(guild_id) -> Checks:
    return get_hint_data(HintType.CHECK, guild_id)


def get_entrances(guild_id) -> Entrances:
    return get_hint_data(HintType.ENTRANCE, guild_id)


@bot.command(name="set-log")
@commands.has_role(ADMIN_ROLE_NAME)
async def set_spoiler_log(ctx):
    """
    Updates spoiler log from the attached text file. Admin-only.
    """
    if len(ctx.message.attachments) == 0:
        await ctx.send(
            "Did you forget something? Please attach your spoiler log as a text file :)"
        )
    else:
        data = await ctx.message.attachments[0].read()
        spoiler_lines = data.decode("utf-8").split("\n")
        guild_id = ctx.guild.id
        result_msg, item_locs, checks, entrances = handle_spoiler_log(
            spoiler_lines, guild_id
        )
        guild_data = guilds.setdefault(guild_id, {})
        guild_data[HintType.ITEM] = item_locs
        guild_data[HintType.CHECK] = checks
        guild_data[HintType.ENTRANCE] = entrances
        await ctx.send(result_msg)


def get_hint(guild_id, author, hint_type: HintType, player_num: int, query: str):
    if player_num is None:
        # Check for player num in author's roles
        player_nums_from_roles = infer_player_nums(author.roles)
        if not len(player_nums_from_roles):
            return f'Unable to detect a player ID in your roles. Please specify your player number, e.g. "!hint 3 sword".'
        player_num = player_nums_from_roles[0]
        if len(player_nums_from_roles) > 1:
            return f'You have multiple player roles. Please specify which player number you want to hint, e.g. "!hint {player_num} sword".'

    hint_data = get_hint_data(hint_type, guild_id)
    return get_hint_response(player_num, query, author.id, hint_data)


@bot.command(name="hint")
async def hint(
    ctx,
    player: Optional[int] = player_param,
    *,
    query: str = commands.parameter(description="Item, check, or location to look up"),
):
    """Reveals location(s) of a given item, result of a given check, or entrance to a given location."""
    item_key, hint_type, error = None, None, None
    for ht in get_hint_types("all"):
        item_key_for_type = get_hint_data(ht, ctx.guild.id).get_item_key(query)
        if item_key_for_type is not None:
            if item_key is not None:
                error = f"Both {hint_type} and {ht} hints can match {query}. Please use !hint-{hint_type} or !hint-{ht}."
                break
            item_key, hint_type = item_key_for_type, ht

    if error:
        await ctx.send(error)
    elif item_key is None:
        await ctx.send(
            f"Query {query} not recognized as an item, check, or location. Try !search <keyword> to find it!"
        )
    else:
        await ctx.send(get_hint(ctx.guild.id, ctx.author, hint_type, player, item_key))


@bot.command(name="hint-item")
async def hint_item(
    ctx,
    player: Optional[int] = player_param,
    *,
    item: str = commands.parameter(description="Item to look up"),
):
    """Reveals location(s) of the given item for the given player."""
    await ctx.send(get_hint(ctx.guild.id, ctx.author, HintType.ITEM, player, item))


@bot.command(name="hint-check")
async def hint_check(
    ctx,
    player: Optional[int] = player_param,
    *,
    check: str = commands.parameter(description="Check to look up"),
):
    """Reveals item at the given check for the given player."""
    await ctx.send(get_hint(ctx.guild.id, ctx.author, HintType.CHECK, player, check))


@bot.command(name="hint-entrance")
async def hint_entrance(
    ctx,
    player: Optional[int] = player_param,
    *,
    location: str = commands.parameter(description="Location to look up"),
):
    """Reveals entrance to the given location for the given player."""
    await ctx.send(
        get_hint(ctx.guild.id, ctx.author, HintType.ENTRANCE, player, location)
    )


@bot.command(name="search")
async def search(ctx, *, query=commands.parameter(description="Search query")):
    """
    Lists items, checks, and entrances matching search query.
    """
    guild_id = ctx.guild.id
    response = get_search_response(
        query,
        get_item_locations(guild_id),
        get_checks(guild_id),
        get_entrances(guild_id),
    )
    if len(response) >= 2000:
        # (actually discord limits the bot's messages to <2000 characters)
        await ctx.send(
            "Search results are too extensive for my little bot brain. Please be more specific."
        )
    else:
        await ctx.send(response)


@bot.command(name="set-cooldown")
@commands.has_role(ADMIN_ROLE_NAME)
async def set_hint_cooldown(
    ctx,
    cooldown: int = commands.parameter(description="Cooldown time in minutes"),
    hint_type: str = hint_type_param,
):
    """
    Sets hint cooldown time in minutes. Admin-only.
    """
    guild_id = ctx.guild.id
    hint_types_to_change = get_hint_types(hint_type)
    if not len(hint_types_to_change):
        await ctx.send(f"Unrecognized hint type '{hint_type}'.")
    else:
        cooldown = max(cooldown, 0)
        if HintType.ITEM in hint_types_to_change:
            set_cooldown(cooldown, get_item_locations(guild_id).hint_times)
        if HintType.CHECK in hint_types_to_change:
            set_cooldown(cooldown, get_checks(guild_id).hint_times)
        if HintType.ENTRANCE in hint_types_to_change:
            set_cooldown(cooldown, get_entrances(guild_id).hint_times)

        cooldown_str = f"{cooldown} minute{'s' if cooldown != 1 else ''}"
        if len(hint_types_to_change) == 1:
            await ctx.send(f"Set {hint_types_to_change[0]} cooldown to {cooldown_str}.")
        else:
            await ctx.send(f"Set all hint cooldowns to {cooldown_str}.")


@bot.command(name="cooldown")
async def show_cooldown(ctx, hint_type: str = hint_type_param):
    """
    Shows hint cooldown time for the given hint type, or all by default.
    """
    guild_id = ctx.guild.id
    hint_types_to_show: list[HintType] = get_hint_types(hint_type)
    if not len(hint_types_to_show):
        await ctx.send(f"Unrecognized hint type '{hint_type}'.")
    else:
        response_lines = []
        for ht in hint_types_to_show:
            # TODO Avoid showing entrance cooldown for hint_type "all" if entrance rando is off?
            cooldown = get_hint_data(ht, guild_id).hint_times.cooldown // 60
            response_lines.append(
                f"{ht.value.capitalize()} hint cooldown: {cooldown} minute{'s' if cooldown != 1 else ''}"
            )
        await ctx.send("\n".join(response_lines))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRole):
        await ctx.send(str(error))


bot.run(TOKEN)
