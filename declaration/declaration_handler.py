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

    async def send_detailed_habit_view(self, interaction: discord.Interaction, guild, tracking_handler, declaration_handler):
        from declaration.components import DetailedHabitCardView

        # Initialize the view with the necessary parameters
        habit_view = DetailedHabitCardView(guild, tracking_handler, declaration_handler, interaction.user)
        
        # Send the first message to acknowledge the interaction
        await interaction.response.send_message(
            content=f"Getting habits for {interaction.user.mention}",
            ephemeral=True
        )

        # Follow up with each habit embed and its corresponding button
        for embed in habit_view.embeds:
            habit_specific_view = discord.ui.View(timeout=None)
            habit_id = habit_view.habit_ids[habit_view.embeds.index(embed)]
            edit_button = discord.ui.Button(
                label="Edit Habit",
                style=discord.ButtonStyle.secondary
            )
            edit_button.callback = habit_view.generate_edit_button_callback(habit_id)
            habit_specific_view.add_item(edit_button)

            # Send each embed with its corresponding button as a follow-up message
            await interaction.followup.send(
                embed=embed,
                view=habit_specific_view,
                ephemeral=True
            )


    async def send_declaration_view(self, interaction: discord.Interaction):
        from declaration.components import DeclarationView
        habit_declaration_channel = discord.utils.get(interaction.guild.text_channels, name=self.habit_declaration_channel)
        if interaction.channel.name == self.habit_declaration_channel:
            # Create the DeclarationView and its embed
            declaration_view = DeclarationView(self, interaction.user.id)

            # Send the message with both embeds
            await interaction.followup.send(
                embeds=[declaration_view.instructions_embed, declaration_view.full_form_embed],  # Include both embeds
                view=declaration_view,
                ephemeral=True
            )
            logger.info(f"Declaration View Sent.")
        else:
            await interaction.followup.send(f"Please declare your habit in {habit_declaration_channel.mention}", ephemeral=True)

    async def send_habit_edit_modal(self, interaction: discord.Interaction, habit_data, tracking_channel_id):
        from declaration.components import HabitEditModal
        tracking_channel = self.guild.get_channel(tracking_channel_id)
        modal = HabitEditModal(self, habit_data, tracking_channel)
        await interaction.response.send_modal(modal)
        
        # Wait for the modal to be submitted and handle the data
        return await modal.wait_for_submission()

    async def send_declaration_modal(self, interaction: discord.Interaction):
        from declaration.components import HabitDeclarationModal
        modal = HabitDeclarationModal(self)
        await interaction.response.send_modal(modal)

    async def handle_habit_submission(self, interaction: discord.Interaction, habit_data: dict, habit_id=None, predefined_tracking_channel: discord.TextChannel = None):
        # Add the user to the database if they do not exist
        self.db_handler.connect()
        self.db_handler.add_user(interaction.user.id, interaction.user.name)

        logger.debug(f"Handling habit submission for user: {interaction.user.name} (ID: {interaction.user.id})")
        habit_declaration_channel = discord.utils.get(interaction.guild.text_channels, name=self.habit_declaration_channel)
        habit_tracking_channel = predefined_tracking_channel if predefined_tracking_channel else await self.tracking_channel_manager.get_or_create_tracking_channel()
        
        # If habit id is given, update the data
        if habit_id:
            self.db_handler.update_habit_with_data(habit_data, habit_tracking_channel.id, habit_id)
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

        from declaration.components import HabitCardView
        habit_card_view = HabitCardView(self.tracking_handler, declaration_handler=self, user=interaction.user, habit_data=habit_data, tracking_channel_name=habit_tracking_channel.name)

        # Send the message with both embeds
        await interaction.response.send_message(
            embed=habit_card_view.embed,  # Include both embeds
            view=habit_card_view
        )
        
        # Add the user to the habit-tracking channel
        if habit_tracking_channel:
            await self.tracking_channel_manager.add_user_to_text_channel(interaction.user, habit_tracking_channel)
            logger.debug(f"User {interaction.user.name} added to habit tracking channel: {habit_tracking_channel.name}")

            # Add user to the tracking channel table
            self.db_handler.add_user_to_tracking_channel(interaction.user.id, habit_tracking_channel.id)

        # Save habit declaration to a database
        self.db_handler.add_habit_with_data(habit_data, habit_tracking_channel.id)
        self.db_handler.close()

        await interaction.followup.send(f"{interaction.user.mention} Your habit has been declared, and you have been added to the {habit_tracking_channel.mention} channel for tracking your habit!", ephemeral=True)
        logger.debug("User notified of successful habit declaration.")
