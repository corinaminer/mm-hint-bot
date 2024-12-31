import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from hint_handler import HintTimes, get_hint_response, set_cooldown
from item_location_handler import ItemLocations
from spoiler_log_handler import handle_spoiler_log

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
ITEM_LOCATIONS_KEY = "item locations"
guilds = {}


def get_item_locations(guild_id) -> ItemLocations:
    guild_data = guilds.get(guild_id, {})
    item_locs = guild_data.get(ITEM_LOCATIONS_KEY)
    if item_locs is None:
        item_locs = ItemLocations(guild_id)
        guild_data[ITEM_LOCATIONS_KEY] = item_locs
    return item_locs


def get_hint_times(guild_id) -> HintTimes:
    guild_data = guilds.setdefault(guild_id, {})
    hint_times = guild_data.get("hint times")
    if hint_times is None:
        hint_times = HintTimes(guild_id)
        guild_data["hint times"] = hint_times
    return hint_times


@bot.command(name="set-log")
@commands.has_role(ADMIN_ROLE_NAME)
async def set_spoiler_log(ctx):
    """
    Updates the spoiler log from the text file attached to the "!set-log" message. Admin-only.
    """
    if len(ctx.message.attachments) == 0:
        await ctx.send(
            "Did you forget something? Please attach your spoiler log as a text file :)"
        )
    else:
        data = await ctx.message.attachments[0].read()
        spoiler_lines = data.decode("utf-8").split("\n")
        guild_id = ctx.guild.id
        result_msg, item_locs = handle_spoiler_log(spoiler_lines, guild_id)
        guilds.setdefault(guild_id, {})[ITEM_LOCATIONS_KEY] = item_locs
        await ctx.send(result_msg)


@bot.command(name="hint")
async def hint(
    ctx,
    player=commands.parameter(
        description="Player formatted without spaces, e.g. player5"
    ),
    *,
    item=commands.parameter(description="Item to look up")
):
    """
    Provides location(s) of the given item for the given player. Limited to once every half hour per user.
    """
    guild_id = ctx.guild.id
    await ctx.send(
        get_hint_response(
            player,
            item,
            ctx.message.author.id,
            get_hint_times(guild_id),
            get_item_locations(guild_id),
        )
    )


def get_search_response(guild_id, query: str):
    try:
        matching_items = get_item_locations(guild_id).find_matching_items(query)
    except FileNotFoundError:
        return "No location data is currently stored. (Use !set-log to upload a spoiler log.)"
    if len(matching_items):
        return "Matches: " + ", ".join(matching_items)
    else:
        return "No matching items. Note that this command only finds items that contain your query as an exact substring (case-insensitive)."


@bot.command(name="search")
async def search(
    ctx, *, query=commands.parameter(description="Search query for items")
):
    """
    Lists item names matching search query to help with hint requests. Items must have the query as an exact substring (case-insensitive) to match.
    """
    await ctx.send(get_search_response(ctx.guild.id, query))


@bot.command(name="set-cooldown")
@commands.has_role(ADMIN_ROLE_NAME)
async def set_hint_cooldown(
    ctx, cooldown: int = commands.parameter(description="Cooldown time in minutes")
):
    """
    Sets hint cooldown time in minutes. Admin-only.
    """
    await ctx.send(set_cooldown(cooldown, get_hint_times(ctx.guild.id)))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRole):
        await ctx.send(str(error))


bot.run(TOKEN)
