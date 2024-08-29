import discord
import logging
from tracking.tracking_handler import TrackingHandler  # Import the handler
from . import pokemon_urls, dragon_urls
import random
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BasicHabitCheckView(discord.ui.View):
    def __init__(self, handler: TrackingHandler, user_id, habit_id):
        super().__init__(timeout=None)
        self.handler = handler
        self.user_id = int(user_id)
        self.habit_id = int(habit_id)
        logger.debug(f"HabitCheckView initialized with handler: {handler}, user_id: {user_id}, habit_id: {habit_id}")

    async def disable_all_buttons(self):
        """Disable all buttons in the view."""
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="✅ Yes, I did it!", style=discord.ButtonStyle.success)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'Yes' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.handler.handle_check_submission(interaction, self.habit_id, completed=True)
            await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)

    @discord.ui.button(label="❌ No, not yet", style=discord.ButtonStyle.danger)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'No' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.handler.handle_check_submission(interaction, self.habit_id, completed=False)
            await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)


class DetailedHabitCheckView(discord.ui.View):
    def __init__(self, handler: TrackingHandler, user_id, habit_id):
        super().__init__(timeout=None)
        self.handler = handler
        self.user_id = int(user_id)
        self.habit_id = int(habit_id)
        self.habit_data = handler.db_handler.get_habit_data(habit_id)
        self.current_streak = handler.db_handler.get_current_streak(habit_id)
        self.week_key = datetime.now().strftime("%Y-W%U")
        self.week_key = '2024-W36'

        self.embed = self.create_embed()  # Create the embed during initialization
        logger.debug(f"PokemonInfoView initialized with user_id: {user_id}, habit_id: {habit_id}")

    async def disable_all_buttons(self):
        """Disable all buttons in the view."""
        for item in self.children:
            item.disabled = True

    def create_embed(self):
        """Create and return the embed for the Habit Check."""
        embed = discord.Embed(
            title=f"{self.habit_data['habit_name']} Habit Check || {self.week_key}",
            color=discord.Color.random()  # Use a random color for the embed
        )
        
        # Add habit details
        embed.add_field(name="Habit Name", value=f"**Week 22**", inline=True)
        embed.add_field(name="Current Streak", value=f"🔥 {self.current_streak} weeks", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Placeholder for spacing
        
        # Add detailed statistics (simulating columns)
        embed.add_field(name="Stats", value="Value: 10\nUnit: Min", inline=True)
        embed.add_field(name="Stats", value="SPATK: 70\nSPDEF: 40\nTotal: 444", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Placeholder for spacing
        
        embed.set_thumbnail(url=self.get_random_image_url())  # Random pikachu image
        return embed
    
    def get_random_image_url(self):
        """Select a random image URL."""
        return random.choice(pokemon_urls)
    
    @discord.ui.button(label="✅ Yes, I did it!", style=discord.ButtonStyle.success)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'Yes' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.handler.handle_check_submission(interaction, self.habit_id, self.week_key, completed=True)
            await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)

    @discord.ui.button(label="❌ No, not yet", style=discord.ButtonStyle.danger)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'No' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.handler.handle_check_submission(interaction, self.habit_id, self.week_key, completed=False)
            await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)

    @discord.ui.button(label="Release", style=discord.ButtonStyle.secondary)
    async def release_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.debug(f"'Release' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
        await interaction.response.send_message("Pikachu has been released!", ephemeral=True)
