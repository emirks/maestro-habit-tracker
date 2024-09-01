import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
from datetime import datetime, timezone
from declaration.declaration_handler import DeclarationHandler
from tracking.tracking_handler import TrackingHandler
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

HABIT_DECLARATION_CHANNEL = 'habit-declaration'
HABIT_TRACKING_CHANNELS_PREFIX = 'habit-tracking'
HABIT_TRACKING_CATEGORY_NAME = 'TRACKING CHANNELS'

guild = None
decalration_handler = None
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
    
    # Initialize handlers
    declaration_handler = DeclarationHandler(guild, HABIT_DECLARATION_CHANNEL, HABIT_TRACKING_CHANNELS_PREFIX, HABIT_TRACKING_CATEGORY_NAME)
    tracking_handler = TrackingHandler(guild, declaration_handler, HABIT_TRACKING_CHANNELS_PREFIX, HABIT_TRACKING_CATEGORY_NAME)

    # Start the weekly habit check task
    check_habits.start()  
    logger.debug("Started weekly habit check task.")

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

# Command to manually trigger the habit check
@bot.tree.command(name="check", description="Ask users if they completed their habits")
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


# Task to check habits every Saturday
@tasks.loop(hours=24)  # Runs every 24 hours
async def check_habits():
    current_day = datetime.now(timezone.utc).weekday()
    logger.debug(f"Current UTC day: {current_day}")
    
    if current_day == 5:  # Saturday at 12:00 PM UTC
        logger.info("It's Saturday. Sending habit check.")
        await tracking_handler.send_habit_check_to_all_tracking_channels()

@check_habits.before_loop
async def before_check_habits():
    await bot.wait_until_ready()
    logger.debug("Bot is ready, starting habit check loop.")

# Run the bot
logger.info("Running the bot.")
bot.run(TOKEN)
