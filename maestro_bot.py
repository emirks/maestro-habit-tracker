import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from declaration.modals import HabitDeclarationModal

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

HABIT_DECLARATION_CHANNEL = 'habit-declaration'
HABIT_TRACKING_CHANNEL = 'habit-tracking'
DECLARATION_DATA_PATH = os.path.join(os.path.dirname(__file__), 'declaration/habit_declarations.json')

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    await bot.tree.sync()  # Synchronize the slash commands
    check_habits.start()  # Start the weekly habit check task

# Set up the /declare command
@bot.tree.command(name="declare", description="Declare a new habit")
async def declare(interaction: discord.Interaction):
    modal = HabitDeclarationModal(HABIT_DECLARATION_CHANNEL, HABIT_TRACKING_CHANNEL, DECLARATION_DATA_PATH)
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
