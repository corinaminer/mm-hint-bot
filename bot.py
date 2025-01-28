import logging
import os
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from guild import Guild
from hint_handler import get_hint, get_hint_without_type
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
guilds: dict[str, Guild] = {}


def get_guild_data(guild_id):
    if guild_id not in guilds:
        guilds[guild_id] = Guild(guild_id)
    return guilds[guild_id]


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
        guilds[guild_id] = Guild(guild_id, item_locs, checks, entrances)
        await ctx.send(result_msg)


@bot.command(name="hint")
async def hint(
    ctx,
    player: Optional[int] = player_param,
    *,
    query: str = commands.parameter(description="Item, check, or location to look up"),
):
    """Reveals location(s) of a given item, result of a given check, or entrance to a given location."""
    g = get_guild_data(ctx.guild.id)
    await ctx.send(get_hint_without_type(g, query, ctx.author, player))


@bot.command(name="hint-item")
async def hint_item(
    ctx,
    player: Optional[int] = player_param,
    *,
    item: str = commands.parameter(description="Item to look up"),
):
    """Reveals location(s) of the given item for the given player."""
    g = get_guild_data(ctx.guild.id)
    disabled = g.metadata.disabled_hint_types
    await ctx.send(get_hint(g.item_locations, disabled, ctx.author, player, item))


@bot.command(name="hint-check")
async def hint_check(
    ctx,
    player: Optional[int] = player_param,
    *,
    check: str = commands.parameter(description="Check to look up"),
):
    """Reveals item at the given check for the given player."""
    g = get_guild_data(ctx.guild.id)
    disabled = g.metadata.disabled_hint_types
    await ctx.send(get_hint(g.checks, disabled, ctx.author, player, check))


@bot.command(name="hint-entrance")
async def hint_entrance(
    ctx,
    player: Optional[int] = player_param,
    *,
    location: str = commands.parameter(description="Location to look up"),
):
    """Reveals entrance to the given location for the given player."""
    g = get_guild_data(ctx.guild.id)
    disabled = g.metadata.disabled_hint_types
    await ctx.send(get_hint(g.entrances, disabled, ctx.author, player, location))


@bot.command(name="search")
async def search(ctx, *, query=commands.parameter(description="Search query")):
    """
    Lists items, checks, and entrances matching search query.
    """
    g = get_guild_data(ctx.guild.id)
    response = get_search_response(
        query,
        # TODO Limit to enabled hint types?
        g.item_locations,
        g.checks,
        g.entrances,
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
    hint_types_to_change = get_hint_types(hint_type)
    if not len(hint_types_to_change):
        await ctx.send(f"Unrecognized hint type '{hint_type}'.")
    else:
        # TODO: Should set-cooldown apply to disabled hint types?
        #  What about set-cooldown specifically for a disabled type?
        cooldown = max(cooldown, 0)
        g = get_guild_data(ctx.guild.id)
        if HintType.ITEM in hint_types_to_change:
            g.item_locations.hint_times.set_cooldown(cooldown)
        if HintType.CHECK in hint_types_to_change:
            g.checks.hint_times.set_cooldown(cooldown)
        if HintType.ENTRANCE in hint_types_to_change:
            g.entrances.hint_times.set_cooldown(cooldown)

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
    specified_hint_types: list[HintType] = get_hint_types(hint_type)
    if not len(specified_hint_types):
        await ctx.send(f"Unrecognized hint type '{hint_type}'.")
    else:
        g = get_guild_data(ctx.guild.id)
        response_lines = []
        for ht in specified_hint_types:
            # TODO Avoid showing entrance cooldown if entrance rando is off?
            cooldown = g.get_hint_data(ht).hint_times.cooldown // 60
            resp = f"{ht.value.capitalize()} hint cooldown: {cooldown} minute{'s' if cooldown != 1 else ''}"
            if ht in g.metadata.disabled_hint_types:
                resp += " [disabled]"
            response_lines.append(resp)
        await ctx.send("\n".join(response_lines))


@bot.command(name="enable")
@commands.has_role(ADMIN_ROLE_NAME)
async def enable_hints(ctx, hint_type: str = hint_type_param):
    """Enables the given hint type, or all by default. Admin-only."""
    g = get_guild_data(ctx.guild.id)
    specified_hint_types: list[HintType] = get_hint_types(hint_type)
    if not len(specified_hint_types):
        await ctx.send(f"Unrecognized hint type '{hint_type}'.")
    elif g.metadata.enable_hint_types(specified_hint_types):
        if hint_type == "all":
            await ctx.send("Hints enabled.")
        else:
            await ctx.send(f"{hint_type.capitalize()} hints enabled.")
    else:
        await ctx.send(f"{hint_type.capitalize()} hints are already enabled.")


@bot.command(name="disable")
@commands.has_role(ADMIN_ROLE_NAME)
async def disable_hints(ctx, hint_type: str = hint_type_param):
    """Disables the given hint type, or all by default. Admin-only."""
    g = get_guild_data(ctx.guild.id)
    specified_hint_types: list[HintType] = get_hint_types(hint_type)
    if not len(specified_hint_types):
        await ctx.send(f"Unrecognized hint type '{hint_type}'.")
    else:
        if g.metadata.disable_hint_types(specified_hint_types):
            if hint_type == "all":
                await ctx.send("Hints disabled.")
            else:
                await ctx.send(f"{hint_type.capitalize()} hints disabled.")
        else:
            await ctx.send(f"{hint_type.capitalize()} hints are already disabled.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRole):
        await ctx.send(str(error))


bot.run(TOKEN)
