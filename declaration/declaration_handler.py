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
    def __init__(self, guild: discord.Guild, habit_declaration_channel: str, habit_tracking_channels_prefix: str, habit_tracking_category_name: str):
        self.guild = guild
        self.habit_declaration_channel = habit_declaration_channel
        self.habit_tracking_channels_prefix = habit_tracking_channels_prefix
        self.tracking_channel_manager = TrackingChannelManager(guild, habit_tracking_channels_prefix, habit_tracking_category_name)
        self.db_handler = DatabaseHandler()
        logger.debug(f"DeclarationHandler initialized with channels: {habit_declaration_channel}, prefix: {habit_tracking_channels_prefix}")

    def init_tracking_handler(self, tracking_handler):
        self.tracking_handler = tracking_handler

    async def send_declaration_view(self, interaction: discord.Interaction):
        from declaration.components import DeclarationView
        
        # Create the DeclarationView and its embed
        declaration_view = DeclarationView(self, interaction.user.id)

        # Send the message with both embeds
        await interaction.response.send_message(
            embeds=[declaration_view.instructions_embed, declaration_view.full_form_embed],  # Include both embeds
            view=declaration_view
        )

    async def send_habit_edit_modal(self, interaction: discord.Interaction, habit_data):
        from declaration.components import HabitEditModal
        modal = HabitEditModal(self, habit_data)
        await interaction.response.send_modal(modal)
        
        # Wait for the modal to be submitted and handle the data
        return await modal.wait_for_submission()


    async def send_declaration_modal(self, interaction: discord.Interaction):
        from declaration.components import HabitDeclarationModal
        modal = HabitDeclarationModal(self)
        await interaction.response.send_modal(modal)

    async def handle_habit_submission(self, interaction: discord.Interaction, habit_data: dict, habit_id=None):
        # Add the user to the database if they do not exist
        self.db_handler.connect()
        self.db_handler.add_user(interaction.user.id, interaction.user.name)

        logger.debug(f"Handling habit submission for user: {interaction.user.name} (ID: {interaction.user.id})")
        habit_declaration_channel = discord.utils.get(interaction.guild.text_channels, name=self.habit_declaration_channel)
        habit_tracking_channel = await self.tracking_channel_manager.get_or_create_tracking_channel()
        
        # If habit id is given, update the data
        if habit_id:
            self.db_handler.add_habit_with_data(habit_data, habit_tracking_channel.id, habit_id)
            self.db_handler.close()
            await interaction.response.send_message(f"Your habit has been updated", ephemeral=True)
            return


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
                f"Habit: {declaration_data['habit_name']}\n"
                f"Time/Location: {declaration_data['time_location']}\n"
                f"Identity: {declaration_data['identity']}\n"
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
