import discord
import logging
import os

from discord.ext import commands
from dotenv import load_dotenv

from hint_handler import get_hint_response, set_cooldown
from location_file_handler import get_locations, store_locations

ADMIN_ROLE_NAME = "admin"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.command(name="set-log")
@commands.has_role(ADMIN_ROLE_NAME)
async def set_spoiler_log(ctx):
    """
    Updates the spoiler log from the text file attached to the "!set-log" message. Admin-only.
    """
    if len(ctx.message.attachments) == 0:
        await ctx.send("Did you forget something? Please attach your spoiler log as a text file :)")
    else:
        data = await ctx.message.attachments[0].read()
        spoiler_lines = data.decode("utf-8").split("\n")
        result_msg = store_locations(spoiler_lines, ctx.message.guild.id)
        await ctx.send(result_msg)


@bot.command(name="hint")
async def hint(
        ctx,
        player=commands.parameter(description="Player formatted without spaces, e.g. player5"),
        *,
        item=commands.parameter(description="Item to look up")):
    """
    Provides location(s) of the given item for the given player. Limited to once every half hour per user.
    """
    await ctx.send(get_hint_response(player, item, ctx.message.author.id, ctx.message.guild.id))


def get_search_response(query: str, locs):
    if not len(locs):
        return "No location data is currently stored. (Use !set-log to upload a spoiler log.)"
    query = query.lower()
    matching_items = []
    for item, data in locs.items():
        if query in item:
            matching_items.append(data["name"])
    if len(matching_items):
        return "Matches: " + ", ".join(matching_items)
    else:
        return "No matching items. Note that this command only finds items that contain your query as an exact substring (case-insensitive)."


@bot.command(name="search")
async def search(ctx, *, query=commands.parameter(description="Search query for items")):
    """
    Lists item names matching search query to help with hint requests. Items must have the query as an exact substring (case-insensitive) to match.
    """
    locs = get_locations(ctx.message.guild.id)
    await ctx.send(get_search_response(query, locs))


@bot.command(name="set-cooldown")
@commands.has_role(ADMIN_ROLE_NAME)
async def set_hint_cooldown(ctx, cooldown: int = commands.parameter(description="Cooldown time in minutes")):
    """
    Sets hint cooldown time in minutes. Admin-only.
    """
    await ctx.send(set_cooldown(cooldown, ctx.message.guild.id))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRole):
        await ctx.send(str(error))


bot.run(TOKEN)
