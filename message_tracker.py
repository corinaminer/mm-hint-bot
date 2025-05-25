import logging

from discord.errors import NotFound

from consts import BOT_VERSION, VERSION_KEY
from utils import HintType, compose_show_hints_message, get_hint_types, load, store

log = logging.getLogger(__name__)

DEFAULT_HINT_COOLDOWN_SEC = 30 * 60


def message_tracker_filename(guild_id) -> str:
    return f"{guild_id}-message_tracker.json"


class MessageTracker:
    """
    File structure:
    {
        VERSION_KEY: version,
        SHOW_HINTS_KEY: {
            player number: {
                hint type query: {
                    channel id: [message id 1, message id 2...]
                },
            },
        }
    }
    A "hint type query" has the same options as the hint type param for show-hints: item | check | entrance | all.
    """

    SHOW_HINTS_KEY = "show-hints"

    def __init__(self, guild_id):
        self.filename = message_tracker_filename(guild_id)
        try:
            self._init_from_file()
        except FileNotFoundError:
            self.messages = {}

    def _init_from_file(self):
        data = load(self.filename)
        data_version = data.get(VERSION_KEY)
        if data_version == BOT_VERSION:
            show_hints_data = data[MessageTracker.SHOW_HINTS_KEY]
            self.messages = {
                int(player_num): {
                    hint_type: {
                        int(channel_id): message_ids
                        for channel_id, message_ids in hint_type_data.items()
                    }
                    for hint_type, hint_type_data in player_data.items()
                }
                for player_num, player_data in show_hints_data.items()
            }
        else:
            # Data in file is outdated or corrupt. If it's a known old version, use it; otherwise ignore it.
            log.info(
                f"No protocol for updating hint message tracker filedata with version {data_version}"
            )
            raise FileNotFoundError

    def save(self):
        show_hints_msg_data = {
            str(player_id): {
                hint_type: {
                    str(channel_id): message_ids
                    for channel_id, message_ids in hint_type_data.items()
                }
                for hint_type, hint_type_data in player_data.items()
            }
            for player_id, player_data in self.messages.items()
        }
        filedata = {
            VERSION_KEY: BOT_VERSION,
            MessageTracker.SHOW_HINTS_KEY: show_hints_msg_data,
        }
        store(filedata, self.filename)

    def track_message(
        self, player_num: int, hint_type_query: str, channel_id: int, message_id: int
    ):
        self.messages.setdefault(player_num, {}).setdefault(
            hint_type_query, {}
        ).setdefault(channel_id, []).append(message_id)
        self.save()

    def clear_tracked_messages(self):
        self.messages = {}
        self.save()

    async def edit_messages(
        self,
        bot,
        player_num: int,
        hint_type_just_hinted: HintType,
        player_hint_data: dict[HintType, dict[str, list[str]]],
    ):
        """Updates old !show-hint responses with a hint that was just redeemed."""
        player_messages = self.messages.get(player_num, {})
        all_hint_type_msgs = player_messages.get("all", {})
        single_hint_type_msgs = player_messages.get(str(hint_type_just_hinted), {})

        records_changed = False
        channels = {
            channel_id: bot.get_channel(channel_id)
            for channel_id in all_hint_type_msgs.keys() | single_hint_type_msgs.keys()
        }
        if len(all_hint_type_msgs):
            updated_content = compose_show_hints_message(
                get_hint_types("all"), player_hint_data
            )
            records_changed = (
                await update_messages(channels, all_hint_type_msgs, updated_content)
                or records_changed
            )
        if len(single_hint_type_msgs):
            updated_content = compose_show_hints_message(
                [hint_type_just_hinted], player_hint_data
            )
            records_changed = (
                await update_messages(channels, single_hint_type_msgs, updated_content)
                or records_changed
            )

        if records_changed:
            self.save()


async def update_messages(channels, message_records, updated_content):
    records_changed = False
    for channel_id, channel in channels.items():
        message_ids = message_records.get(channel_id)
        if message_ids is None:
            # none of these messages are in that channel
            continue
        if channel is None:
            # channel was deleted
            records_changed = True
            del message_records[channel_id]
            continue

        updated_message_ids = []
        for message_id in message_ids:
            try:
                message = await channel.fetch_message(message_id)
            except NotFound:
                continue  # message deleted
            await message.edit(content=updated_content)
            updated_message_ids.append(message_id)
        if len(updated_message_ids) < len(message_ids):
            records_changed = True
            if not len(updated_message_ids):
                # all recorded messages in this channel have been deleted
                del message_records[channel_id]
            else:
                # some recorded messages in this channel have been deleted
                message_records[channel_id] = updated_message_ids
    return records_changed
