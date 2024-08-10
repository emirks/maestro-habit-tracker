import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import os
import json
from datetime import datetime

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

HABIT_DECLARATION_CHANNEL = 'habit-declaration'
HABIT_TRACKING_CHANNEL = 'habit-tracking'
DATA_FILE = 'habit_declarations.json'

# Helper function to save data to a JSON file
def save_habit_declaration(user_id, habit_data):
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as file:
                data = json.load(file)
        else:
            data = {}

        # Append the new habit data
        if user_id in data:
            data[user_id].append(habit_data)
        else:
            data[user_id] = [habit_data]

        with open(DATA_FILE, 'w') as file:
            json.dump(data, file, indent=4)

    except Exception as e:
        print(f"Error saving data: {e}")

class HabitDeclarationModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Habit Declaration")

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

    async def on_submit(self, interaction: discord.Interaction):
        habit_data = {
            'habit': self.habit.value,
            'cue': self.cue.value,
            'frequency': self.frequency.value,
            'intention': self.intention.value,
            'commitment': self.commitment.value,
            'timestamp': datetime.now().isoformat()
        }

        # Save the habit declaration to a file
        save_habit_declaration(str(interaction.user.id), habit_data)

        habit_declaration_channel = discord.utils.get(interaction.guild.text_channels, name=HABIT_DECLARATION_CHANNEL)
        habit_tracking_channel = discord.utils.get(interaction.guild.text_channels, name=HABIT_TRACKING_CHANNEL)

        if habit_declaration_channel:
            await habit_declaration_channel.send(
                f"**Habit Declaration**\n"
                f"Habit: {habit_data['habit']}\n"
                f"Cue: {habit_data['cue']}\n"
                f"Frequency: {habit_data['frequency']}\n"
                f"Implementation Intention: {habit_data['intention']}\n"
                f"Commitment: {habit_data['commitment']}\n"
                f"- {interaction.user.mention}"
            )
        
        if habit_tracking_channel:
            # Add the user to the habit-tracking channel
            await habit_tracking_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            await habit_declaration_channel.send(f"{interaction.user.mention}, you have been added to {habit_tracking_channel.mention} for habit tracking!")

        await interaction.response.send_message("Your habit has been declared, saved, and you have been added to the habit-tracking channel!", ephemeral=True)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    await bot.tree.sync()  # Synchronize the slash commands
    check_habits.start()  # Start the weekly habit check task

@bot.tree.command(name="declare", description="Declare a new habit")
async def declare(interaction: discord.Interaction):
    modal = HabitDeclarationModal()
    await interaction.response.send_modal(modal)

# Task to check habits every Saturday
@tasks.loop(time=datetime.strptime('12:00', '%H:%M').time())  # Run at 12:00 PM UTC
async def check_habits():
    current_day = datetime.utcnow().weekday()
    if current_day == 5:  # Saturday is represented by 5
        await send_habit_check()

@check_habits.before_loop
async def before_check_habits():
    await bot.wait_until_ready()

# Function to send habit check to all users in the habit-tracking channel
async def send_habit_check():
    habit_tracking_channel = discord.utils.get(bot.get_all_channels(), name=HABIT_TRACKING_CHANNEL)
    if habit_tracking_channel:
        for member in habit_tracking_channel.members:
            try:
                await habit_tracking_channel.send(f"{member.mention}, have you completed your habit this week?")
            except Exception as e:
                print(f"Could not message {member.name}: {e}")

# Command to manually trigger the habit check
@bot.tree.command(name="check", description="Ask users if they completed their habits")
async def check(interaction: discord.Interaction):
    await send_habit_check()
    await interaction.response.send_message("Habit check has been sent to all users in the habit-tracking channel.", ephemeral=True)

# Run the bot
bot.run(TOKEN)
