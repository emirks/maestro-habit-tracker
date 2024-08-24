import discord
from discord.ext import commands, tasks
from datetime import datetime
import json
import os 

class HabitDeclarationModal(discord.ui.Modal):
    def __init__(self, habit_declaration_channel: str, habit_tracking_channel: str, data_path: str):
        super().__init__(title="Habit Declaration")
        self.habit_declaration_channel = habit_declaration_channel
        self.habit_tracking_channel = habit_tracking_channel
        self.data_path = data_path

        # Add the components (text inputs)
        self.habit = discord.ui.TextInput(
            label="Habit",
            placeholder="Describe the small, specific habit you're committing to",
            style=discord.TextStyle.short
        )
        self.add_item(self.habit)

        self.cue = discord.ui.TextInput(
            label="Cue",
            placeholder="What will trigger this habit? (e.g., time, place, preceding action)",
            style=discord.TextStyle.short
        )
        self.add_item(self.cue)

        self.frequency = discord.ui.TextInput(
            label="Frequency",
            placeholder="How often will this habit occur? (e.g., Daily, Weekly)",
            style=discord.TextStyle.short
        )
        self.add_item(self.frequency)

        self.intention = discord.ui.TextInput(
            label="Implementation Intention",
            placeholder="When [cue], I will [routine].",
            style=discord.TextStyle.short
        )
        self.add_item(self.intention)

        self.commitment = discord.ui.TextInput(
            label="Commitment",
            placeholder="Why this habit matters to you and how it aligns with your goals",
            style=discord.TextStyle.long
        )
        self.add_item(self.commitment)

    # Helper function to save data to a JSON file
    def save_habit_declaration(self, channel_id, habit_data):
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r') as file:
                    data = json.load(file)
            else:
                data = {}

            # Append the new habit data
            if channel_id in data:
                data[channel_id].append(habit_data)
            else:
                data[channel_id] = [habit_data]

            with open(self.data_path, 'w') as file:
                json.dump(data, file, indent=4)

        except Exception as e:
            print(f"Error saving data: {e}")

    async def on_submit(self, interaction: discord.Interaction):
        habit_data = {
            'metadata': {
                'user_id': str(interaction.user.id),
                'timestamp': datetime.now().isoformat(),
            },
            'declaration': {
                'habit': self.habit.value,
                'cue': self.cue.value,
                'frequency': self.frequency.value,
                'intention': self.intention.value,
                'commitment': self.commitment.value,
            },
        }

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