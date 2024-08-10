import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

intents = discord.Intents.default()
intents.message_content = True  # Enable intent to read message content
intents.guilds = True  # Required for adding users to roles/channels

bot = commands.Bot(command_prefix='!', intents=intents)

# Load the env variables
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
print(TOKEN)

# Define the channel names
HABIT_DECLARATION_CHANNEL = 'habit-declaration'
HABIT_TRACKING_CHANNEL = 'habit-tracking'

# Define the format of a habit declaration
HABIT_DECLARATION_FORMAT = "I will [habit] every day at [time]."

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.event
async def on_message(message):
    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # Check if the message is in the habit declaration channel
    if message.channel.name == HABIT_DECLARATION_CHANNEL:
        # Check if the message matches the specific habit declaration format
        if validate_habit_declaration(message.content):
            # Find the habit-tracking channel
            habit_tracking_channel = discord.utils.get(message.guild.text_channels, name=HABIT_TRACKING_CHANNEL)
            if habit_tracking_channel:
                # Add the user to the habit-tracking channel
                await habit_tracking_channel.set_permissions(message.author, read_messages=True, send_messages=True)
                await message.channel.send(f"{message.author.mention}, you have been added to {habit_tracking_channel.mention} for habit tracking!")
        else:
            await message.channel.send(f"{message.author.mention}, please follow the correct format: {HABIT_DECLARATION_FORMAT}")
    await bot.process_commands(message)


def validate_habit_declaration(content):
    # Simple validation based on expected format (can be more complex)
    return content.startswith("I will") and "every day at" in content

# Define the /declare command
@bot.tree.command(name="declare", description="Declare a new habit")
async def declare(interaction: discord.Interaction):
    # Create the components for the habit declaration
    habit_input = discord.ui.TextInput(label="Habit", placeholder="Describe the small, specific habit you're committing to")
    cue_select = discord.ui.Select(
        placeholder="What will trigger this habit?",
        options=[
            discord.SelectOption(label="time", description="A specific time"),
            discord.SelectOption(label="place", description="A specific place"),
            discord.SelectOption(label="preceding action", description="An action that precedes the habit")
        ]
    )
    frequency_select = discord.ui.Select(
        placeholder="Frequency",
        options=[
            discord.SelectOption(label="Daily", description="Every day"),
            discord.SelectOption(label="Weekly", description="Once a week")
        ]
    )
    intention_input = discord.ui.TextInput(label="Implementation Intention", placeholder="When [cue], I will [routine].")
    commitment_input = discord.ui.TextInput(label="Commitment", placeholder="Why this habit matters to you and how it aligns with your goals")

    # Create a view to hold these components
    view = discord.ui.View()
    view.add_item(habit_input)
    view.add_item(cue_select)
    view.add_item(frequency_select)
    view.add_item(intention_input)
    view.add_item(commitment_input)

    # Send the message with components
    await interaction.response.send_message("Please fill out the form below to declare your habit:", view=view, ephemeral=True)

# Event handler for when a user submits the form
@bot.event
async def on_submit(interaction: discord.Interaction):
    habit = interaction.data['components'][0]['value']
    cue = interaction.data['components'][1]['values'][0]
    frequency = interaction.data['components'][2]['values'][0]
    intention = interaction.data['components'][3]['value']
    commitment = interaction.data['components'][4]['value']

    # Find the habit-declaration channel
    habit_declaration_channel = discord.utils.get(interaction.guild.text_channels, name=HABIT_DECLARATION_CHANNEL)
    
    if habit_declaration_channel:
        # Send the formatted habit declaration to the channel
        await habit_declaration_channel.send(
            f"**Habit Declaration**\n"
            f"Habit: {habit}\n"
            f"Cue: {cue}\n"
            f"Frequency: {frequency}\n"
            f"Implementation Intention: {intention}\n"
            f"Commitment: {commitment}\n"
            f"- {interaction.user.mention}"
        )

    await interaction.response.send_message("Your habit has been declared!", ephemeral=True)


# Run the bot
bot.run(TOKEN)
