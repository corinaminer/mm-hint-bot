import logging
import os
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from entrances_handler import Entrances
from hint_handler import get_hint_response, set_cooldown
from item_location_handler import ItemLocations
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
        result_msg, item_locs, entrances = handle_spoiler_log(spoiler_lines, guild_id)
        guild_data = guilds.setdefault(guild_id, {})
        guild_data[HintType.ITEM] = item_locs
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
    """Provides location(s) of the given item for the given player."""
    guild_id = ctx.guild.id
    await ctx.send(
        get_hint_response(
            player,
            item,
            ctx.message.author.id,
            get_item_locations(guild_id),
        )
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
    """Provides entrance to the given location for the given player."""
    guild_id = ctx.guild.id
    await ctx.send(
        get_hint_response(
            player,
            location,
            ctx.message.author.id,
            get_entrances(guild_id),
        )
    )


@bot.command(name="search")
async def search(
    ctx, *, query=commands.parameter(description="Search query")
):
    """
    Lists items and entrances matching search query. Only returns matches that have the query as an exact substring (case-insensitive).
    """
    guild_id = ctx.guild.id
    await ctx.send(
        get_search_response(
            query, get_item_locations(guild_id), get_entrances(guild_id)
        )
    )


@bot.command(name="set-cooldown")
@commands.has_role(ADMIN_ROLE_NAME)
async def set_hint_cooldown(
    ctx,
    cooldown: int = commands.parameter(description="Cooldown time in minutes"),
    hint_type: Optional[str] = commands.parameter(
        description="Optional hint type: item | entrance | all (default all)"
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
        if HintType.ENTRANCE in hint_types_to_change:
            set_cooldown(cooldown, get_entrances(guild_id).hint_times)

        # TODO fix once we have more than two hint types
        changed = " and ".join([str(h) for h in hint_types_to_change])
        cooldown_plur = "s" if len(hint_types_to_change) > 1 else ""
        minute_plur = "s" if cooldown != 1 else ""
        await ctx.send(
            f"Set {changed} cooldown{cooldown_plur} to {cooldown} minute{minute_plur}."
        )


@bot.command(name="cooldown")
async def show_cooldown(
    ctx,
    hint_type: Optional[str] = commands.parameter(
        description="Optional hint type: item | entrance | all (default all)"
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
            hint_times = get_item_locations(guild_id).hint_times
            response_lines.append(
                f"Item hint cooldown: {hint_times.cooldown // 60} minutes"
            )
        if HintType.ENTRANCE in hint_types_to_show:
            # TODO Avoid showing entrance cooldown for hint_type "all" if entrance rando is off?
            hint_times = get_entrances(guild_id).hint_times
            response_lines.append(f"Entrance hint cooldown: {hint_times.cooldown // 60} minutes")
        await ctx.send("\n".join(response_lines))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRole):
        await ctx.send(str(error))


bot.run(TOKEN)
