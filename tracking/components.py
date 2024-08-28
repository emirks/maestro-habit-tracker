import discord
from datetime import datetime
from tracking.tracking_handler import TrackingHandler  # Import the handler
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class HabitCheckView(discord.ui.View):
    def __init__(self, handler: TrackingHandler, user_id):
        super().__init__(timeout=None)
        self.handler = handler
        self.user_id = int(user_id)
        logger.debug(f"HabitCheckView initialized with handler: {handler}, user_id: {user_id}")

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'Yes' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.handler.handle_check_submission(interaction, completed=True)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'No' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.handler.handle_check_submission(interaction, completed=False)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)
