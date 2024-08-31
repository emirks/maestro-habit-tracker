import discord
import json
import os
from tracking.channel_management import TrackingChannelManager
import logging
from data_handler import DatabaseHandler

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DeclarationHandler:
    def __init__(self, guild: discord.Guild, habit_declaration_channel: str, habit_tracking_channels_prefix: str, habit_tracking_category_name: str, declaration_data_path: str):
        self.guild = guild
        self.habit_declaration_channel = habit_declaration_channel
        self.habit_tracking_channels_prefix = habit_tracking_channels_prefix
        self.declaration_data_path = declaration_data_path
        self.tracking_channel_manager = TrackingChannelManager(guild, habit_tracking_channels_prefix, habit_tracking_category_name)
        self.db_handler = DatabaseHandler()
        logger.debug(f"DeclarationHandler initialized with channels: {habit_declaration_channel}, prefix: {habit_tracking_channels_prefix} and data path: {declaration_data_path}")

    async def send_habit_declaration(self, interaction: discord.Interaction):
        from declaration.components import HabitDeclarationModal, DeclarationHandler
        modal = HabitDeclarationModal(self)
        await interaction.response.send_modal(modal)

    async def handle_habit_submission(self, interaction: discord.Interaction, habit_data: dict):
        # Add the user to database if not exists
        self.db_handler.add_user(interaction.user.id, interaction.user.name)

        logger.debug(f"Handling habit submission for user: {interaction.user.name} (ID: {interaction.user.id})")
        habit_declaration_channel = discord.utils.get(interaction.guild.text_channels, name=self.habit_declaration_channel)
        habit_tracking_channel = await self.tracking_channel_manager.get_or_create_tracking_channel()

        if habit_declaration_channel:
            logger.debug(f"Habit declaration channel found: {habit_declaration_channel.name}")
        else:
            logger.warning(f"Habit declaration channel '{self.habit_declaration_channel}' not found.")

        if habit_tracking_channel:
            logger.debug(f"Habit tracking channel found: {habit_tracking_channel.name}")
        else:
            logger.warning(f"Habit tracking channel not found.")

        
        # Log declaration data
        declaration_data = habit_data['declaration']
        logger.debug(f"Declaration data: {declaration_data}")

        # Send declaration message to channel
        if habit_declaration_channel:
            await habit_declaration_channel.send(
                f"**Habit Declaration: {interaction.user.mention}**\n"
                f"Habit: {declaration_data['habit']}\n"
                f"Cue: {declaration_data['cue']}\n"
                f"Frequency: {declaration_data['frequency']}\n"
                f"Implementation Intention: {declaration_data['intention']}\n"
                f"Commitment: {declaration_data['commitment']}"
            )
            logger.debug(f"Habit declaration message sent to channel: {habit_declaration_channel.name}")
        
        # Add the user to the habit-tracking channel
        if habit_tracking_channel:
            await self.tracking_channel_manager.add_user_to_text_channel(interaction.user, habit_tracking_channel)
            logger.debug(f"User {interaction.user.name} added to habit tracking channel: {habit_tracking_channel.name}")

            # Add user to the tracking channel table
            self.db_handler.add_user_to_tracking_channel(interaction.user.id, habit_tracking_channel.id)

        # Save habit declaration to a database
        self.db_handler.add_habit_with_data(habit_data, habit_tracking_channel.id)
        self.db_handler.close()

        await interaction.response.send_message(f"{interaction.user.mention} Your habit has been declared, and you have been added to the {habit_tracking_channel.mention} channel for tracking your habit!", ephemeral=True)
        logger.debug("User notified of successful habit declaration.")
