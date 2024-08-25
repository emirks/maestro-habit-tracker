import discord
import json
import os
from datetime import datetime
from discord.ext import tasks
from discord import app_commands
from tracking.channel_management import TrackingChannelManager
import logging

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
        logger.debug(f"DeclarationHandler initialized with channels: {habit_declaration_channel}, prefix: {habit_tracking_channels_prefix} and data path: {declaration_data_path}")

    async def handle_habit_submission(self, interaction: discord.Interaction, habit_data: dict):
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
            logger.warning(f"Habit tracking channel '{self.habit_tracking_channel}' not found.")

        # Save the habit declaration to a file
        logger.debug("Saving habit declaration...")
        self.save_habit_declaration(str(habit_tracking_channel.id), habit_data)

        declaration_data = habit_data['declaration']
        logger.debug(f"Declaration data: {declaration_data}")

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
        
        if habit_tracking_channel:
            # Add the user to the habit-tracking channel
            await self.tracking_channel_manager.add_user_to_text_channel(interaction.user, habit_tracking_channel)
            logger.debug(f"User {interaction.user.name} added to habit tracking channel: {habit_tracking_channel.name}")

        await interaction.response.send_message(f"{interaction.user.mention} Your habit has been declared, and you have been added to the {habit_tracking_channel.mention} channel for tracking your habit!", ephemeral=True)
        logger.debug("User notified of successful habit declaration.")

    def save_habit_declaration(self, channel_id, habit_data):
        try:
            if os.path.exists(self.declaration_data_path):
                logger.debug(f"Loading existing habit declaration data from: {self.declaration_data_path}")
                with open(self.declaration_data_path, 'r') as file:
                    data = json.load(file)
            else:
                logger.debug("No existing declaration data found, creating new data.")
                data = {}

            # Append the new habit data
            if channel_id in data:
                logger.debug(f"Appending new habit data for channel ID: {channel_id}")
                data[channel_id].append(habit_data)
            else:
                logger.debug(f"Creating new entry for channel ID: {channel_id}")
                data[channel_id] = [habit_data]

            with open(self.declaration_data_path, 'w') as file:
                json.dump(data, file, indent=4)
                logger.debug(f"Habit declaration data saved to: {self.declaration_data_path}")

        except Exception as e:
            logger.error(f"Error saving data: {e}")
