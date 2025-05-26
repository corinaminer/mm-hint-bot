import logging
import re

from discord.errors import NotFound

from consts import BOT_VERSION, VERSION_KEY
from utils import (
    HintType,
    SuccessfulHintResult,
    compose_show_hints_message,
    curtail_message,
    get_hint_types,
    load,
    store,
)

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
        },
        SHOW_CHECKS_KEY: {
            player number: {
                channel id: [message id 1, message id 2...]
            }
        }
    }
    A "hint type query" has the same options as the hint type param for show-hints: item | check | entrance | all.
    """

    SHOW_HINTS_KEY = "show-hints"
    SHOW_CHECKS_KEY = "show-checks"

    def __init__(self, guild_id):
        self.filename = message_tracker_filename(guild_id)
        try:
            self._init_from_file()
        except FileNotFoundError:
            self.show_hints_messages = {}
            self.show_checks_msgs = {}

    def _init_from_file(self):
        data = load(self.filename)
        data_version = data.get(VERSION_KEY)
        if data_version == BOT_VERSION:
            show_hints_data = data.get(MessageTracker.SHOW_HINTS_KEY, {})
            self.show_hints_messages = {
                int(player_num): {
                    hint_type: {
                        int(channel_id): message_ids
                        for channel_id, message_ids in hint_type_data.items()
                    }
                    for hint_type, hint_type_data in player_data.items()
                }
                for player_num, player_data in show_hints_data.items()
            }
            show_checks_data = data.get(MessageTracker.SHOW_CHECKS_KEY, {})
            self.show_checks_msgs = {
                int(player_num): {
                    int(channel_id): message_ids
                    for channel_id, message_ids in player_data.items()
                }
                for player_num, player_data in show_checks_data.items()
            }
        else:
            # Data in file is outdated or corrupt. If it's a known old version, use it; otherwise ignore it.
            log.info(
                f"No protocol for updating message tracker filedata with version {data_version}"
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
            for player_id, player_data in self.show_hints_messages.items()
        }
        show_checks_msg_data = {
            str(player_id): {
                str(channel_id): message_ids
                for channel_id, message_ids in player_data.items()
            }
            for player_id, player_data in self.show_checks_msgs.items()
        }
        filedata = {
            VERSION_KEY: BOT_VERSION,
            MessageTracker.SHOW_HINTS_KEY: show_hints_msg_data,
            MessageTracker.SHOW_CHECKS_KEY: show_checks_msg_data,
        }
        store(filedata, self.filename)

    def track_show_hints_message(
        self, player_num: int, hint_type_query: str, channel_id: int, message_id: int
    ):
        self.show_hints_messages.setdefault(player_num, {}).setdefault(
            hint_type_query, {}
        ).setdefault(channel_id, []).append(message_id)
        self.save()

    def track_show_checks_message(
        self, player_num: int, channel_id: int, message_id: int
    ):
        self.show_checks_msgs.setdefault(player_num, {}).setdefault(
            channel_id, []
        ).append(message_id)
        self.save()

    def clear_tracked_messages(self):
        self.show_hints_messages = {}
        self.show_checks_msgs = {}
        self.save()

    async def edit_messages(
        self, bot, hint_result: SuccessfulHintResult, player_hint_data: dict
    ):
        """Updates !show-hint and !show-check responses as needed, given a hint that was just redeemed."""
        show_hints_messages = self.show_hints_messages.get(hint_result.player_num, {})
        all_hint_type_msgs = show_hints_messages.get("all", {})
        single_hint_type_msgs = show_hints_messages.get(str(hint_result.hint_type), {})
        show_checks_updates_per_player = _get_updates_for_show_checks(
            hint_result, self.show_checks_msgs.keys()
        )

        all_relevant_channel_id_dicts = [all_hint_type_msgs, single_hint_type_msgs]
        for player_num in show_checks_updates_per_player:
            all_relevant_channel_id_dicts.append(self.show_checks_msgs[player_num])
        if all(len(msgs) == 0 for msgs in all_relevant_channel_id_dicts):
            # This hint doesn't affect any !show-hints or !show-checks messages.
            return

        # Fetch all messages that need to be updated.
        fetched_messages = await _get_messages(bot, all_relevant_channel_id_dicts)
        records_changed = False

        # Update responses to !show-hints all
        updated_all_hint_type_content = None
        updated_all_hint_type_msgs = {}
        for channel_id in all_hint_type_msgs:
            for message_id in all_hint_type_msgs[channel_id]:
                message = fetched_messages.get(channel_id, {}).get(message_id)
                if message is None:
                    records_changed = True
                    continue
                if updated_all_hint_type_content is None:
                    updated_all_hint_type_content = compose_show_hints_message(
                        get_hint_types("all"), player_hint_data
                    )
                await message.edit(content=updated_all_hint_type_content)
                updated_all_hint_type_msgs.setdefault(channel_id, []).append(message_id)
        if len(updated_all_hint_type_msgs):
            show_hints_messages["all"] = updated_all_hint_type_msgs
        elif len(all_hint_type_msgs):
            del show_hints_messages["all"]

        # Update responses to !show-hints [this hint type]
        updated_single_hint_type_content = None
        updated_single_hint_type_msgs = {}
        for channel_id in single_hint_type_msgs:
            for message_id in single_hint_type_msgs[channel_id]:
                message = fetched_messages.get(channel_id, {}).get(message_id)
                if message is None:
                    records_changed = True
                    continue
                if updated_single_hint_type_content is None:
                    updated_single_hint_type_content = compose_show_hints_message(
                        [hint_result.hint_type], player_hint_data
                    )
                await message.edit(content=updated_single_hint_type_content)
                updated_single_hint_type_msgs.setdefault(channel_id, []).append(
                    message_id
                )
        if len(updated_single_hint_type_msgs):
            show_hints_messages[str(hint_result.hint_type)] = (
                updated_single_hint_type_msgs
            )
        elif len(single_hint_type_msgs):
            del show_hints_messages[str(hint_result.hint_type)]

        # Update affected responses to !show-checks
        for player_num, updates in show_checks_updates_per_player.items():
            show_checks_msgs = self.show_checks_msgs[player_num]
            updated_show_checks_msgs = {}
            for channel_id in show_checks_msgs:
                for message_id in show_checks_msgs[channel_id]:
                    message = fetched_messages.get(channel_id, {}).get(message_id)
                    if message is None:
                        records_changed = True
                        continue
                    existing_content = message.content
                    if existing_content.startswith("-"):
                        await message.edit(
                            content=curtail_message(
                                existing_content + "\n" + "\n".join(updates)
                            )
                        )
                    else:
                        await message.edit(content="\n".join(updates))
                    updated_show_checks_msgs.setdefault(channel_id, []).append(
                        message_id
                    )
            if len(updated_show_checks_msgs):
                self.show_checks_msgs[player_num] = updated_show_checks_msgs
            else:
                del self.show_checks_msgs[player_num]

        # Save if any recorded messages or channels were deleted
        if records_changed:
            self.save()


async def _get_messages(bot, channel_id_maps: list[dict[int, list[int]]]):
    """
    Takes in some dicts of channel IDs to lists of message IDs, e.g. {channel 1 ID: [message 1 ID, message 2 ID]}.
    Returns dict of channel ID -> message ID -> message, including only and all valid messages in the given dicts.
    """
    channels = {}
    messages = {}
    for channels_to_message_ids in channel_id_maps:
        for channel_id in channels_to_message_ids:
            # Find channel
            channel = channels.get(channel_id)
            if channel is None:
                # Haven't looked up this channel yet
                channel = bot.get_channel(channel_id)
                if channel is None:
                    # channel deleted
                    continue
                channels[channel_id] = channel

            # Find messages in this channel
            for message_id in channels_to_message_ids[channel_id]:
                try:
                    message = await channel.fetch_message(message_id)
                except NotFound:
                    # message was deleted
                    continue
                messages.setdefault(channel_id, {})[message_id] = message

    return messages


def _get_updates_for_show_checks(
    hint_result: SuccessfulHintResult, relevant_players
) -> dict[int, list[str]]:
    """
    Given a hint result, determines what updates should be added to !show-checks messages for which players.
    Ignores any players not included in relevant_players (i.e., players with no recorded !show-checks messages).
    Returns a mapping of player numbers to list of updates for that player's !show-checks messages.
    """
    if hint_result.hint_type != HintType.ITEM:
        # !show-checks can only be affected by item hints
        return {}

    results_by_player = {}
    result_re = re.compile(r"World (\d+) (.+)")
    for result in hint_result.results:
        match = result_re.search(result)
        result_world = int(match.group(1))
        if result_world not in relevant_players:
            continue
        result_check = match.group(2)
        results_by_player.setdefault(result_world, []).append(
            f"- {result_check}: Player {hint_result.player_num} {hint_result.item_name}"
        )
    return results_by_player
