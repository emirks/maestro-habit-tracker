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
        self.detailed_check_view_list = None
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

        channel_view_lists = []
        self.db_handler.connect()
        for channel in channels:
            self.db_handler.connect()
            channel_view_list = await self.send_habit_check_to_tracking_channel(channel)
            channel_view_lists.append(channel_view_list)
        self.db_handler.close()

        concatanated_list = [item for sublist in channel_view_lists for item in sublist]
        self.detailed_check_view_list = concatanated_list

    async def send_habit_check_to_tracking_channel(self, tracking_channel: discord.TextChannel):
        from tracking.components import BasicHabitCheckView, DetailedHabitCheckView
        logger.debug(f"Sending habit check to channel: {tracking_channel.name} (ID: {tracking_channel.id})")
        
        habit_data = self.db_handler.get_habits_in_channel(tracking_channel.id)
        logger.debug(f"Retrieved habit data for channel {tracking_channel.name}: {habit_data}")

        channel_view_list = []
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
                    detailed_check_view = DetailedHabitCheckView(self, self.declaration_handler, user, habit_id)
                    
                    habit_message = await tracking_channel.send(
                        detailed_check_view.check_text, 
                        embed=detailed_check_view.embed,  # Include the embed in the message
                        view=detailed_check_view
                    )
                    detailed_check_view.message_id = habit_message.id  # Store the message ID in the view
                    channel_view_list.append(detailed_check_view)

                except Exception as e:
                    logger.error(f"Could not message {user.name}: {e}")
            else:
                logging.info(f"User not found with id: {user_id}")
            
        return channel_view_list
    
    async def end_habit_check_session(self):
        logger.debug("Ending habit check session and disabling all buttons for incomplete checks...")
        for detailed_check_view in self.detailed_check_view_list:
            tracking_channel_id = detailed_check_view.habit_data['tracking_channel_id']
            habit_id = detailed_check_view.habit_data['habit_id']
            user = detailed_check_view.user
            week_key = detailed_check_view.week_key

            channel = await self._get_channel_by_id(tracking_channel_id)

            habit_message = await channel.fetch_message(detailed_check_view.message_id)
            # Disable all buttons in the view
            await detailed_check_view.disable_all_buttons()
            
            # Edit the message to disable the buttons
            await habit_message.edit(view=detailed_check_view)

            # Mark the habit as failed in the database
            self.db_handler.connect()
            self.db_handler.mark_habit_completed(habit_id, completed=False, week_key=week_key)
            self.db_handler.close()

            logger.info(f"Marked habit as failed for {user.name} (ID: {user.id}).")
            
            self.db_handler.close()


    async def _get_channel_by_id(self, channel_id):
        # Try to get the channel from the cache
        channel = self.guild.get_channel(channel_id)
        
        # If it's not cached, fetch from the API
        if not channel:
            try:
                channel = await self.guild.fetch_channel(channel_id)
            except discord.NotFound:
                print(f"Channel with ID {channel_id} not found.")
            except discord.Forbidden:
                print(f"Bot doesn't have permission to access channel {channel_id}.")
            except discord.HTTPException as e:
                print(f"Failed to fetch channel {channel_id}: {e}")
        
        return channel