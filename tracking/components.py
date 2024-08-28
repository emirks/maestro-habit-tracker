import discord
import logging
from tracking.tracking_handler import TrackingHandler  # Import the handler

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class HabitCheckView(discord.ui.View):
    def __init__(self, handler: TrackingHandler, user_id):
        super().__init__(timeout=None)
        self.handler = handler
        self.user_id = int(user_id)
        logger.debug(f"HabitCheckView initialized with handler: {handler}, user_id: {user_id}")

    async def disable_all_buttons(self):
        """Disable all buttons in the view."""
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="✅ Yes, I did it!", style=discord.ButtonStyle.success)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'Yes' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.handler.handle_check_submission(interaction, completed=True)
            await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)

    @discord.ui.button(label="❌ No, not yet", style=discord.ButtonStyle.danger)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'No' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.handler.handle_check_submission(interaction, completed=False)
            await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)
