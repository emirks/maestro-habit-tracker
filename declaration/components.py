import discord
from datetime import datetime
from declaration.declaration_handler import DeclarationHandler  # Import the handler
import logging
import random

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DeclarationView(discord.ui.View):
    def __init__(self, handler: DeclarationHandler, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.handler = handler

        self.embed = self.create_embed()  # Create the embed during initialization
        logger.debug(f"DeclareView initialized with handler: %s", handler)

    async def disable_all_buttons(self):
        """Disable all buttons in the view."""
        for item in self.children:
            item.disabled = True

    def create_embed(self):
        """Create and return the embed for the Habit Check."""
        embed = discord.Embed(
            title="Habit Declaration",
            description=(
                "An atomic habit is a regular practice that is small and easy to do, and can make a remarkable difference in your life.\n"
                "Before declaring your habit, please read the following:\n\n"
                "**Preliminary Info:**\n"
                "- Your habit should be specific and measurable.\n"
                "- Declare habits that you can commit to daily.\n\n"
                "**Example Declaration:**\n"
                "I will ``meditate **for** 5 mins``, ``when I wake up`` so that I can become ``a mindful person``.\n\n"
                "**1- Define your habit:**\n"
                "``Meditate for 5 mins``\n"
                "**2- Get specific:** Setting an exact time and place means not waiting around for inspiration to strike. \n\n"
                "``When I wake up``\n"
                "**3- Ground it in an identity:** The ultimate form of motivation is when a habit becomes part of who you are.\n\n"
                "``A mindful person``"
            ),
            color=discord.Color.blue()
        )

        embed.set_thumbnail(url=self.get_random_image_url())  # Random pikachu image
        return embed
    
    def get_random_image_url(self):
        """Select a random image URL."""
        from tracking import pokemon_urls
        return random.choice(pokemon_urls)
    
    @discord.ui.button(label="Declare", style=discord.ButtonStyle.success)
    async def declare_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'Declare' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
    
            await self.handler.send_declaration_modal(interaction)

            await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)

class HabitDeclarationModal(discord.ui.Modal):
    def __init__(self, handler: DeclarationHandler):
        super().__init__(title="Habit Declaration")
        self.handler = handler
        logger.debug("HabitDeclarationModal initialized with handler: %s", handler)

        # Add the components (text inputs)
        self.habit = discord.ui.TextInput(
            label="Habit",
            placeholder="Describe the small, specific habit you're committing to",
            style=discord.TextStyle.short
        )
        self.add_item(self.habit)
        logger.debug("Added TextInput for habit.")

        self.cue = discord.ui.TextInput(
            label="Cue",
            placeholder="What will trigger this habit? (e.g., time, place, preceding action)",
            style=discord.TextStyle.short
        )
        self.add_item(self.cue)
        logger.debug("Added TextInput for cue.")

        self.frequency = discord.ui.TextInput(
            label="Frequency",
            placeholder="How often will this habit occur? (e.g., Daily, Weekly)",
            style=discord.TextStyle.short
        )
        self.add_item(self.frequency)
        logger.debug("Added TextInput for frequency.")

        self.intention = discord.ui.TextInput(
            label="Implementation Intention",
            placeholder="When [cue], I will [routine].",
            style=discord.TextStyle.short
        )
        self.add_item(self.intention)
        logger.debug("Added TextInput for intention.")

        self.commitment = discord.ui.TextInput(
            label="Commitment",
            placeholder="Why this habit matters to you and how it aligns with your goals",
            style=discord.TextStyle.long
        )
        self.add_item(self.commitment)
        logger.debug("Added TextInput for commitment.")

    async def on_submit(self, interaction: discord.Interaction):
        logger.debug("HabitDeclarationModal submitted by user: %s (ID: %s)", interaction.user.name, interaction.user.id)
        
        habit_data = {
            'metadata': {
                'user_id': str(interaction.user.id),
                'timestamp': datetime.now().isoformat(),
            },
            'declaration': {
                'habit': self.habit.value,
                'cue': self.cue.value,
                'frequency': self.frequency.value,
                'intention': self.intention.value,
                'commitment': self.commitment.value,
            },
        }
        logger.debug("Habit data collected: %s", habit_data)

        await self.handler.handle_habit_submission(interaction, habit_data)
        logger.debug("Habit submission handled for user: %s", interaction.user.name)