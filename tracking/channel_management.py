import discord
import logging
logger = logging.getLogger(__name__)

from data_handler import DatabaseHandler

class TrackingChannelManager:
    def __init__(self, guild: discord.Guild, tracking_channel_prefix: str = 'habit-tracking', category_name: str = 'TRACKING CHANNELS'):
        self.guild = guild
        self.tracking_channel_prefix = tracking_channel_prefix
        self.category_name = category_name
        self.db_handler = DatabaseHandler()

    async def assign_role_to_user_for_channel(self, user: discord.User, channel: discord.TextChannel):
        # Get the role for the channel
        role = discord.utils.get(self.guild.roles, name=channel.name)
        
        if role:
            # Assign the role to the user
            await user.add_roles(role)
            logger.info(f"Assigned role '{role.name}' to user '{user.name}'")
        else:
            logger.warning(f"Role for channel '{channel.name}' not found.")



    async def get_or_create_tracking_channel(self) -> discord.TextChannel:
        logger.info('\n'*2)
        logger.info(f"Deciding on the tracking channel to link the declaration. ")
        category = await self._get_category()
        channels = self._get_tracking_channels(category)
        logger.info(f"Current tracking channels: {channels}")

        # Check if there are any existing tracking channels
        if not channels:
            logger.info("No tracking channel exists")
            # No channels exist, create the first one
            new_channel_name = f"{self.tracking_channel_prefix}-1"
            # Create a new channel with specific permissions
            new_channel = await self._create_tracking_channel(category, new_channel_name)
            return new_channel

        # Look for a channel with fewer than 8 members
        for channel in channels:
            habit_data = self.db_handler.get_habits_in_channel(channel.id)
            num_habits = len(habit_data)
            if num_habits < 8:
                logger.info(f"Number of habits in the {channel.name} is {num_habits}. Assigning this channel.\n")
                return channel

        # Create a new channel if all existing ones are full
        new_channel_number = len(channels) + 1
        new_channel_name = f"{self.tracking_channel_prefix}-{new_channel_number}"
        new_channel = await self._create_tracking_channel(category, new_channel_name)
        logger.info(f"Could not find a channel with habit number less than 8. Created new channel: {new_channel.name}\n")
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
    
    async def _create_tracking_channel(self, category: discord.CategoryChannel, new_channel_name: str) -> discord.TextChannel:
        # Create a role with the same name as the channel
        new_role = await self.guild.create_role(name=new_channel_name)
        
        # Set permissions for the role
        permission_overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),  # Show channel to everyone
            new_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),  # Allow this role to access
            self.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)  # Bot can manage the channel
        }

        # Create a new text channel with permissions
        new_channel = await category.create_text_channel(
            new_channel_name,
            overwrites=permission_overwrites,
        )

        # Log the creation
        logger.info(f"Created new channel '{new_channel_name}' with role '{new_role.name}'")

        return new_channel
