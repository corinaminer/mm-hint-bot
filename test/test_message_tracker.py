import asyncio
from test.conftest import TEST_GUILD_ID
from test.utils import MockBot, MockChannel, MockMessage

from message_tracker import MessageTracker
from utils import (
    HintType,
    SuccessfulHintResult,
    compose_show_hints_message,
    get_hint_types,
)


def test_edit_messages():
    async def test():
        message_tracker = MessageTracker(TEST_GUILD_ID)
        bot = MockBot()
        hint_result = SuccessfulHintResult(
            "foo", ["World 2 bar"], HintType.ITEM, 1, True
        )
        player_hint_data = {HintType.ITEM: {hint_result.item_name: hint_result.results}}

        # No problem if nothing is recorded
        await message_tracker.edit_messages(bot, hint_result, player_hint_data)

        # Create some messages to track
        show_hints1 = MockMessage(1, "initial content")
        show_hints2 = MockMessage(2, "initial content")
        show_item_hints1 = MockMessage(3, "initial content")
        show_item_hints2 = MockMessage(4, "initial content")
        show_check_hints1 = MockMessage(5, "initial content")
        show_check_hints2 = MockMessage(6, "initial content")
        show_checks1 = MockMessage(7, "initial content")
        show_checks2 = MockMessage(8, "initial content")
        channel = MockChannel(
            1,
            [
                show_hints1,
                show_hints2,
                show_item_hints1,
                show_item_hints2,
                show_check_hints1,
                show_check_hints2,
                show_checks1,
                show_checks2,
            ],
        )
        bot.channels = {channel.id: channel}
        message_tracker.track_show_hints_message(1, "all", channel.id, show_hints1.id)
        message_tracker.track_show_hints_message(2, "all", channel.id, show_hints2.id)
        message_tracker.track_show_hints_message(
            1, "item", channel.id, show_item_hints1.id
        )
        message_tracker.track_show_hints_message(
            2, "item", channel.id, show_item_hints2.id
        )
        message_tracker.track_show_hints_message(
            1, "check", channel.id, show_check_hints1.id
        )
        message_tracker.track_show_hints_message(
            2, "check", channel.id, show_check_hints2.id
        )
        message_tracker.track_show_checks_message(1, channel.id, show_checks1.id)
        message_tracker.track_show_checks_message(2, channel.id, show_checks2.id)

        # Record item hint for player 1 with a result in player's 2 world. Should see updates in player 1's show-hints
        # for types all and item, and player 2's show-checks.
        await message_tracker.edit_messages(bot, hint_result, player_hint_data)
        assert show_hints1.content == compose_show_hints_message(
            get_hint_types("all"), player_hint_data
        )
        assert show_hints2.content == "initial content"
        assert show_item_hints1.content == compose_show_hints_message(
            [HintType.ITEM], player_hint_data
        )
        assert show_item_hints2.content == "initial content"
        assert show_check_hints1.content == "initial content"
        assert show_check_hints2.content == "initial content"
        assert show_checks1.content == "initial content"
        assert show_checks2.content == "- bar: Player 1 foo"

    asyncio.run(test())


def test_show_checks_adds_to_existing_message():
    async def test():
        # If a show-checks message already contains a list of checks, edits should add to that list
        message_tracker = MessageTracker(TEST_GUILD_ID)
        hint_result = SuccessfulHintResult(
            "foo", ["World 2 bar"], HintType.ITEM, 1, True
        )
        player_hint_data = {HintType.ITEM: {hint_result.item_name: hint_result.results}}

        show_checks = MockMessage(1, "- Location 1: Player 1 Fire Arrows")
        channel = MockChannel(1, [show_checks])
        bot = MockBot([channel])
        message_tracker.track_show_checks_message(2, channel.id, show_checks.id)
        await message_tracker.edit_messages(bot, hint_result, player_hint_data)
        assert (
            show_checks.content
            == "- Location 1: Player 1 Fire Arrows\n- bar: Player 1 foo"
        )

    asyncio.run(test())


def test_edit_multiple_messages():
    async def test():
        # Should be able to edit lots of messages across channels
        message_tracker = MessageTracker(TEST_GUILD_ID)
        hint_result = SuccessfulHintResult(
            "foo", ["World 2 bar"], HintType.ITEM, 1, True
        )
        player_hint_data = {HintType.ITEM: {hint_result.item_name: hint_result.results}}

        show_hints1 = MockMessage(1, "initial content")
        show_hints2 = MockMessage(2, "initial content")
        show_hints3 = MockMessage(3, "initial content")
        channel1 = MockChannel(1, [show_hints1, show_hints2])
        channel2 = MockChannel(2, [show_hints3])
        bot = MockBot([channel1, channel2])
        message_tracker.track_show_hints_message(1, "item", channel1.id, show_hints1.id)
        message_tracker.track_show_hints_message(1, "item", channel1.id, show_hints2.id)
        message_tracker.track_show_hints_message(1, "item", channel2.id, show_hints3.id)

        await message_tracker.edit_messages(bot, hint_result, player_hint_data)
        expected_content = compose_show_hints_message(
            get_hint_types("all"), player_hint_data
        )
        assert show_hints1.content == expected_content
        assert show_hints2.content == expected_content
        assert show_hints3.content == expected_content

    asyncio.run(test())


def test_edit_multiple_player_show_checks():
    async def test():
        # Recording a hint with results in multiple worlds should be able to update multiple players' show-checks
        message_tracker = MessageTracker(TEST_GUILD_ID)
        hint_result = SuccessfulHintResult(
            "foo", ["World 2 bar", "World 3 baz"], HintType.ITEM, 1, True
        )
        player_hint_data = {HintType.ITEM: {hint_result.item_name: hint_result.results}}

        show_checks2 = MockMessage(1, "initial content")
        show_checks3 = MockMessage(2, "initial content")
        channel = MockChannel(1, [show_checks2, show_checks3])
        bot = MockBot([channel])
        message_tracker.track_show_checks_message(2, channel.id, show_checks2.id)
        message_tracker.track_show_checks_message(3, channel.id, show_checks3.id)

        await message_tracker.edit_messages(bot, hint_result, player_hint_data)
        assert show_checks2.content == "- bar: Player 1 foo"
        assert show_checks3.content == "- baz: Player 1 foo"

    asyncio.run(test())


def test_edit_messages_deleted():
    async def test():
        message_tracker = MessageTracker(TEST_GUILD_ID)
        hint_result = SuccessfulHintResult(
            "foo", ["World 2 bar"], HintType.ITEM, 1, True
        )
        player_hint_data = {HintType.ITEM: {hint_result.item_name: hint_result.results}}

        show_hints1 = MockMessage(1, "initial content")
        show_hints2 = MockMessage(2, "initial content")
        show_item_hints1 = MockMessage(3, "initial content")
        show_item_hints2 = MockMessage(4, "initial content")
        show_checks1 = MockMessage(5, "initial content")
        show_checks2 = MockMessage(6, "initial content")

        # Make it look like show_hints1, show_item_hints1, show_checks1 were once in this channel but were deleted
        channel = MockChannel(1, [show_hints2, show_item_hints2, show_checks2])
        bot = MockBot([channel])
        message_tracker.track_show_hints_message(1, "all", channel.id, show_hints1.id)
        message_tracker.track_show_hints_message(1, "all", channel.id, show_hints2.id)
        message_tracker.track_show_hints_message(
            1, "item", channel.id, show_item_hints1.id
        )
        message_tracker.track_show_hints_message(
            1, "item", channel.id, show_item_hints2.id
        )
        message_tracker.track_show_checks_message(2, channel.id, show_checks1.id)
        message_tracker.track_show_checks_message(2, channel.id, show_checks2.id)
        await message_tracker.edit_messages(bot, hint_result, player_hint_data)

        # Existing messages should be updated
        assert show_hints2.content == compose_show_hints_message(
            get_hint_types("all"), player_hint_data
        )
        assert show_item_hints2.content == compose_show_hints_message(
            [HintType.ITEM], player_hint_data
        )
        assert show_checks2.content == "- bar: Player 1 foo"

        # Message tracker should update itself to erase records of deleted messages
        assert message_tracker.show_hints_messages[1] == {
            "all": {channel.id: [show_hints2.id]},
            "item": {channel.id: [show_item_hints2.id]},
        }
        assert message_tracker.show_checks_msgs[2] == {channel.id: [show_checks2.id]}

        # Delete the remaining messages. Tracker should no longer include the channel after another edit call
        channel.messages = {}
        await message_tracker.edit_messages(bot, hint_result, player_hint_data)
        # don't really care that it keeps 1 as a key in show_hints_messages, as long as it drops the channel ref
        assert message_tracker.show_hints_messages[1] == {}
        assert 2 not in message_tracker.show_checks_msgs

    asyncio.run(test())


def test_edit_channels_deleted():
    async def test():
        message_tracker = MessageTracker(TEST_GUILD_ID)
        hint_result = SuccessfulHintResult(
            "foo", ["World 2 bar"], HintType.ITEM, 1, True
        )
        player_hint_data = {HintType.ITEM: {hint_result.item_name: hint_result.results}}

        show_hints1 = MockMessage(1, "initial content")
        show_hints2 = MockMessage(2, "initial content")
        show_item_hints1 = MockMessage(3, "initial content")
        show_item_hints2 = MockMessage(4, "initial content")
        show_checks1 = MockMessage(5, "initial content")
        show_checks2 = MockMessage(6, "initial content")

        # Make it look like channel 1 with the first set of messages was deleted
        channel2 = MockChannel(2, [show_hints2, show_item_hints2, show_checks2])
        bot = MockBot([channel2])
        message_tracker.track_show_hints_message(1, "all", 1, show_hints1.id)
        message_tracker.track_show_hints_message(1, "all", channel2.id, show_hints2.id)
        message_tracker.track_show_hints_message(1, "item", 1, show_item_hints1.id)
        message_tracker.track_show_hints_message(
            1, "item", channel2.id, show_item_hints2.id
        )
        message_tracker.track_show_checks_message(2, 1, show_checks1.id)
        message_tracker.track_show_checks_message(2, channel2.id, show_checks2.id)
        await message_tracker.edit_messages(bot, hint_result, player_hint_data)

        # Existing messages should be updated
        assert show_hints2.content == compose_show_hints_message(
            get_hint_types("all"), player_hint_data
        )
        assert show_item_hints2.content == compose_show_hints_message(
            [HintType.ITEM], player_hint_data
        )
        assert show_checks2.content == "- bar: Player 1 foo"

        # Message tracker should update itself to erase records of deleted channel
        assert message_tracker.show_hints_messages[1] == {
            "all": {channel2.id: [show_hints2.id]},
            "item": {channel2.id: [show_item_hints2.id]},
        }
        assert message_tracker.show_checks_msgs[2] == {channel2.id: [show_checks2.id]}

        # Delete the remaining channel. Tracker should no longer include the channel after another edit call
        bot.channels = {}
        await message_tracker.edit_messages(bot, hint_result, player_hint_data)
        # don't really care that it keeps 1 as a key in show_hints_messages, as long as it drops the channel ref
        assert message_tracker.show_hints_messages[1] == {}
        assert 2 not in message_tracker.show_checks_msgs

    asyncio.run(test())
