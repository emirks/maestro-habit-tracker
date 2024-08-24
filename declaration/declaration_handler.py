import discord
import json
import os
from datetime import datetime
from discord.ext import tasks
from discord import app_commands
from tracking.channel_management import TrackingChannelManager


class DeclarationHandler:
    def __init__(self, bot: discord.Client, habit_declaration_channel: str, habit_tracking_channel: str, declaration_data_path: str):
        self.bot = bot
        self.habit_declaration_channel = habit_declaration_channel
        self.habit_tracking_channel = habit_tracking_channel
        self.declaration_data_path = declaration_data_path

        # Initialize and register the /declare command
        bot.tree.command(name="declare", description="Declare a new habit")(self.declare_command)

    @app_commands.command(name="declare", description="Declare a new habit")
    async def declare_command(self, interaction: discord.Interaction):
        from declaration.modals import HabitDeclarationModal
        modal = HabitDeclarationModal(self)
        await interaction.response.send_modal(modal)

    async def handle_habit_submission(self, interaction: discord.Interaction, habit_data: dict):
        habit_declaration_channel = discord.utils.get(interaction.guild.text_channels, name=self.habit_declaration_channel)
        habit_tracking_channel = discord.utils.get(interaction.guild.text_channels, name=self.habit_tracking_channel)

        # Save the habit declaration to a file
        self.save_habit_declaration(str(habit_tracking_channel.id), habit_data)

        declaration_data = habit_data['declaration']
        if habit_declaration_channel:
            await habit_declaration_channel.send(
                f"**Habit Declaration**\n"
                f"Habit: {declaration_data['habit']}\n"
                f"Cue: {declaration_data['cue']}\n"
                f"Frequency: {declaration_data['frequency']}\n"
                f"Implementation Intention: {declaration_data['intention']}\n"
                f"Commitment: {declaration_data['commitment']}\n"
                f"- {interaction.user.mention}"
            )
        
        if habit_tracking_channel:
            # Add the user to the habit-tracking channel
            await habit_tracking_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            await habit_declaration_channel.send(f"{interaction.user.mention}, you have been added to {habit_tracking_channel.mention} for habit tracking!")

        await interaction.response.send_message("Your habit has been declared, saved, and you have been added to the habit-tracking channel!", ephemeral=True)

    def save_habit_declaration(self, channel_id, habit_data):
        try:
            if os.path.exists(self.declaration_data_path):
                with open(self.declaration_data_path, 'r') as file:
                    data = json.load(file)
            else:
                data = {}

            # Append the new habit data
            if channel_id in data:
                data[channel_id].append(habit_data)
            else:
                data[channel_id] = [habit_data]

            with open(self.declaration_data_path, 'w') as file:
                json.dump(data, file, indent=4)

        except Exception as e:
            print(f"Error saving data: {e}")
