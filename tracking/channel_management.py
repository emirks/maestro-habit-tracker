import discord

class TrackingChannelManager:
    def __init__(self, guild: discord.Guild, tracking_channel_prefix: str = 'habit-tracking', category_name: str = 'TRACKING CHANNELS'):
        self.guild = guild
        self.tracking_channel_prefix = tracking_channel_prefix
        self.category_name = category_name

    async def get_or_create_tracking_channel(self, user: discord.User) -> discord.TextChannel:
        category = await self._get_category()
        channels = self._get_tracking_channels(category)
        
        for channel in channels:
            if len(channel.members) < 8:
                await channel.set_permissions(user, read_messages=True, send_messages=True)
                return channel

        # Create a new channel if all existing ones are full
        new_channel_number = len(channels) + 1
        new_channel_name = f"{self.tracking_channel_prefix}-{new_channel_number}"
        new_channel = await category.create_text_channel(new_channel_name)
        await new_channel.set_permissions(user, read_messages=True, send_messages=True)
        return new_channel

    async def clean_up_empty_channels(self):
        category = await self._get_category()
        channels = self._get_tracking_channels(category)
        empty_channels = [channel for channel in channels if len(channel.members) == 0]

        for channel in empty_channels:
            await channel.delete()

        # Rename channels to keep the naming convention
        channels = self._get_tracking_channels(category)
        for i, channel in enumerate(sorted(channels, key=lambda c: c.name)):
            expected_name = f"{self.tracking_channel_prefix}-{i + 1}"
            if channel.name != expected_name:
                await channel.edit(name=expected_name)

    async def _get_category(self) -> discord.CategoryChannel:
        return discord.utils.get(self.guild.categories, name=self.category_name)

    def _get_tracking_channels(self, category: discord.CategoryChannel):
        return [channel for channel in category.text_channels if channel.name.startswith(self.tracking_channel_prefix)]
