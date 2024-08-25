import discord
from tracking.channel_management import TrackingChannelManager
import logging
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TrackingHandler:
    def __init__(self, guild: discord.Guild, habit_tracking_channels_prefix: str, habit_tracking_category_name: str, declaration_data_path: str):
        self.declaration_data_path = declaration_data_path
        self.tracking_channel_manager = TrackingChannelManager(guild, habit_tracking_channels_prefix, habit_tracking_category_name)
        logger.debug(f"TrackingHandler initialized.")

    async def send_habit_check_to_all_tracking_channels(self):
        category = await self.tracking_channel_manager._get_category()
        channels = self.tracking_channel_manager._get_tracking_channels(category)

        for channel in channels:
            await self.send_habit_check_to_tracking_channel(channel)

    async def send_habit_check_to_tracking_channel(self, tracking_channel: discord.TextChannel):
        channel_id = str(tracking_channel.id)
        habit_data = self.read_habit_data_for_channel(channel_id)

        for habit in habit_data:
            metadata = habit['metadata']
            habit_data = habit['declaration']

            user_id = metadata['user_id']
            habit_name = habit_data['habit']
            user = tracking_channel.guild.get_member(int(user_id))

            if user:
                try:
                    await tracking_channel.send(f"{user.mention}, have you completed your habit: **{habit_name}** this week?")
                except Exception as e:
                    logger.error(f"Could not message {user.name}: {e}")

    def read_habit_data_for_channel(self, tracking_channel_id):
        with open(self.declaration_data_path, 'r') as file:
            data = json.load(file)

        return data[tracking_channel_id]

    # Function to send habit check to all users in the habit-tracking channel
    async def send_habit_check():
        habit_tracking_channel = discord.utils.get(bot.get_all_channels(), name=HABIT_TRACKING_CHANNEL)
        if habit_tracking_channel:
            logger.info(f"Sending habit check to channel: {habit_tracking_channel.name}")
            for member in habit_tracking_channel.members:
                try:
                    await habit_tracking_channel.send(f"{member.mention}, have you completed your habit this week?")
                    logger.debug(f"Sent habit check message to {member.name}")
                except discord.Forbidden:
                    logger.warning(f"Permission denied: Could not message {member.name}")
                except discord.HTTPException as e:
                    logger.error(f"Failed to send message to {member.name}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error when messaging {member.name}: {e}")
        else:
            logger.warning(f"Habit tracking channel '{HABIT_TRACKING_CHANNEL}' not found.")
