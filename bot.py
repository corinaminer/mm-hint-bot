import logging
import os
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from checks import Checks
from entrances import Entrances
from hint_handler import get_hint_response, set_cooldown
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

# Cache tracking spoiler & hint data for each guild
# TODO: Periodically clear old cache items if a lot of guilds start using me :o
guilds = {}


def get_item_locations(guild_id) -> ItemLocations:
    guild_data = guilds.setdefault(guild_id, {})
    item_locs = guild_data.get(HintType.ITEM)
    if item_locs is None:
        log.debug("creating ItemLocations")
        item_locs = ItemLocations(guild_id)
        guild_data[HintType.ITEM] = item_locs
    return item_locs


def get_checks(guild_id) -> Checks:
    guild_data = guilds.setdefault(guild_id, {})
    checks = guild_data.get(HintType.CHECK)
    if checks is None:
        log.debug("creating Checks")
        checks = Checks(guild_id)
        guild_data[HintType.CHECK] = checks
    return checks


def get_entrances(guild_id) -> Entrances:
    guild_data = guilds.setdefault(guild_id, {})
    entrances = guild_data.get(HintType.ENTRANCE)
    if entrances is None:
        log.debug("creating Entrances")
        entrances = Entrances(guild_id)
        guild_data[HintType.ENTRANCE] = entrances
    return entrances


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


@bot.command(name="hint")
async def hint(
    ctx,
    player=commands.parameter(
        description="Player formatted without spaces, e.g. player5"
    ),
    *,
    item=commands.parameter(description="Item to look up"),
):
    """Reveals location(s) of the given item for the given player."""
    guild_id = ctx.guild.id
    await ctx.send(
        get_hint_response(player, item, ctx.author.id, get_item_locations(guild_id))
    )


@bot.command(name="hint-check")
async def hint_check(
    ctx,
    player=commands.parameter(
        description="Player formatted without spaces, e.g. player5"
    ),
    *,
    check=commands.parameter(description="Check to look up"),
):
    """Reveals item at the given check for the given player."""
    guild_id = ctx.guild.id
    await ctx.send(
        get_hint_response(player, check, ctx.author.id, get_checks(guild_id))
    )


@bot.command(name="hint-entrance")
async def hint_entrance(
    ctx,
    player=commands.parameter(
        description="Player formatted without spaces, e.g. player5"
    ),
    *,
    location=commands.parameter(description="Location to look up"),
):
    """Reveals entrance to the given location for the given player."""
    guild_id = ctx.guild.id
    await ctx.send(
        get_hint_response(player, location, ctx.author.id, get_entrances(guild_id))
    )


@bot.command(name="search")
async def search(ctx, *, query=commands.parameter(description="Search query")):
    """
    Lists items, checks, and entrances matching search query. Only returns matches that have the query as an exact substring (case-insensitive).
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
    hint_type: Optional[str] = commands.parameter(
        description="Optional hint type: item | check | entrance | all (default all)"
    ),
):
    """
    Sets hint cooldown time in minutes. Admin-only.
    """
    guild_id = ctx.guild.id
    hint_types_to_change = get_hint_types(hint_type or "all")
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
async def show_cooldown(
    ctx,
    hint_type: Optional[str] = commands.parameter(
        description="Optional hint type: item | check | entrance | all (default all)"
    ),
):
    """
    Shows hint cooldown time for the given hint type, or all by default.
    """
    guild_id = ctx.guild.id
    hint_types_to_show = get_hint_types(hint_type or "all")
    if not len(hint_types_to_show):
        await ctx.send(f"Unrecognized hint type '{hint_type}'.")
    else:
        response_lines = []
        if HintType.ITEM in hint_types_to_show:
            cooldown = get_item_locations(guild_id).hint_times.cooldown // 60
            response_lines.append(
                f"Item hint cooldown: {cooldown} minute{'s' if cooldown != 1 else ''}"
            )
        if HintType.CHECK in hint_types_to_show:
            cooldown = get_checks(guild_id).hint_times.cooldown // 60
            response_lines.append(
                f"Check hint cooldown: {cooldown} minute{'s' if cooldown != 1 else ''}"
            )
        if HintType.ENTRANCE in hint_types_to_show:
            # TODO Avoid showing entrance cooldown for hint_type "all" if entrance rando is off?
            cooldown = get_entrances(guild_id).hint_times.cooldown // 60
            response_lines.append(
                f"Entrance hint cooldown: {cooldown} minute{'s' if cooldown != 1 else ''}"
            )
        await ctx.send("\n".join(response_lines))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRole):
        await ctx.send(str(error))


bot.run(TOKEN)
