import discord
from tracking.channel_management import TrackingChannelManager
from tracking import congrats_messages, not_accomplished_messages
from declaration.declaration_handler import DeclarationHandler
from data_handler import DatabaseHandler
import logging
import json
import random

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TrackingHandler:
    def __init__(self, guild: discord.Guild, declaration_handler: DeclarationHandler, habit_tracking_channels_prefix: str, habit_tracking_category_name: str):
        self.guild = guild
        self.tracking_channel_manager = TrackingChannelManager(guild, habit_tracking_channels_prefix, habit_tracking_category_name)
        self.declaration_handler = declaration_handler
        self.db_handler = DatabaseHandler()
        logger.debug(f"TrackingHandler initialized with guild: {guild.name}, category name: {habit_tracking_category_name}")

    def get_response_message(self, interaction, completed):
        user_mention = interaction.user.mention
        message_list = congrats_messages if completed else not_accomplished_messages
        random_message = random.choice(message_list)
        return random_message.format(user_mention=user_mention)
    
    async def handle_check_submission(self, interaction: discord.Interaction, habit_id, week_key, completed: bool):
        """Handle the habit check response from the user."""
        logger.debug(f"Handling habit check for {interaction.user.name} (ID: {interaction.user.id}), completed: {completed}")
        self.db_handler.connect()
        self.db_handler.mark_habit_completed(habit_id, completed, week_key=week_key)
        self.db_handler.close()
        response_message = self.get_response_message(interaction, completed)
        await interaction.response.send_message(response_message)
        logger.debug(f"Sent response to {interaction.user.name}: {response_message}")


    async def send_habit_check_to_all_tracking_channels(self):
        logger.debug("Sending habit check to all tracking channels...")
        category = await self.tracking_channel_manager._get_category()
        channels = self.tracking_channel_manager._get_tracking_channels(category)
        logger.debug(f"Found {len(channels)} tracking channels in category: {category.name}")

        self.db_handler.connect()
        for channel in channels:
            self.db_handler.connect()
            await self.send_habit_check_to_tracking_channel(channel)
        self.db_handler.close()

    async def send_habit_check_to_tracking_channel(self, tracking_channel: discord.TextChannel):
        from tracking.components import BasicHabitCheckView, DetailedHabitCheckView
        logger.debug(f"Sending habit check to channel: {tracking_channel.name} (ID: {tracking_channel.id})")
        
        habit_data = self.db_handler.get_habits_in_channel(tracking_channel.id)
        logger.debug(f"Retrieved habit data for channel {tracking_channel.name}: {habit_data}")

        for user_id, habit_id, habit_name in habit_data:
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
                    detailed_view = DetailedHabitCheckView(self, self.declaration_handler, user, habit_id)
                    
                    await tracking_channel.send(
                        detailed_view.check_text, 
                        embed=detailed_view.embed,  # Include the embed in the message
                        view=detailed_view
                    )
                except Exception as e:
                    logger.error(f"Could not message {user.name}: {e}")
            else:
                logging.info(f"User not found with id: {user_id}")
            
        return None