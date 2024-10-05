import discord
from discord import ButtonStyle
from discord.ui import Button, View
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta, timezone
import drive
import os

import logging
logging.basicConfig(level=logging.DEBUG)

def load_environment():
    # Check if running in development or production mode
    environment = os.environ['ENV']
    logging.info('\n')
    logging.info('='*32)
    logging.info(f"MODE: {environment}")
    logging.info('='*32)
    logging.info('\n')

    # Load environment variables
    from dotenv import load_dotenv
    dotenv_file = '.env' if environment == 'production' else '.env.dev'
    logging.info(f"Loading '{dotenv_file}'")
    dotenv_loaded = load_dotenv(dotenv_path=dotenv_file, override=True)
    logging.info(f".env file loaded: {dotenv_loaded}")
    
    # Set the DISCORD_BOT_DB_PREFIX based on the database name
    os.environ['DISCORD_BOT_DB_PREFIX'] = os.environ['DISCORD_BOT_DB_NAME'].split('.')[0]

    # Return the environment variables as a dictionary
    return {
        "DISCORD_BOT_TOKEN": os.environ['DISCORD_BOT_TOKEN'],
        "DRIVE_FOLDER_ID": os.environ['DRIVE_FOLDER_ID'],
        "DISCORD_BOT_DB_NAME": os.environ['DISCORD_BOT_DB_NAME'],
        "DISCORD_BOT_DB_PREFIX": os.environ['DISCORD_BOT_DB_PREFIX'],  # Now it's in the environment
        "GUILD_NAME": os.environ['GUILD_NAME']
    }

def check_and_download_db(db_name, drive_folder_id, db_prefix):
    # Check if the 'discord_bot.db' file exists in the current directory
    if not os.path.exists(db_name):
        logging.info(f"'{db_name}' does not exist. Downloading the latest version from Google Drive...")
        drive.download_latest_file(drive_folder_id, db_prefix, db_name)
    else:
        logging.info(f"'{db_name}' already exists. Skipping download.")

# Initialize bot-related variables and handlers
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

HABIT_DECLARATION_CHANNEL = 'habit-declaration'
HABIT_TRACKING_CHANNELS_PREFIX = 'habit-tracking'
HABIT_TRACKING_CATEGORY_NAME = 'TRACKING CHANNELS'

guild = None
declaration_handler = None
tracking_handler = None
db_handler = None

def initialize_handlers():
    global guild, declaration_handler, tracking_handler, db_handler
    from declaration.declaration_handler import DeclarationHandler
    from tracking.tracking_handler import TrackingHandler
    from data_handler import DatabaseHandler
    
    try:
        guild = discord.utils.get(bot.guilds, name=os.environ['GUILD_NAME'])
        if not guild:
            raise ValueError(f"Guild '{os.environ['GUILD_NAME']}' not found.")

        # Initialize the handlers
        declaration_handler = DeclarationHandler(guild, HABIT_DECLARATION_CHANNEL, HABIT_TRACKING_CHANNELS_PREFIX, HABIT_TRACKING_CATEGORY_NAME)
        tracking_handler = TrackingHandler(guild, declaration_handler, HABIT_TRACKING_CHANNELS_PREFIX, HABIT_TRACKING_CATEGORY_NAME)
        declaration_handler.init_tracking_handler(tracking_handler)
        
        # Initialize the database handler and clean up development habits
        db_handler = DatabaseHandler()
        db_handler.remove_all_dev_habits()

        logging.info("Handlers and guild successfully initialized.")

    except ValueError as ve:
        logging.error(f"Initialization Error: {ve}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during initialization: {e}")

@bot.event
async def on_ready():
    logging.info(f'{bot.user.name} has connected to Discord!')
    initialize_handlers()

    # Start the habit check and DB upload tasks
    check_habits.start()
    logging.debug("Started weekly habit check task.")
    upload_db_to_drive.start()
    logging.debug("Started DB upload task.")
    
    try:
        await bot.tree.sync()  # Synchronize slash commands with Discord
        logging.debug("Slash commands synchronized with Discord.")
    except Exception as e:
        logging.error(f"Failed to sync commands: {e}")

    logging.info("Commands synced:")
    for command in bot.tree.get_commands():
        logging.info(f"- {command.name}")
    logging.info("Sync complete.")

@bot.tree.command(name="declare", description="Declare a new habit")
async def declare(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    logging.debug(f"Declare command invoked by user: {interaction.user.name} (ID: {interaction.user.id})")

    if guild:
        await declaration_handler.send_declaration_view(interaction)
        logging.debug("HabitDeclarationModal sent to user.")
    else:
        logging.warning("Guild is not initialized. Cannot declare habit.")
        await interaction.response.send_message("Guild not found. Please try again later.", ephemeral=True)

@bot.tree.command(name="habits", description="See all habits")
async def habits(interaction: discord.Interaction):
    logging.debug(f"Habits command invoked by user: {interaction.user.name} (ID: {interaction.user.id})")

    if guild:
        await declaration_handler.send_detailed_habit_view(interaction, guild, tracking_handler, declaration_handler)
        logging.debug("DetailedHabitView sent to user.")
    else:
        logging.warning("Guild is not initialized. Cannot see habits.")
        await interaction.response.send_message("Guild not found. Please try again later.", ephemeral=True)

@bot.tree.command(name="support", description="Get the links to support us via membership or donations")
async def support(interaction: discord.Interaction):
    patreon_link = "https://patreon.com/emir_kisa"
    buymeacoffee_link = "https://buymeacoffee.com/maestro.bot"

    embed = discord.Embed(
        title="Support Us",
        description=(
            "Thank you for considering supporting us! By becoming a member on Patreon, "
            "you will gain access to exclusive features and benefits. Alternatively, you can "
            "support us with a one-time donation via Buy Me a Coffee. Use the buttons below to contribute."
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="Your support means a lot to us!")

    patreon_button = Button(label="Become a Member", url=patreon_link, style=ButtonStyle.link)
    donate_button = Button(label="Donate", url=buymeacoffee_link, style=ButtonStyle.link)

    view = View()
    view.add_item(patreon_button)
    view.add_item(donate_button)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

@bot.tree.command(name="check", description="Ask users if they completed their habits")
@is_admin()
async def check(interaction: discord.Interaction):
    logging.debug(f"Check command invoked by user: {interaction.user.name} (ID: {interaction.user.id})")
    await interaction.response.defer(ephemeral=True)
    
    if guild:
        await tracking_handler.send_habit_check_to_all_tracking_channels()
        await interaction.followup.send("Habit check has been triggered for all tracking channels.", ephemeral=True)
    else:
        logging.warning("Guild is not initialized. Cannot track habit.")
        await interaction.followup.send("Guild not found. Please try again later.", ephemeral=True)

# Define timezone
utc_plus_3 = timezone(timedelta(hours=3))

@tasks.loop(minutes=1)
async def check_habits():
    current_time = datetime.now(utc_plus_3)
    current_day = current_time.weekday()
    current_hour = current_time.hour
    current_minute = current_time.minute

    logging.debug(f"Current UTC+3 day: {current_day}, hour: {current_hour}, minute: {current_minute}")

    if current_day == 5 and current_hour == 12 and current_minute == 0:
        logging.info("It's exactly 12:00 on Saturday (UTC+3). Sending habit check.")
        await tracking_handler.send_habit_check_to_all_tracking_channels()

    if current_day == 5 and current_hour == 23 and current_minute == 59:
        logging.info("It's 00:00 on Sunday (UTC+3). Ending habit check session.")
        await tracking_handler.end_habit_check_session()

@check_habits.before_loop
async def before_check_habits():
    await bot.wait_until_ready()
    logging.debug("Bot is ready, starting habit check loop.")

@tasks.loop(minutes=10)
async def upload_db_to_drive():
    try:
        drive.upload_file(os.environ['DISCORD_BOT_DB_NAME'], os.environ['DRIVE_FOLDER_ID'], os.environ['DISCORD_BOT_DB_PREFIX'])
        logging.info("Successfully uploaded discord_bot.db to Google Drive.")
    except Exception as e:
        logging.error(f"Failed to upload discord_bot.db to Google Drive: {e}")

@upload_db_to_drive.before_loop
async def before_upload_db_to_drive():
    await bot.wait_until_ready()
    logging.debug("Bot is ready, starting DB upload task loop.")

# Function to run the bot
def create_and_run_bot():
    # Load environment variables
    env_vars = load_environment()

    # Check and download the latest DB if necessary
    check_and_download_db(env_vars['DISCORD_BOT_DB_NAME'], env_vars['DRIVE_FOLDER_ID'], env_vars['DISCORD_BOT_DB_PREFIX'])

    # Run the bot with the token
    logging.info("Running the bot.")
    bot.run(env_vars["DISCORD_BOT_TOKEN"])

if __name__ == '__main__':
    create_and_run_bot()
