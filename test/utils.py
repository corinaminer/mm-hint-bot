from unittest.mock import MagicMock

from discord.errors import NotFound


class MockMessage:
    def __init__(self, id, content):
        self.id = id
        self.content = content

    async def edit(self, content):
        self.content = content


class MockChannel:
    def __init__(self, id, messages=None):
        self.id = id
        self.messages = (
            {} if messages is None else {message.id: message for message in messages}
        )

    async def fetch_message(self, message_id):
        message = self.messages.get(message_id)
        if message is None:
            raise NotFound(MagicMock(status=404), None)
        return message


class MockBot:
    def __init__(self, channels=None):
        self.channels = (
            {} if channels is None else {channel.id: channel for channel in channels}
        )

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)
