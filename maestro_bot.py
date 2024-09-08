import discord
from discord.ext import commands, tasks
from discord import app_commands

from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone
import logging
import webserver
import drive

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')

# Check if the 'discord_bot.db' file exists in the current directory
if not os.path.exists('discord_bot.db'):
    logger.info("'discord_bot.db' does not exist. Downloading the latest version from Google Drive...")
    drive.download_latest_file(DRIVE_FOLDER_ID, 'discord_bot')
else:
    logger.info("'discord_bot.db' already exists. Skipping download.")

from declaration.declaration_handler import DeclarationHandler
from tracking.tracking_handler import TrackingHandler

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

HABIT_DECLARATION_CHANNEL = 'habit-declaration'
HABIT_TRACKING_CHANNELS_PREFIX = 'habit-tracking'
HABIT_TRACKING_CATEGORY_NAME = 'TRACKING CHANNELS'

guild = None
declaration_handler = None
tracking_handler = None

@bot.event
async def on_ready():
    global guild, declaration_handler, tracking_handler
    logger.info(f'{bot.user.name} has connected to Discord!')

    # Initialize the guild
    guild = discord.utils.get(bot.guilds, name="Molecular Momentum")
    if guild:
        logger.debug(f"Guild found: {guild.name}")
    else:
        logger.warning("Guild 'Molecular Momentum' not found.")
    
    # Initialize handlers and connect both
    declaration_handler = DeclarationHandler(guild, HABIT_DECLARATION_CHANNEL, HABIT_TRACKING_CHANNELS_PREFIX, HABIT_TRACKING_CATEGORY_NAME)
    tracking_handler = TrackingHandler(guild, declaration_handler, HABIT_TRACKING_CHANNELS_PREFIX, HABIT_TRACKING_CATEGORY_NAME)
    declaration_handler.init_tracking_handler(tracking_handler)

    # Start the weekly habit check task
    check_habits.start()  
    logger.debug("Started weekly habit check task.")

    # Start the DB upload task
    upload_db_to_drive.start()
    logger.debug("Started DB upload task.")
    
    try:
        await bot.tree.sync()  # Synchronize the slash commands with Discord
        logger.debug("Slash commands synchronized with Discord.")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
    
    # Print out all synced commands
    logger.info("Commands synced:")
    for command in bot.tree.get_commands():
        logger.info(f"- {command.name}")
    logger.info("Sync complete.")

# Command to declare a habit
@bot.tree.command(name="declare", description="Declare a new habit")
async def declare(interaction: discord.Interaction):
    logger.debug(f"Declare command invoked by user: {interaction.user.name} (ID: {interaction.user.id})")

    if guild:
        await declaration_handler.send_declaration_view(interaction)
        logger.debug("HabitDeclarationModal sent to user.")
    else:
        logger.warning("Guild is not initialized. Cannot declare habit.")
        await interaction.response.send_message("Guild not found. Please try again later.", ephemeral=True)

# Command to show all habits
@bot.tree.command(name="habits", description="See all habits")
async def habits(interaction: discord.Interaction):
    logger.debug(f"habits command invoked by user: {interaction.user.name} (ID: {interaction.user.id})")

    if guild:
        await declaration_handler.send_detailed_habit_view(interaction, guild, tracking_handler, declaration_handler)
        logger.debug("DetailedHabitView sent to user.")
    else:
        logger.warning("Guild is not initialized. Cannot see habits.")
        await interaction.response.send_message("Guild not found. Please try again later.", ephemeral=True)


# Check if the user has administrator permissions
def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

# Command to manually trigger the habit check, restricted to admins
@bot.tree.command(name="check", description="Ask users if they completed their habits")
@is_admin()
async def check(interaction: discord.Interaction):
    logger.debug(f"Check command invoked by user: {interaction.user.name} (ID: {interaction.user.id})")
    
    # Send an initial response to the interaction
    await interaction.response.defer(ephemeral=True)
    
    if guild:        
        # Run the handler asynchronously to avoid blocking
        await tracking_handler.send_habit_check_to_all_tracking_channels()
        
        # Optionally, edit the deferred response to notify the user that the check is complete
        await interaction.followup.send("Habit check has been triggered for all tracking channels.", ephemeral=True)
    else:
        logger.warning("Guild is not initialized. Cannot track habit.")
        await interaction.followup.send("Guild not found. Please try again later.", ephemeral=True)


# Define UTC+3 timezone by using a timedelta of 3 hours
utc_plus_3 = timezone(timedelta(hours=3))

# Task to check habits every hour
@tasks.loop(hours=1)  # Runs every hour
async def check_habits():
    current_time = datetime.now(utc_plus_3)  # Get the current time in UTC+3
    current_day = current_time.weekday()
    current_hour = current_time.hour

    logger.debug(f"Current UTC+3 day: {current_day}, hour: {current_hour}")

    if current_day == 5 and current_hour == 12:  # Saturday at 12:xx PM UTC+3
        logger.info("It's Saturday between 12:00 and 12:59 (UTC+3). Sending habit check.")
        await tracking_handler.send_habit_check_to_all_tracking_channels()

@check_habits.before_loop
async def before_check_habits():
    await bot.wait_until_ready()
    logger.debug("Bot is ready, starting habit check loop.")

# Add the task to upload the file every 10 minutes
@tasks.loop(minutes=10)  # Runs every 10 minutes
async def upload_db_to_drive():
    try:
        # Assuming drive.upload_file is already implemented and works
        drive.upload_file('discord_bot.db', DRIVE_FOLDER_ID)
        logger.info("Successfully uploaded discord_bot.db to Google Drive.")
    except Exception as e:
        logger.error(f"Failed to upload discord_bot.db to Google Drive: {e}")

@upload_db_to_drive.before_loop
async def before_upload_db_to_drive():
    await bot.wait_until_ready()
    logger.debug("Bot is ready, starting DB upload task loop.")


webserver.keep_alive()
# Run the bot
logger.info("Running the bot.")
bot.run(TOKEN)
