import discord
from tracking.channel_management import TrackingChannelManager
import logging
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TrackingHandler:
    def __init__(self, guild: discord.Guild, habit_tracking_channels_prefix: str, habit_tracking_category_name: str, declaration_data_path: str):
        self.guild = guild
        self.declaration_data_path = declaration_data_path
        self.tracking_channel_manager = TrackingChannelManager(guild, habit_tracking_channels_prefix, habit_tracking_category_name)
        logger.debug(f"TrackingHandler initialized with guild: {guild.name}, category name: {habit_tracking_category_name}, data path: {declaration_data_path}")

    async def send_habit_check_to_all_tracking_channels(self):
        logger.debug("Sending habit check to all tracking channels...")
        category = await self.tracking_channel_manager._get_category()
        channels = self.tracking_channel_manager._get_tracking_channels(category)
        logger.debug(f"Found {len(channels)} tracking channels in category: {category.name}")

        for channel in channels:
            await self.send_habit_check_to_tracking_channel(channel)

    async def send_habit_check_to_tracking_channel(self, tracking_channel: discord.TextChannel):
        logger.debug(f"Sending habit check to channel: {tracking_channel.name} (ID: {tracking_channel.id})")
        from tracking.components import HabitCheckView
        channel_id = str(tracking_channel.id)
        habit_data = self.read_habit_data_for_channel(channel_id)
        logger.debug(f"Retrieved habit data for channel {tracking_channel.name}: {habit_data}")

        for habit in habit_data:
            metadata = habit['metadata']
            habit_data = habit['declaration']

            user_id = metadata['user_id']
            habit_name = habit_data['habit']
            user = tracking_channel.guild.get_member(int(user_id))
            if not user:
                try:
                    logger.info(f"Trying to fetch the user_id.")
                    user = await tracking_channel.guild.fetch_member(int(user_id))
                except discord.NotFound:
                    logger.info(f"User with ID {user_id} not found in the guild.")
                except Exception as e:
                    logger.error(f"Error fetching user with ID {user_id}: {e}")

            if user:
                try:
                    logger.debug(f"Sending habit check to user: {user.name} (ID: {user.id}) for habit: {habit_name}")
                    view = HabitCheckView(self, user_id)  # Pass the handler (self) to the view
                    await tracking_channel.send(f"{user.mention}, have you completed your habit: **{habit_name}** this week?", view=view)
                except Exception as e:
                    logger.error(f"Could not message {user.name}: {e}")
            else:
                logging.info(f"User not found with id: {user_id}")

    def read_habit_data_for_channel(self, tracking_channel_id):
        logger.debug(f"Reading habit data for channel ID: {tracking_channel_id}")
        with open(self.declaration_data_path, 'r') as file:
            data = json.load(file)
        logger.debug(f"Data read for channel ID {tracking_channel_id}")

        return data[tracking_channel_id]

    async def handle_check_submission(self, interaction: discord.Interaction, completed: bool):
        """Handle the habit check response from the user."""
        logger.debug(f"Handling habit check for {interaction.user.name} (ID: {interaction.user.id}), completed: {completed}")
        response_message = f"{interaction.user.mention} Great job on completing your habit!" if completed else "Keep pushing forward on your habit!"
        await interaction.response.send_message(response_message, ephemeral=True)
        logger.debug(f"Sent response to {interaction.user.name}: {response_message}")
