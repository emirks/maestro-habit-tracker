import discord
import logging
from tracking.tracking_handler import TrackingHandler  # Import the handler
from declaration.declaration_handler import DeclarationHandler
from . import pokemon_urls, dragon_urls
import random
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BasicHabitCheckView(discord.ui.View):
    def __init__(self, tracking_handler: TrackingHandler, user_id, habit_id):
        super().__init__(timeout=None)
        self.tracking_handler = tracking_handler
        self.user_id = int(user_id)
        self.habit_id = int(habit_id)
        logger.debug(f"HabitCheckView initialized with handler: {tracking_handler}, user_id: {user_id}, habit_id: {habit_id}")

    async def disable_all_buttons(self):
        """Disable all buttons in the view."""
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="✅ Yes, I did it!", style=discord.ButtonStyle.success)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'Yes' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.tracking_handler.handle_check_submission(interaction, self.habit_id, completed=True)
            await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)

    @discord.ui.button(label="❌ No, not yet", style=discord.ButtonStyle.danger)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'No' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.tracking_handler.handle_check_submission(interaction, self.habit_id, completed=False)
            await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)


class DetailedHabitCheckView(discord.ui.View):
    def __init__(self, tracking_handler: TrackingHandler, declaration_handler: DeclarationHandler, user, habit_id):
        super().__init__(timeout=None)
        self.declaration_handler = declaration_handler
        self.tracking_handler = tracking_handler
        self.user = user
        self.user_id = user.id
        self.habit_id = int(habit_id)
        self.tracking_handler.db_handler.connect()
        self.habit_data = tracking_handler.db_handler.get_habit_data(habit_id)
        self.current_streak = tracking_handler.db_handler.get_current_streak(habit_id)
        self.tracking_handler.db_handler.close()
        self.week_key = datetime.now().strftime("%Y-W%U")

        self.check_text = f"{self.user.mention} did you accomplish your habit of {self.habit_data['habit_name'].lower()} {self.habit_data['time_location'].lower()} this week?"
        self.embed = self.create_embed()  # Create the embed during initialization
        logger.debug(f"DetailedHabitCheckView initialized with user_id: {self.user_id}, habit_id: {habit_id}")

    async def disable_all_buttons(self):
        """Disable all buttons in the view."""
        for item in self.children:
            item.disabled = True

    def create_embed(self):
        """Create and return the embed for the Habit Check."""
        embed = discord.Embed(
            title=f"{self.habit_data['habit_name']} Habit Check || {self.week_key}",
            description=f"{self.user.mention}",
            color=discord.Color.random()  # Use a random color for the embed
        )
        
        # Add habit details
        embed.add_field(name="Habit", value=self.habit_data['habit_name'], inline=True)
        embed.add_field(name="Streak", value=f"🔥 {self.current_streak} weeks", inline=True)
        embed.add_field(name="Time / Location", value=self.habit_data['time_location'], inline=False)
        
        # Motivation and Identity Reminder
        embed.add_field(name="Don't Forget Your Purpose!", value=f"You're {self.habit_data['habit_name'].lower()} to become {self.habit_data['identity'].lower()}.", inline=False)
        
        embed.set_thumbnail(url=self.get_random_image_url())  # Random image
        return embed
    
    def get_random_image_url(self):
        """Select a random image URL."""
        # Adding some variety to the images used, including from dragon_urls
        return random.choice(pokemon_urls)
    
    @discord.ui.button(label="✅ Yes, I did it!", style=discord.ButtonStyle.success)
    async def yes_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'Yes' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.tracking_handler.handle_check_submission(interaction, self.habit_id, self.week_key, completed=True)
            await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)

    @discord.ui.button(label="❌ No, not yet", style=discord.ButtonStyle.danger)
    async def no_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'No' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            await self.tracking_handler.handle_check_submission(interaction, self.habit_id, self.week_key, completed=False)
            await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)

    @discord.ui.button(label="Edit Habit", style=discord.ButtonStyle.secondary)
    async def edit_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'Edit Habit' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
            
            # Wait for the declaration modal to be submitted and handled
            habit_data = await self.declaration_handler.send_habit_edit_modal(interaction, self.habit_data)
            logger.debug(f"Habit data after modal submission: {habit_data}")
            
            logger.debug(f"Initializing the new view for updated habit")
            new_view = DetailedHabitCheckView(self.tracking_handler, self.declaration_handler, self.user, self.habit_id)
            
            logger.debug(f"Initializing DONE the new view for updated habit")

            # Log details of the existing embed(s)
            for embed in interaction.message.embeds:
                logger.debug("Existing Embed Title: %s", embed.title)
                logger.debug("Existing Embed Description: %s", embed.description)
                for field in embed.fields:
                    logger.debug("Existing Embed Field - Name: %s, Value: %s, Inline: %s", field.name, field.value, field.inline)
            
            # Log interaction message content for debugging
            logger.debug("INTERACTION MESSAGE content: %s", interaction.message.content)
            
            # Create the new embed as a list (even if it's a single embed)
            new_embeds = [new_view.embed]

            # Log details of the new embed
            for embed in new_embeds:
                logger.debug("New Embed Title: %s", embed.title)
                logger.debug("New Embed Description: %s", embed.description)
                for field in embed.fields:
                    logger.debug("New Embed Field - Name: %s, Value: %s, Inline: %s", field.name, field.value, field.inline)

            # Clear old embeds and then add the new one
            await interaction.message.edit(embeds=[], view=None)  # Clear existing embeds and view
            await interaction.message.edit(embeds=new_embeds, view=new_view)  # Add new embeds and view
            
            logger.debug(f"New view and embeds added to the message.")
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)
